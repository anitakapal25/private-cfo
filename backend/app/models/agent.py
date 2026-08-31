"""Persistence for conversations, verified facts, agent runs, and evidence."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Conversation(Base):
    __tablename__ = "agent_conversations"
    __table_args__ = {"schema": "financial"}

    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, index=True)
    title = Column(String(160), nullable=False, default="Financial freedom conversation")
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"), nullable=False)
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("uq_agent_message_client_request", "conversation_id", "client_request_id", unique=True),
        {"schema": "financial"},
    )

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("financial.agent_conversations.conversation_id"), nullable=False, index=True)
    role = Column(String(12), nullable=False)
    content = Column(Text, nullable=False)
    structured_content = Column(JSONB, nullable=False, default=dict)
    client_request_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    conversation = relationship("Conversation", back_populates="messages")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "financial"}

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("financial.agent_messages.message_id"), nullable=False)
    intent = Column(String(40), nullable=False)
    policy_decision = Column(String(30), nullable=False)
    model_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class ToolCall(Base):
    __tablename__ = "agent_tool_calls"
    __table_args__ = {"schema": "financial"}

    tool_call_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("financial.agent_runs.run_id"), nullable=False, index=True)
    tool_name = Column(String(80), nullable=False)
    tool_version = Column(String(30), nullable=False)
    sanitized_input_hash = Column(String(64), nullable=False)
    outcome = Column(String(20), nullable=False)
    result_reference = Column(String(120))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"
    __table_args__ = (Index("ix_evidence_sources_user_id", "user_id"), {"schema": "financial"})

    evidence_source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    source_type = Column(String(30), nullable=False)
    source_reference = Column(String(120))
    observed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class FinancialFact(Base):
    __tablename__ = "financial_facts"
    __table_args__ = (
        Index(
            "uq_financial_facts_verified_type",
            "user_id", "fact_type", unique=True,
            postgresql_where=text("verification_status = 'verified'"),
        ),
        Index("ix_financial_facts_user_id", "user_id"),
        {"schema": "financial"},
    )

    fact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    fact_type = Column(String(60), nullable=False)
    value = Column(Numeric(20, 4), nullable=False)
    unit = Column(String(12), nullable=False, default="INR")
    source_type = Column(String(30), nullable=False)
    source_id = Column(String(120))
    evidence_source_id = Column(UUID(as_uuid=True), ForeignKey("financial.evidence_sources.evidence_source_id"))
    verification_status = Column(String(20), nullable=False, default="unverified")
    confidence = Column(Numeric(5, 4))
    sensitivity_classification = Column(String(20), nullable=False, default="confidential")
    supersedes_fact_id = Column(UUID(as_uuid=True), ForeignKey("financial.financial_facts.fact_id"))
    observed_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class CalculationRecord(Base):
    __tablename__ = "calculation_records"
    __table_args__ = (Index("ix_calculation_records_user_id", "user_id"), {"schema": "financial"})

    calculation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False)
    calculation_type = Column(String(60), nullable=False)
    calculation_version = Column(String(30), nullable=False)
    inputs = Column(JSONB, nullable=False)
    assumptions = Column(JSONB, nullable=False)
    result = Column(JSONB, nullable=False)
    input_provenance = Column(JSONB, nullable=False, default=list)
    rule_versions = Column(JSONB, nullable=False, default=dict)
    limitations = Column(JSONB, nullable=False, default=list)
    as_of = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)


class ActionPlan(Base):
    __tablename__ = "action_plans"
    __table_args__ = {"schema": "financial"}

    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    actions = relationship("PlannedAction", back_populates="plan", cascade="all, delete-orphan")


class PlannedAction(Base):
    __tablename__ = "planned_actions"
    __table_args__ = {"schema": "financial"}

    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("financial.action_plans.plan_id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)
    monthly_amount = Column(Numeric(20, 4), nullable=False)
    currency = Column(String(12), nullable=False, default="INR")
    rank = Column(Numeric(8, 4), nullable=False)
    rationale = Column(Text, nullable=False)
    impact = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="planned")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    plan = relationship("ActionPlan", back_populates="actions")


class ProactiveReview(Base):
    __tablename__ = "proactive_reviews"
    __table_args__ = {"schema": "financial"}

    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, index=True)
    finding_type = Column(String(60), nullable=False)
    status = Column(String(20), nullable=False, default="open")
    evidence = Column(JSONB, nullable=False)
    rule_version = Column(String(30), nullable=False, default="proactive-review-v1")
    dedup_key = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    dismissed_at = Column(DateTime(timezone=True))


class Confirmation(Base):
    __tablename__ = "agent_confirmations"
    __table_args__ = {"schema": "financial"}

    confirmation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("financial.users.user_id"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("financial.agent_conversations.conversation_id"), nullable=False)
    action_type = Column(String(60), nullable=False)
    action_payload_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = {"schema": "audit"}

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(60), nullable=False)
    target_type = Column(String(60), nullable=False)
    target_id = Column(String(120), nullable=False)
    outcome = Column(String(20), nullable=False)
    metadata_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
