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
    upload_dir: Path = PROJECT_ROOT / "uploads"
    enable_external_webhooks: bool = False
    enable_financial_integrations: bool = False
    enable_background_sync: bool = False
    enable_external_model: bool = False

    @model_validator(mode="after")
    def validate_secrets(self):
        if self.environment.lower() in {"production", "staging"}:
            if not self.jwt_secret or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET of at least 32 characters is required")
            if not self.encryption_key:
                raise ValueError("ENCRYPTION_KEY is required")
        elif not self.jwt_secret:
            self.jwt_secret = secrets.token_urlsafe(48)
            logger.warning(
                "JWT_SECRET is unset; using an ephemeral development key. "
                "Tokens will be invalid after restart."
            )
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
