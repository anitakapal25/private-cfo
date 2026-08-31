"""Add confirmed action plans.

Revision ID: a41f7832c9d0
Revises: 90d4c2e8a731
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a41f7832c9d0"
down_revision = "90d4c2e8a731"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("action_plans", sa.Column("plan_id", sa.UUID(), primary_key=True), sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_action_plans_user_id", "action_plans", ["user_id"], schema="financial")
    op.create_table("planned_actions", sa.Column("action_id", sa.UUID(), primary_key=True), sa.Column("plan_id", sa.UUID(), sa.ForeignKey("financial.action_plans.plan_id"), nullable=False), sa.Column("action_type", sa.String(50), nullable=False), sa.Column("monthly_amount", sa.Numeric(20, 4), nullable=False), sa.Column("currency", sa.String(12), nullable=False), sa.Column("rank", sa.Numeric(8, 4), nullable=False), sa.Column("rationale", sa.Text(), nullable=False), sa.Column("impact", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")
    op.create_index("ix_planned_actions_plan_id", "planned_actions", ["plan_id"], schema="financial")


def downgrade() -> None:
    op.drop_table("planned_actions", schema="financial")
    op.drop_table("action_plans", schema="financial")
