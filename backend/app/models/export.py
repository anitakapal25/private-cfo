from sqlalchemy import Column, DateTime, Boolean, String, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime


class TaxExportTemplate(Base, BaseModel):
    """Template for exporting tax filing documents."""
    __tablename__ = "tax_export_templates"
    __table_args__ = {'schema': 'financial'}

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_name = Column(String(200), nullable=False)  # e.g., "ITR-1 Sahaj", "ITR-2", "ITR-4 Sugam"
    assessment_year = Column(String(9), nullable=False)  # e.g., "2026-27"
    description = Column(Text)
    # Format of the export (PDF, XML, JSON, etc.)
    export_format = Column(String(20), nullable=False, default='PDF')  # PDF, XML, JSON, CSV
    # Whether this template is active
    is_active = Column(Boolean, nullable=False, default=True)
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exports = relationship("TaxExport", back_populates="template")


class TaxExport(Base, BaseModel):
    """Record of tax document exports for users."""
    __tablename__ = "tax_exports"
    __table_args__ = {'schema': 'financial'}

    export_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("financial.tax_export_templates.template_id"), nullable=False)
    # Export details
    export_data = Column(Text, nullable=False)  # The actual exported data (could be JSON, XML, etc.)
    file_name = Column(String(255), nullable=False)  # Suggested filename for download
    file_size_bytes = Column(Integer, nullable=False)
    # Status
    is_downloaded = Column(Boolean, nullable=False, default=False)
    download_count = Column(Integer, nullable=False, default=0)
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Export links can expire

    # Relationships
    user = relationship("User", back_populates="tax_exports")
    template = relationship("TaxExportTemplate", back_populates="exports")


class LoanApplicationExport(Base, BaseModel):
    """Record of loan application document exports for users."""
    __tablename__ = "loan_application_exports"
    __table_args__ = {'schema': 'financial'}

    export_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    # Loan details
    loan_type = Column(String(50), nullable=False)  # home, personal, auto, education, business
    loan_amount_requested = Column(Integer, nullable=False)  # Amount in currency units
    # Export details
    export_data = Column(Text, nullable=False)  # The actual exported data (JSON format)
    file_name = Column(String(255), nullable=False)  # Suggested filename for download
    file_size_bytes = Column(Integer, nullable=False)
    # Status
    is_downloaded = Column(Boolean, nullable=False, default=False)
    download_count = Column(Integer, nullable=False, default=0)
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Export links can expire

    # Relationships
    user = relationship("User", back_populates="loan_application_exports")