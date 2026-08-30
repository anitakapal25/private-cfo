from sqlalchemy import Column, DateTime, Boolean, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime


class EmployerWellnessProgram(Base, BaseModel):
    """Model for employer-sponsored financial wellness programs."""
    __tablename__ = "employer_wellness_programs"
    __table_args__ = {'schema': 'financial'}

    program_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employer_name = Column(String(200), nullable=False)
    program_name = Column(String(200), nullable=False)
    description = Column(Text)
    # Custom branding elements
    logo_url = Column(String(500), nullable=True)
    brand_color = Column(String(20), nullable=True)  # Hex color code
    # Program details
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    # Participation tracking
    max_participants = Column(Integer, nullable=True)
    current_participants = Column(Integer, nullable=False, default=0)
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    participants = relationship("UserWellnessParticipation", back_populates="program")


class UserWellnessParticipation(Base, BaseModel):
    """Model for tracking user participation in wellness programs."""
    __tablename__ = "user_wellness_participation"
    __table_args__ = {'schema': 'financial'}

    participation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    program_id = Column(UUID(as_uuid=True), ForeignKey("financial.employer_wellness_programs.program_id"), nullable=False)
    # Participation details
    enrollment_date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # Progress tracking
    progress_percentage = Column(Integer, nullable=False, default=0)  # 0-100
    # Completion status
    status = Column(String(20), nullable=False, default='active')  # active, completed, withdrawn, paused
    # Rewards/incentives
    points_earned = Column(Integer, nullable=False, default=0)
    rewards_redeemed = Column(Integer, nullable=False, default=0)
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="wellness_participations")
    program = relationship("EmployerWellnessProgram", back_populates="participants")