"""Public registration and session routes with fail-closed delivery and MFA gates."""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.manager import (
    account_is_locked,
    activate_mfa,
    authenticate_user,
    clear_login_failures,
    create_mfa_challenge,
    enforce_rate_limit,
    get_password_hash,
    issue_session,
    normalize_email,
    now_utc,
    opaque_token,
    record_failed_login,
    revoke_all_sessions,
    rotate_refresh_token,
    session_for_access_token,
    start_mfa_enrollment,
    token_hash,
    user_from_mfa_challenge,
    verify_mfa_login,
)
from app.auth.manager import get_current_active_user, oauth2_scheme
from app.core.config import Settings, get_db, get_settings
from app.models.auth import AuthChallenge, MfaCredential
from app.models.user import Profile, User
from app.services.email_delivery import EmailDeliveryUnavailableError, TransactionalEmailDelivery, get_email_delivery

router = APIRouter()
CHALLENGE_TTL = timedelta(minutes=30)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    full_name: str | None = Field(default=None, max_length=200)


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class PasswordResetConfirmRequest(TokenRequest):
    password: str = Field(min_length=12, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=200)


class MfaChallengeRequest(BaseModel):
    challenge_token: str = Field(min_length=32, max_length=2000)


class MfaCodeRequest(MfaChallengeRequest):
    code: str = Field(pattern=r"^\d{6}$")


def delivery_for(settings: Settings) -> TransactionalEmailDelivery:
    return get_email_delivery(settings)


def record_challenge(db: Session, user: User, challenge_type: str) -> str:
    db.query(AuthChallenge).filter(
        AuthChallenge.user_id == user.user_id,
        AuthChallenge.challenge_type == challenge_type,
        AuthChallenge.consumed_at.is_(None),
    ).update({AuthChallenge.consumed_at: now_utc()}, synchronize_session=False)
    raw_token = opaque_token()
    db.add(AuthChallenge(
        user_id=user.user_id,
        challenge_type=challenge_type,
        secret_hash=token_hash(raw_token),
        expires_at=now_utc() + CHALLENGE_TTL,
    ))
    return raw_token


def consume_challenge(db: Session, token: str, challenge_type: str) -> User:
    challenge = db.query(AuthChallenge).filter(
        AuthChallenge.secret_hash == token_hash(token),
        AuthChallenge.challenge_type == challenge_type,
        AuthChallenge.consumed_at.is_(None),
    ).with_for_update().first()
    if challenge is None or challenge.expires_at <= now_utc():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired")
    user = db.query(User).filter(User.user_id == challenge.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired")
    challenge.consumed_at = now_utc()
    return user


@router.post("/register", status_code=status.HTTP_202_ACCEPTED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not settings.enable_public_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration is not enabled for this release")
    email = normalize_email(str(payload.email))
    enforce_rate_limit(db, "register_ip", request.client.host if request.client else "unknown", limit=10)
    enforce_rate_limit(db, "register_email", email, limit=3)
    existing = db.query(Profile).filter(Profile.email_address == email).first()
    if existing is not None:
        db.commit()
        return {"detail": "If this email can register, a verification message will arrive shortly."}
    try:
        user = User(hashed_password=get_password_hash(payload.password), is_active=True, role="user")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    profile = Profile(user=user, email_address=email, full_name=payload.full_name, email_verified=False)
    db.add_all((user, profile))
    db.flush()
    verification_token = record_challenge(db, user, "email_verification")
    try:
        await delivery_for(settings).send_verification(email, verification_token)
    except EmailDeliveryUnavailableError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registration email is temporarily unavailable") from exc
    db.commit()
    return {"detail": "Check your email for a verification link before signing in."}


@router.post("/verify-email")
def verify_email(payload: TokenRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = consume_challenge(db, payload.token, "email_verification")
    if user.profile is not None:
        user.profile.email_verified = True
    db.commit()
    return {"detail": "Email verified. Sign in to set up multi-factor authentication."}


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    email = normalize_email(str(payload.email))
    enforce_rate_limit(db, "reset_ip", request.client.host if request.client else "unknown", limit=10)
    enforce_rate_limit(db, "reset_email", email, limit=3)
    user = db.query(User).join(Profile).filter(Profile.email_address == email, Profile.email_verified.is_(True)).first()
    if user is not None:
        reset_token = record_challenge(db, user, "password_reset")
        try:
            await delivery_for(settings).send_password_reset(email, reset_token)
        except EmailDeliveryUnavailableError:
            db.rollback()
            return {"detail": "If the account exists, password-reset instructions will arrive shortly."}
    db.commit()
    return {"detail": "If the account exists, password-reset instructions will arrive shortly."}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = consume_challenge(db, payload.token, "password_reset")
    try:
        user.hashed_password = get_password_hash(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    revoke_all_sessions(db, user.user_id, "password_reset")
    db.commit()
    return {"detail": "Password reset. Sign in again with your authenticator code."}


@router.post("/token", response_model=dict)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    email = normalize_email(form_data.username)
    enforce_rate_limit(db, "login_ip", request.client.host if request.client else "unknown", limit=20)
    enforce_rate_limit(db, "login_email", email, limit=8)
    user = db.query(User).join(Profile).filter(Profile.email_address == email).first()
    if user is None or account_is_locked(user) or not authenticate_user(db, email, form_data.password):
        record_failed_login(user)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email, password, or authentication code", headers={"WWW-Authenticate": "Bearer"})
    clear_login_failures(user)
    if not user.profile.email_verified:
        db.commit()
        return {"email_verification_required": True}
    if not settings.enable_mfa:
        user.last_login = now_utc()
        tokens = issue_session(db, user)
        db.commit()
        return tokens
    credential = db.query(MfaCredential).filter(MfaCredential.user_id == user.user_id, MfaCredential.is_active.is_(True)).first()
    user.last_login = now_utc()
    db.commit()
    return {
        "mfa_required": credential is not None,
        "mfa_enrollment_required": credential is None,
        "mfa_challenge_token": create_mfa_challenge(user, "mfa_login" if credential else "mfa_enroll"),
    }


@router.post("/mfa/enrollment")
def enroll_mfa(payload: MfaChallengeRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    user = user_from_mfa_challenge(db, payload.challenge_token, "mfa_enroll")
    try:
        _, secret = start_mfa_enrollment(db, user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="MFA setup is temporarily unavailable") from exc
    db.commit()
    return {"secret": secret, "issuer": "Artha", "account_name": user.profile.email_address}


@router.post("/mfa/enrollment/confirm", response_model=dict)
def confirm_mfa_enrollment(payload: MfaCodeRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    user = user_from_mfa_challenge(db, payload.challenge_token, "mfa_enroll")
    enforce_rate_limit(db, "mfa_enroll", str(user.user_id), limit=10)
    credential = db.query(MfaCredential).filter(MfaCredential.user_id == user.user_id, MfaCredential.is_active.is_(False)).with_for_update().first()
    if credential is None or not activate_mfa(credential, payload.code):
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticator code is invalid")
    tokens = issue_session(db, user)
    db.commit()
    return tokens


@router.post("/mfa/verify", response_model=dict)
def verify_mfa(payload: MfaCodeRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    user = user_from_mfa_challenge(db, payload.challenge_token, "mfa_login")
    enforce_rate_limit(db, "mfa_verify", str(user.user_id), limit=10)
    credential = db.query(MfaCredential).filter(MfaCredential.user_id == user.user_id, MfaCredential.is_active.is_(True)).with_for_update().first()
    if credential is None or not verify_mfa_login(credential, payload.code):
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticator code is invalid")
    tokens = issue_session(db, user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=dict)
def refresh_access_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict[str, str | int]:
    tokens = rotate_refresh_token(db, payload.refresh_token)
    if tokens is None:
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or expired")
    db.commit()
    return tokens


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    session = session_for_access_token(db, token)
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    session.revoked_at = now_utc()
    session.revoked_reason = "logout"
    db.commit()
    return {"detail": "Successfully signed out"}


@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_active_user)) -> dict[str, str | bool | None]:
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.profile.email_address if current_user.profile else None,
        "full_name": current_user.profile.full_name if current_user.profile else None,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }
