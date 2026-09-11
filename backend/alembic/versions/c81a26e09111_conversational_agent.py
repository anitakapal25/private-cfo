"""Bounded conversation state and durable request reservations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "c81a26e09111"
down_revision = "f4b7c2d9a101"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("agent_conversations", sa.Column("conversation_state", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), schema="financial")
    op.create_table("agent_requests",
        sa.Column("request_id", sa.UUID(), primary_key=True),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("financial.agent_conversations.conversation_id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False),
        sa.Column("client_request_id", sa.UUID(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")), schema="financial")
    op.create_index("uq_agent_request_identity", "agent_requests", ["conversation_id", "client_request_id"], unique=True, schema="financial")

def downgrade():
    op.drop_table("agent_requests", schema="financial")
    op.drop_column("agent_conversations", "conversation_state", schema="financial")
