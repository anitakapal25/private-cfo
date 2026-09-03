"""Server-side authentication state. Secrets are stored only as hashes or ciphertext."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_active", "user_id", "revoked_at"), {"schema": "financial"})

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    refresh_token_hash = Column(String(64), nullable=False, unique=True)
    parent_session_id = Column(UUID(as_uuid=True), ForeignKey("financial.auth_sessions.session_id"))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(String(40))


class AuthChallenge(Base):
    """One-time, hashed email-verification and password-reset challenges."""

    __tablename__ = "auth_challenges"
    __table_args__ = (
        Index("ix_auth_challenges_user_type", "user_id", "challenge_type"),
        {"schema": "financial"},
    )

    challenge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    challenge_type = Column(String(40), nullable=False)
    secret_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True))


class MfaCredential(Base):
    __tablename__ = "mfa_credentials"
    __table_args__ = (Index("uq_mfa_credentials_user", "user_id", unique=True), {"schema": "financial"})

    credential_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    encrypted_totp_secret = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    last_used_step = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    enabled_at = Column(DateTime(timezone=True))


class AuthRateLimitEvent(Base):
    """Hashed rate-limit subjects only; raw IPs and email addresses are not retained."""

    __tablename__ = "auth_rate_limit_events"
    __table_args__ = (Index("ix_auth_rate_limit_subject_time", "subject_hash", "occurred_at"), {"schema": "financial"})

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(40), nullable=False)
    subject_hash = Column(String(64), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
