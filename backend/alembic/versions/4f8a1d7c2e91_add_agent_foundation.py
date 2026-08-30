"""Add financial-freedom agent foundation.

Revision ID: 4f8a1d7c2e91
Revises: dbb12e7646f0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "4f8a1d7c2e91"
down_revision = "dbb12e7646f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("agent_conversations", sa.Column("conversation_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_agent_conversations_user_id", "agent_conversations", ["user_id"], schema="financial")
    op.create_table("agent_messages", sa.Column("message_id", sa.UUID(), primary_key=True), sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("financial.agent_conversations.conversation_id"), nullable=False), sa.Column("role", sa.String(12), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("structured_content", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_agent_messages_conversation_id", "agent_messages", ["conversation_id"], schema="financial")
    op.create_table("agent_runs", sa.Column("run_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("message_id", sa.UUID(), sa.ForeignKey("financial.agent_messages.message_id"), nullable=False), sa.Column("intent", sa.String(40), nullable=False), sa.Column("policy_decision", sa.String(30), nullable=False), sa.Column("model_used", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"], schema="financial")
    op.create_table("agent_tool_calls", sa.Column("tool_call_id", sa.UUID(), primary_key=True), sa.Column("run_id", sa.UUID(), sa.ForeignKey("financial.agent_runs.run_id"), nullable=False), sa.Column("tool_name", sa.String(80), nullable=False), sa.Column("tool_version", sa.String(30), nullable=False), sa.Column("sanitized_input_hash", sa.String(64), nullable=False), sa.Column("outcome", sa.String(20), nullable=False), sa.Column("result_reference", sa.String(120)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_agent_tool_calls_run_id", "agent_tool_calls", ["run_id"], schema="financial")
    op.create_table("financial_facts", sa.Column("fact_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("fact_type", sa.String(60), nullable=False), sa.Column("value", sa.Numeric(20, 4), nullable=False), sa.Column("unit", sa.String(12), nullable=False), sa.Column("source_type", sa.String(30), nullable=False), sa.Column("source_id", sa.String(120)), sa.Column("verification_status", sa.String(20), nullable=False), sa.Column("confidence", sa.Numeric(5, 4)), sa.Column("sensitivity_classification", sa.String(20), nullable=False), sa.Column("supersedes_fact_id", sa.UUID(), sa.ForeignKey("financial.financial_facts.fact_id")), sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False), sa.Column("verified_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_financial_facts_user_id", "financial_facts", ["user_id"], schema="financial")
    op.create_table("calculation_records", sa.Column("calculation_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("calculation_type", sa.String(60), nullable=False), sa.Column("calculation_version", sa.String(30), nullable=False), sa.Column("inputs", postgresql.JSONB(), nullable=False), sa.Column("assumptions", postgresql.JSONB(), nullable=False), sa.Column("result", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_calculation_records_user_id", "calculation_records", ["user_id"], schema="financial")
    op.create_table("proactive_reviews", sa.Column("review_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("finding_type", sa.String(60), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("evidence", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), sa.Column("acknowledged_at", sa.DateTime(timezone=True)), schema="financial")
    op.create_index("ix_proactive_reviews_user_id", "proactive_reviews", ["user_id"], schema="financial")
    op.create_table("agent_confirmations", sa.Column("confirmation_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("financial.agent_conversations.conversation_id"), nullable=False), sa.Column("action_type", sa.String(60), nullable=False), sa.Column("action_payload_hash", sa.String(64), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)), schema="financial")
    op.create_index("ix_agent_confirmations_user_id", "agent_confirmations", ["user_id"], schema="financial")
    op.create_table("audit_events", sa.Column("event_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), nullable=False), sa.Column("event_type", sa.String(60), nullable=False), sa.Column("target_type", sa.String(60), nullable=False), sa.Column("target_id", sa.String(120), nullable=False), sa.Column("outcome", sa.String(20), nullable=False), sa.Column("metadata_json", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="audit")
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], schema="audit")


def downgrade() -> None:
    for schema, table in (("audit", "audit_events"), ("financial", "agent_confirmations"), ("financial", "proactive_reviews"), ("financial", "calculation_records"), ("financial", "financial_facts"), ("financial", "agent_tool_calls"), ("financial", "agent_runs"), ("financial", "agent_messages"), ("financial", "agent_conversations")):
        op.drop_table(table, schema=schema)
