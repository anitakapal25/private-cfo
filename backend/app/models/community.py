from sqlalchemy import Column, DateTime, Boolean, Integer, String, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import datetime


class CommunityBenchmark(Base, BaseModel):
    """Model for storing anonymized community benchmarks for financial metrics."""
    __tablename__ = "community_benchmarks"
    __table_args__ = {'schema': 'financial'}

    benchmark_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Demographic groupings for anonymization
    age_group = Column(String(20), nullable=False)  # e.g., '25-34', '35-44', '45-54', '55+'
    income_bracket = Column(String(20), nullable=False)  # e.g., '0-5L', '5-10L', '10L+', '10L+'
    # Financial metric being benchmarked
    metric_type = Column(String(50), nullable=False)  # e.g., 'savings_rate', 'asset_allocation_equity', 'debt_to_income', 'emergency_fund_months'
    # The benchmark value (could be average, median, percentile, etc.)
    metric_value = Column(Numeric(10, 4), nullable=False)  # e.g., 0.15 for 15% savings rate
    # Optional: store the type of value (average, median, p25, p75, etc.)
    value_type = Column(String(20), nullable=False, default='average')  # average, median, p25, p75
    # Sample size used to calculate this benchmark (for transparency)
    sample_size = Column(Integer, nullable=False)
    # When this benchmark was last calculated/updated
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    # Optional: region or other filtering criteria
    region = Column(String(50), nullable=True)  # e.g., 'India', 'Maharashtra', etc.
    # Optional: additional metadata in JSON format
    benchmark_metadata = Column(JSONB, nullable=True)

    # Note: We do not store any user-identifiable information in this table.
    # All data is aggregated and anonymized.

# We'll need to import JSONB from sqlalchemy.dialects.postgresql if we want to use it.
# Let's adjust the import.