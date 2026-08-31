from sqlalchemy import Column, DateTime, Boolean, Integer, String, BigInteger, Date, Numeric, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from .base import Base, BaseModel
import uuid
from datetime import date

# Document management models
class DocumentStorage(Base, BaseModel):
    """Document storage model for tracking uploaded documents."""
    __tablename__ = "document_storage"
    __table_args__ = {'schema': 'documents'}

    # BaseModel contributes the legacy integer ``id`` primary-key column. Keep
    # this public UUID independently unique so evidence tables can reference it.
    document_id = Column(UUID(as_uuid=True), primary_key=True, unique=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    document_type = Column(String(30), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)  # Reference to encrypted storage (S3 path, etc.)
    file_size_bytes = Column(BigInteger, nullable=False)  # CHECK (file_size_bytes >= 0)
    mime_type = Column(String(100), nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)  # Hex encoded SHA-256
    upload_timestamp = Column(DateTime(timezone=True), nullable=False, server_default=text('NOW()'))
    extraction_status = Column(String(20), nullable=False, default='pending')  # pending, processing, completed, failed, needs_review
    extraction_confidence = Column(Integer)  # CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1)
    verification_status = Column(String(20), nullable=False, default='unverified')  # unverified, partially_verified, verified, disputed
    extracted_data = Column(JSONB)  # Structured data extracted from document
    page_count = Column(Integer)  # For PDFs
    is_encrypted = Column(Boolean, nullable=False, default=True)
    encryption_key_id = Column(UUID(as_uuid=True))  # Reference to encryption key in secrets management
    virus_scan_status = Column(String(20), default='pending')  # pending, clean, infected
    virus_scan_timestamp = Column(DateTime(timezone=True))

class ExtractedField(Base, BaseModel):
    """Extracted field model for tracking data extracted from documents."""
    __tablename__ = "extracted_fields"
    __table_args__ = {'schema': 'documents'}

    extracted_field_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    field_name = Column(String(100), nullable=False)  # Standardized name like 'monthly_gross_salary'
    field_category = Column(String(20), nullable=False)  # income, deduction, asset_value, liability_amount, insurance_premium, tax_info, other
    extracted_value = Column(String, nullable=False)  # Raw extracted value as string
    parsed_value = Column(Integer)  # Parsed numeric value (for currency, percentages, etc.)
    parsed_date = Column(Date)  # Parsed date value
    parsed_text = Column(String)  # Parsed text value
    data_type = Column(String(20), nullable=False)  # currency, date, percentage, text, integer
    source_location = Column(String(100))  # Page number, table/cell reference if available
    extraction_method = Column(String(20), nullable=False)  # ocr, template_matching, rule_based, ml_model
    confidence_score = Column(Integer, nullable=False)  # CHECK (confidence_score >= 0 AND confidence_score <= 1)
    verified_by_user = Column(Boolean, nullable=False, default=False)
    user_corrected_value = Column(Integer)  # If user corrected the extraction
    user_corrected_date = Column(Date)
    user_corrected_text = Column(String)
    verification_timestamp = Column(DateTime(timezone=True))


class DocumentCandidate(Base):
    """Normalized numeric candidate; never authoritative before user confirmation."""
    __tablename__ = "document_candidates"
    __table_args__ = {"schema": "documents"}

    candidate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_storage.document_id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    fact_type = Column(String(60), nullable=False)
    value = Column(Numeric(20, 4), nullable=False)
    unit = Column(String(12), nullable=False, default="INR")
    confidence = Column(Numeric(5, 4), nullable=False)
    source_location = Column(String(100))
    status = Column(String(20), nullable=False, default="candidate")
    linked_fact_id = Column(UUID(as_uuid=True), ForeignKey("financial.financial_facts.fact_id"))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    decided_at = Column(DateTime(timezone=True))
