from sqlalchemy import Column, DateTime, Boolean, Integer, String, CHAR, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .base import Base, BaseModel
from .advisor import AdvisorConsent
from .investment_platform import InvestmentPlatformConnection
from .wellness_program import UserWellnessParticipation
from .webhook import WebhookSubscription
from .export import TaxExport, LoanApplicationExport
import uuid
from datetime import date, datetime

class User(Base, BaseModel):
    """User model representing a financial freedom copilot user."""
    __tablename__ = "users"
    __table_args__ = {'schema': 'financial'}

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date_of_birth = Column(DateTime(timezone=True), nullable=False)
    gender = Column(CHAR(1))  # 'M', 'F', 'O' (other), or NULL
    marital_status = Column(String(20))  # 'single', 'married', 'divorced', 'widowed'
    dependents_count = Column(Integer, nullable=False, default=0)
    residential_status = Column(String(20), nullable=False, default='resident_indian')
    pan_last_four = Column(CHAR(4))  # Last 4 digits of PAN for reference only
    aadhaar_last_four = Column(CHAR(4))  # Last 4 digits of Aadhaar for reference only
    employment_status = Column(String(20), nullable=False)  # 'employed', 'unemployed', 'self_employed', 'retired'
    primary_occupation = Column(String(100))
    # Authentication fields
    hashed_password = Column(String(255), nullable=True)  # hashed password for auth
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    # Role-based access control
    role = Column(String(20), nullable=False, default='user')  # 'user', 'advisor', 'admin'

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False)
    income_sources = relationship("IncomeSource", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    assets = relationship("Asset", back_populates="user")
    liabilities = relationship("Liability", back_populates="user")
    insurance_policies = relationship("InsurancePolicy", back_populates="user")
    goals = relationship("Goal", back_populates="user")
    financial_freedom_targets = relationship("FinancialFreedomTarget", back_populates="user")
    # Advisor consent relationships
    advisor_consents_given = relationship("AdvisorConsent", foreign_keys="AdvisorConsent.client_id", back_populates="client")
    advisor_consents_received = relationship("AdvisorConsent", foreign_keys="AdvisorConsent.advisor_id", back_populates="advisor")
    # Investment platform connections
    investment_platform_connections = relationship("InvestmentPlatformConnection", back_populates="user")
    # Wellness program participations
    wellness_participations = relationship("UserWellnessParticipation", back_populates="user")
    # Webhook subscriptions
    webhook_subscriptions = relationship("WebhookSubscription", back_populates="user")
    # Tax exports
    tax_exports = relationship("TaxExport", back_populates="user")
    # Loan application exports
    loan_application_exports = relationship("LoanApplicationExport", back_populates="user")

class Profile(Base, BaseModel):
    """Profile model for user contact and preference information."""
    __tablename__ = "profiles"
    __table_args__ = {'schema': 'financial'}

    profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, unique=True)
    full_name = Column(String(200), nullable=False)
    email_address = Column(String(255), nullable=False, unique=True)
    phone_number = Column(String(20), nullable=False, unique=True)
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(10))
    country = Column(String(50), nullable=False, default='India')
    preferred_language = Column(String(10), nullable=False, default='en')
    timezone = Column(String(50), nullable=False, default='Asia/Kolkata')
    email_verified = Column(Boolean, nullable=False, default=False)
    phone_verified = Column(Boolean, nullable=False, default=False)

    # Relationship
    user = relationship("User", back_populates="profile")