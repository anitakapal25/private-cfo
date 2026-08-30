from sqlalchemy import Column, DateTime, Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime


class AdvisorConsent(Base, BaseModel):
    """Model for advisor-client consent relationships."""
    __tablename__ = "advisor_consents"
    __table_args__ = {'schema': 'financial'}

    consent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisor_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    is_active = Column(Boolean, nullable=False, default=True)
    scope = Column(String(100), nullable=False, default='read_only')  # e.g., 'read_only', 'full_access'

    # Relationships
    advisor = relationship("User", foreign_keys=[advisor_id])
    client = relationship("User", foreign_keys=[client_id])