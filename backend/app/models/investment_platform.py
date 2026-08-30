from sqlalchemy import Column, DateTime, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime
from app.core.crypto import decrypt_secret, encrypt_secret


class InvestmentPlatformConnection(Base, BaseModel):
    """Model for user connections to investment platforms (e.g., mutual funds, stocks)."""
    __tablename__ = "investment_platform_connections"
    __table_args__ = {'schema': 'financial'}

    connection_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    platform_name = Column(String(100), nullable=False)  # e.g., 'zerodha', 'groww', 'ET Money', 'CAMS'
    platform_user_id = Column(String(255), nullable=True)  # User ID on the platform (if applicable)
    is_active = Column(Boolean, nullable=False, default=True)
    # Encrypted credentials (in practice, use encryption; for MVP, we might store encrypted API keys)
    # For security, we should not store raw credentials. Instead, we can store encrypted tokens.
    # We'll use an encrypted field for the access token or API key.
    encrypted_credentials = Column(Text, nullable=True)  # Encrypted credentials (e.g., access token)
    # Token expiration
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Last sync time
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    # Sync status
    sync_status = Column(String(50), nullable=True)  # e.g., 'success', 'failed', 'pending'
    # Error message if sync failed
    last_error_message = Column(Text, nullable=True)

    # Relationship
    user = relationship("User")

    @staticmethod
    def encrypt_credentials(credentials: str) -> str:
        """
        Encrypt credentials using Fernet symmetric encryption.
        In production, the encryption key should come from a secure key management service.
        """
        return encrypt_secret(credentials)

    @staticmethod
    def decrypt_credentials(encrypted_credentials: str) -> str:
        """
        Decrypt credentials using Fernet symmetric encryption.
        """
        return decrypt_secret(encrypted_credentials)
