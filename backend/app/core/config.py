"""Validated application configuration and database session management."""

import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql://postgres:dev@localhost:5432/artha_dev"
    jwt_secret: str | None = None
    jwt_issuer: str = "arthaos"
    jwt_audience: str = "arthaos-api"
    encryption_key: str | None = None
    enable_external_webhooks: bool = False
    enable_financial_integrations: bool = False
    enable_background_sync: bool = False
    enable_external_model: bool = False
    enable_advisor_access: bool = False
    enable_community_benchmarks: bool = False
    enable_wellness_programs: bool = False
    enable_data_exports: bool = False
    enable_proactive_reviews: bool = False
    proactive_review_interval_seconds: int = 86400
    financial_integration_provider: str | None = None
    financial_integration_approval_reference: str | None = None
    openai_api_key: str | None = None
    external_model_provider: str | None = None
    external_model_approval_reference: str | None = None
    enable_public_registration: bool = False
    enable_mfa: bool = True
    email_delivery_mode: str = "disabled"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_security: str = "starttls"
    smtp_username: str | None = None
    smtp_password: str | None = None
    email_from_address: str | None = None
    public_app_url: str | None = None

    @model_validator(mode="after")
    def validate_secrets(self):
        if self.proactive_review_interval_seconds < 3600:
            raise ValueError("Proactive review interval must be at least one hour")
        if self.enable_background_sync and not self.enable_financial_integrations:
            raise ValueError(
                "ENABLE_BACKGROUND_SYNC requires ENABLE_FINANCIAL_INTEGRATIONS"
            )
        if self.enable_financial_integrations and (
            not self.financial_integration_provider
            or not self.financial_integration_approval_reference
        ):
            raise ValueError(
                "Financial integrations require an approved provider and release approval reference"
            )
        if self.environment.lower() in {"production", "staging", "pilot"}:
            if not self.enable_mfa:
                raise ValueError("MFA cannot be disabled outside development")
            if not self.jwt_secret or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET of at least 32 characters is required")
            if not self.encryption_key:
                raise ValueError("ENCRYPTION_KEY is required")
            if self.database_url.endswith("artha_dev"):
                raise ValueError("DATABASE_URL must be configured outside development")
        elif not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
            logger.warning(
                "JWT_SECRET is unset; using an ephemeral development key. "
                "Tokens will be invalid after restart."
            )
        if self.enable_external_model and (
            self.external_model_provider != "openai"
            or not self.openai_api_key
            or not self.external_model_approval_reference
        ):
            raise ValueError(
                "External model use requires the approved OpenAI provider, API key, and release approval reference"
            )
        if self.email_delivery_mode not in {"disabled", "smtp"}:
            raise ValueError("EMAIL_DELIVERY_MODE must be disabled or smtp")
        if self.smtp_security not in {"ssl", "starttls"}:
            raise ValueError("SMTP_SECURITY must be ssl or starttls")
        if self.enable_public_registration and self.email_delivery_mode != "smtp":
            raise ValueError("Public registration requires SMTP email delivery")
        if self.email_delivery_mode == "smtp" and not all((
            self.smtp_host, self.smtp_username, self.smtp_password,
            self.email_from_address, self.public_app_url,
        )):
            raise ValueError("SMTP email delivery requires host, credentials, from address, and public app URL")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
