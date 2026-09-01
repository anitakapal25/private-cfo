"""Add conversation-scoped external-model consent.

Revision ID: f3e84c1a2b90
Revises: d74fb83a10c2
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f3e84c1a2b90"
down_revision = "d74fb83a10c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_model_consents",
        sa.Column("consent_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("purpose", sa.String(length=120), nullable=False),
        sa.Column("policy_bundle_version", sa.String(length=40), nullable=False),
        sa.Column("data_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["financial.users.user_id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["financial.agent_conversations.conversation_id"]),
        schema="financial",
    )
    op.create_index("ix_agent_model_consents_user_id", "agent_model_consents", ["user_id"], schema="financial")
    op.create_index("uq_agent_model_consent_conversation", "agent_model_consents", ["conversation_id"], unique=True, schema="financial")


def downgrade() -> None:
    op.drop_index("uq_agent_model_consent_conversation", table_name="agent_model_consents", schema="financial")
    op.drop_index("ix_agent_model_consents_user_id", table_name="agent_model_consents", schema="financial")
    op.drop_table("agent_model_consents", schema="financial")
