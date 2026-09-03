"""Authentication primitives with server-side session revocation and TOTP MFA."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
import struct
from typing import Any
import uuid

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_db, get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.auth import AuthRateLimitEvent, AuthSession, MfaCredential
from app.models.user import Profile, User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14
MFA_CHALLENGE_EXPIRE_MINUTES = 5
LOCKOUT_THRESHOLD = 5
RATE_LIMIT_WINDOW = timedelta(minutes=15)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def password_is_strong(password: str) -> bool:
    return len(password) >= 12 and any(char.islower() for char in password) and any(char.isupper() for char in password) and any(char.isdigit() for char in password)


def get_password_hash(password: str) -> str:
    if not password_is_strong(password):
        raise ValueError("Password must contain at least 12 characters with upper-case, lower-case, and numeric characters")
    kdf = Argon2id(salt=secrets.token_bytes(16), length=32, iterations=3, lanes=4, memory_cost=64 * 1024)
    return kdf.derive_phc_encoded(password.encode())


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    if hashed_password.startswith("$argon2id$"):
        try:
            Argon2id.verify_phc_encoded(plain_password.encode(), hashed_password)
            return True
        except (InvalidKey, ValueError):
            return False
    return pwd_context.verify(plain_password, hashed_password)


def opaque_token() -> str:
    return secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def subject_hash(subject: str) -> str:
    settings = get_settings()
    return hmac.new(settings.jwt_secret.encode(), subject.encode(), hashlib.sha256).hexdigest()


def enforce_rate_limit(db: Session, category: str, subject: str, limit: int) -> None:
    cutoff = now_utc() - RATE_LIMIT_WINDOW
    digest = subject_hash(f"{category}:{subject}")
    attempts = db.query(AuthRateLimitEvent).filter(AuthRateLimitEvent.subject_hash == digest, AuthRateLimitEvent.occurred_at >= cutoff).count()
    if attempts >= limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Please wait before trying again.", headers={"Retry-After": str(int(RATE_LIMIT_WINDOW.total_seconds()))})
    db.add(AuthRateLimitEvent(category=category, subject_hash=digest))


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.query(User).join(Profile).filter(Profile.email_address == normalize_email(email)).first()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return user


def record_failed_login(user: User | None) -> None:
    if user is None:
        return
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= LOCKOUT_THRESHOLD:
        user.lockout_count = (user.lockout_count or 0) + 1
        user.lockout_until = now_utc() + timedelta(minutes=min(15 * (2 ** (user.lockout_count - 1)), 24 * 60))
        user.failed_login_count = 0


def clear_login_failures(user: User) -> None:
    user.failed_login_count = 0
    user.lockout_until = None


def account_is_locked(user: User) -> bool:
    return bool(user.lockout_until and user.lockout_until > now_utc())


def create_access_token(user: User, session: AuthSession, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    now = now_utc()
    return jwt.encode({"sub": str(user.user_id), "sid": str(session.session_id), "exp": now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)), "iat": now, "jti": str(uuid.uuid4()), "iss": settings.jwt_issuer, "aud": settings.jwt_audience}, settings.jwt_secret, algorithm=ALGORITHM)


def issue_session(db: Session, user: User, parent_session_id: uuid.UUID | None = None) -> dict[str, str | int]:
    refresh_token = opaque_token()
    session = AuthSession(user_id=user.user_id, refresh_token_hash=token_hash(refresh_token), parent_session_id=parent_session_id, expires_at=now_utc() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    db.add(session)
    db.flush()
    return {"access_token": create_access_token(user, session), "refresh_token": refresh_token, "token_type": "bearer", "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}


def rotate_refresh_token(db: Session, refresh_token: str) -> dict[str, str | int] | None:
    session = db.query(AuthSession).filter(AuthSession.refresh_token_hash == token_hash(refresh_token)).with_for_update().first()
    if session is None:
        return None
    if session.revoked_at is not None:
        revoke_all_sessions(db, session.user_id, "refresh_replay_detected")
        return None
    if session.expires_at <= now_utc():
        session.revoked_at, session.revoked_reason = now_utc(), "expired"
        return None
    user = db.query(User).filter(User.user_id == session.user_id, User.is_active.is_(True)).first()
    if user is None:
        return None
    session.revoked_at, session.revoked_reason = now_utc(), "rotated"
    return issue_session(db, user, parent_session_id=session.session_id)


def revoke_all_sessions(db: Session, user_id: uuid.UUID, reason: str) -> None:
    db.query(AuthSession).filter(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)).update({AuthSession.revoked_at: now_utc(), AuthSession.revoked_reason: reason}, synchronize_session=False)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], issuer=settings.jwt_issuer, audience=settings.jwt_audience)
        if not payload.get("sub") or not payload.get("sid"):
            raise JWTError("Session-bound token required")
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}) from exc


def session_for_access_token(db: Session, token: str) -> AuthSession:
    payload = decode_access_token(token)
    session = db.query(AuthSession).filter(AuthSession.session_id == payload["sid"], AuthSession.user_id == payload["sub"]).first()
    if session is None or session.revoked_at is not None or session.expires_at <= now_utc():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    return session


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    session = session_for_access_token(db, token)
    user = db.query(User).filter(User.user_id == session.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def create_mfa_challenge(user: User, purpose: str) -> str:
    settings = get_settings()
    now = now_utc()
    return jwt.encode({"sub": str(user.user_id), "purpose": purpose, "exp": now + timedelta(minutes=MFA_CHALLENGE_EXPIRE_MINUTES), "iat": now, "jti": str(uuid.uuid4()), "iss": settings.jwt_issuer, "aud": settings.jwt_audience}, settings.jwt_secret, algorithm=ALGORITHM)


def user_from_mfa_challenge(db: Session, token: str, expected_purpose: str) -> User:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], issuer=settings.jwt_issuer, audience=settings.jwt_audience)
        if payload.get("purpose") != expected_purpose:
            raise JWTError("Incorrect challenge purpose")
        user = db.query(User).filter(User.user_id == payload.get("sub"), User.is_active.is_(True)).first()
        if user is None:
            raise JWTError("Unknown user")
        return user
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA challenge is invalid or expired") from exc


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def totp_step(at: datetime | None = None) -> int:
    return int((at or now_utc()).timestamp()) // 30


def totp_code(secret: str, step: int) -> str:
    padded = secret + "=" * (-len(secret) % 8)
    digest = hmac.new(base64.b32decode(padded), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    return f"{((struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000):06d}"


def verify_totp(secret: str, code: str, *, last_used_step: int | None = None) -> int | None:
    if not (len(code) == 6 and code.isdigit()):
        return None
    current = totp_step()
    for step in (current - 1, current, current + 1):
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(totp_code(secret, step), code):
            return step
    return None


def start_mfa_enrollment(db: Session, user: User) -> tuple[MfaCredential, str]:
    secret = generate_totp_secret()
    credential = db.query(MfaCredential).filter(MfaCredential.user_id == user.user_id).with_for_update().first()
    if credential is None:
        credential = MfaCredential(user_id=user.user_id, encrypted_totp_secret=encrypt_secret(secret), is_active=False)
        db.add(credential)
    else:
        credential.encrypted_totp_secret, credential.is_active, credential.last_used_step, credential.enabled_at = encrypt_secret(secret), False, None, None
    db.flush()
    return credential, secret


def activate_mfa(credential: MfaCredential, code: str) -> bool:
    step = verify_totp(decrypt_secret(credential.encrypted_totp_secret), code, last_used_step=credential.last_used_step)
    if step is None:
        return False
    credential.is_active, credential.last_used_step, credential.enabled_at = True, step, now_utc()
    return True


def verify_mfa_login(credential: MfaCredential, code: str) -> bool:
    step = verify_totp(decrypt_secret(credential.encrypted_totp_secret), code, last_used_step=credential.last_used_step)
    if step is None:
        return False
    credential.last_used_step = step
    return True
