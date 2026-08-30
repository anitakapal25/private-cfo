from sqlalchemy import Column, DateTime, Boolean, Integer, String, CHAR, Numeric, Date, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
import uuid
from datetime import date

# Financial data models
class IncomeSource(Base, BaseModel):
    """Income source model for tracking user's income streams."""
    __tablename__ = "income_sources"
    __table_args__ = {'schema': 'financial'}

    income_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    source_type = Column(String(20), nullable=False)  # salary, bonus, freelance, rental, interest, dividend, pension, other
    source_name = Column(String(200), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # CHECK (amount >= 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    frequency = Column(String(10), nullable=False)  # monthly, quarterly, annually, one-time
    is_taxable = Column(Boolean, nullable=False, default=True)
    tax_withheld = Column(Numeric(15, 2), nullable=False, default=0)  # CHECK (tax_withheld >= 0)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # NULL for ongoing
    growth_rate = Column(Numeric(5, 4), default=0)  # e.g., 0.08 for 8%
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="income_sources")

class Expense(Base, BaseModel):
    """Expense model for tracking user's expenses."""
    __tablename__ = "expenses"
    __table_args__ = {'schema': 'financial'}

    expense_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    category = Column(String(30), nullable=False)
    subcategory = Column(String(100))
    description = Column(String)
    amount = Column(Numeric(15, 2), nullable=False)  # CHECK (amount >= 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    frequency = Column(String(10), nullable=False)
    is_essential = Column(Boolean, nullable=False)
    is_inflation_linked = Column(Boolean, nullable=False, default=True)
    inflation_rate = Column(Numeric(5, 4))  # Custom inflation rate if different from general
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)  # NULL for ongoing
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="expenses")

class Asset(Base, BaseModel):
    """Asset model for tracking user's assets."""
    __tablename__ = "assets"
    __table_args__ = {'schema': 'financial'}

    asset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    asset_type = Column(String(30), nullable=False)
    account_name = Column(String(200), nullable=False)
    institution_name = Column(String(200))
    account_number_masked = Column(CHAR(4))  # Last 4 digits only
    current_value = Column(Numeric(15, 2), nullable=False)  # CHECK (current_value >= 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    purchase_date = Column(Date)
    expected_return_rate = Column(Numeric(5, 4))  # e.g., 0.10 for 10%
    risk_level = Column(String(10))  # low, medium, high
    liquidity = Column(String(10))  # high, medium, low
    is_joint_owned = Column(Boolean, nullable=False, default=False)
    joint_owner_details = Column(JSONB)  # Store structured info about co-owners
    nominee_details = Column(JSONB)  # Store nominee information
    maturity_date = Column(Date)  # For fixed-term instruments
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="assets")

class Liability(Base, BaseModel):
    """Liability model for tracking user's liabilities."""
    __tablename__ = "liabilities"
    __table_args__ = {'schema': 'financial'}

    liability_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    liability_type = Column(String(30), nullable=False)
    lender_name = Column(String(200), nullable=False)
    account_number_masked = Column(CHAR(4))  # Last 4 digits only
    principal_outstanding = Column(Numeric(15, 2), nullable=False)  # CHECK (principal_outstanding >= 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    interest_rate = Column(Numeric(5, 4), nullable=False)  # CHECK (interest_rate >= 0)
    interest_type = Column(String(10), nullable=False)  # fixed, floating, reducing_balance
    emi_amount = Column(Numeric(15, 2), nullable=False)  # CHECK (emi_amount >= 0)
    total_emis = Column(Integer, nullable=False)  # CHECK (total_emis > 0)
    emis_paid = Column(Integer, nullable=False)  # CHECK (emis_paid >= 0 AND emis_paid <= total_emis)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    prepayment_penalty_details = Column(JSONB)  # Store prepayment terms
    is_tax_deductible = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="liabilities")

class InsurancePolicy(Base, BaseModel):
    """Insurance policy model for tracking user's insurance policies."""
    __tablename__ = "insurance_policies"
    __table_args__ = {'schema': 'financial'}

    insurance_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    insurance_type = Column(String(30), nullable=False)
    policy_number_masked = Column(String(20))  # Masked policy number for reference
    provider_name = Column(String(200), nullable=False)
    sum_assured = Column(Numeric(15, 2), nullable=False)  # CHECK (sum_assured >= 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    premium_amount = Column(Numeric(10, 2), nullable=False)  # CHECK (premium_amount >= 0)
    premium_frequency = Column(String(10), nullable=False)  # monthly, quarterly, semi-annual, annual
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    maturity_date = Column(Date)  # For endowment policies
    beneficiaries = Column(JSONB)  # Array of beneficiary objects with relationship and percentage
    nominee_details = Column(JSONB)
    riders = Column(JSONB)  # Array of rider objects
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="insurance_policies")

class Goal(Base, BaseModel):
    """Goal model for tracking user's financial goals."""
    __tablename__ = "goals"
    __table_args__ = {'schema': 'financial'}

    goal_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    goal_type = Column(String(30), nullable=False)
    goal_name = Column(String(200), nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)  # CHECK (target_amount > 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    target_date = Column(Date, nullable=False)
    priority = Column(String(10), nullable=False)  # high, medium, low
    current_amount = Column(Numeric(15, 2), nullable=False, default=0)  # CHECK (current_amount >= 0)
    monthly_contribution = Column(Numeric(10, 2), nullable=False, default=0)  # CHECK (monthly_contribution >= 0)
    expected_return = Column(Numeric(5, 4), default=0)  # e.g., 0.08 for 8%
    inflation_adjusted = Column(Boolean, nullable=False, default=False)
    inflation_rate = Column(Numeric(5, 4))  # Custom inflation rate if different from general
    notes = Column(String)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    user = relationship("User", back_populates="goals")

class FinancialFreedomTarget(Base, BaseModel):
    """Financial freedom target model for tracking user's financial freedom goals."""
    __tablename__ = "financial_freedom_targets"
    __table_args__ = {'schema': 'financial'}

    ff_target_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    target_age = Column(Integer, nullable=False)  # CHECK (target_age > 0 AND target_age <= 100)
    target_lifestyle_expenses = Column(Numeric(15, 2), nullable=False)  # CHECK (target_lifestyle_expenses > 0)
    currency = Column(CHAR(3), nullable=False, default='INR')
    inflation_assumption = Column(Numeric(5, 4), nullable=False)  # CHECK (inflation_assumption >= 0 AND inflation_assumption <= 0.20)
    return_assumption = Column(Numeric(5, 4), nullable=False)  # CHECK (return_assumption >= -0.50 AND return_assumption <= 0.50)
    current_age = Column(Integer)  # Calculated from date_of_birth
    years_to_target = Column(Integer)  # Calculated: target_age - current_age
    required_corpus = Column(Numeric(15, 2))  # Calculated: present value of target lifestyle expenses
    current_projected_corpus = Column(Numeric(15, 2))  # Calculated: future value of current trajectory
    freedom_gap = Column(Numeric(15, 2))  # Calculated: required_corpus - current_projected_corpus
    projected_freedom_age = Column(Integer)  # Calculated: age when projected corpus meets required corpus
    assumptions_documents = Column(JSONB)  # Array of document IDs justifying assumptions

    # Relationships
    user = relationship("User", back_populates="financial_freedom_targets")