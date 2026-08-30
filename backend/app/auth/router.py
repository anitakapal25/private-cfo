"""Authentication router for login/logout endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from app.auth.manager import (
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_active_user,
)
from app.core.config import get_db
from app.models.user import User

router = APIRouter()


@router.post("/token", response_model=dict)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.profile.email_address}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Logout user (invalidate token on client side).
    """
    return {"message": "Successfully logged out"}


@router.get("/me")
async def read_current_user(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Get current user information.
    """
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.profile.email_address if current_user.profile else None,
        "full_name": current_user.profile.full_name if current_user.profile else None,
        "role": current_user.role,
        "is_active": current_user.is_active
    }