"""Add agent message request idempotency.

Revision ID: d74fb83a10c2
Revises: c63ea702f915
"""

from alembic import op
import sqlalchemy as sa

revision = "d74fb83a10c2"
down_revision = "c63ea702f915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_messages", sa.Column("client_request_id", sa.UUID(), nullable=True),
        schema="financial",
    )
    op.create_index(
        "uq_agent_message_client_request", "agent_messages",
        ["conversation_id", "client_request_id"], unique=True, schema="financial",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_agent_message_client_request", table_name="agent_messages",
        schema="financial",
    )
    op.drop_column("agent_messages", "client_request_id", schema="financial")
