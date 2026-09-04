"""Add action tracking dates, states, and manual check-ins.

Revision ID: f4b7c2d9a101
Revises: e7c41b92d5a0
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4b7c2d9a101"
down_revision = "e7c41b92d5a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("planned_actions", sa.Column("start_date", sa.Date(), nullable=True), schema="financial")
    op.add_column("planned_actions", sa.Column("target_date", sa.Date(), nullable=True), schema="financial")
    op.add_column("planned_actions", sa.Column("target_amount", sa.Numeric(20, 4), nullable=True), schema="financial")
    op.add_column("planned_actions", sa.Column("priority_label", sa.String(12), nullable=False, server_default="medium"), schema="financial")
    op.add_column("planned_actions", sa.Column("difficulty_label", sa.String(12), nullable=False, server_default="manageable"), schema="financial")
    op.add_column("planned_actions", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")), schema="financial")
    op.add_column("planned_actions", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True), schema="financial")
    op.add_column("planned_actions", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True), schema="financial")
    op.execute("UPDATE financial.planned_actions SET status = CASE WHEN status = 'planned' THEN 'active' ELSE status END, start_date = created_at::date, target_date = created_at::date, target_amount = monthly_amount")
    op.alter_column("planned_actions", "start_date", nullable=False, schema="financial")
    op.alter_column("planned_actions", "target_date", nullable=False, schema="financial")
    op.alter_column("planned_actions", "target_amount", nullable=False, schema="financial")
    op.execute("""
        WITH ranked AS (
          SELECT plan_id, row_number() OVER (PARTITION BY user_id ORDER BY created_at DESC, plan_id DESC) AS position
          FROM financial.action_plans WHERE status = 'active'
        )
        UPDATE financial.action_plans p SET status = 'archived'
        FROM ranked r WHERE p.plan_id = r.plan_id AND r.position > 1
    """)
    op.create_index("uq_one_active_action_plan_per_user", "action_plans", ["user_id"], unique=True, schema="financial", postgresql_where=sa.text("status = 'active'"))
    op.create_table(
        "action_check_ins",
        sa.Column("check_in_id", sa.UUID(), primary_key=True),
        sa.Column("action_id", sa.UUID(), sa.ForeignKey("financial.planned_actions.action_id"), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency", sa.String(12), nullable=False, server_default="INR"),
        sa.Column("check_in_date", sa.Date(), nullable=False),
        sa.Column("note", sa.String(240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="financial",
    )
    op.create_index("ix_action_check_ins_action_id", "action_check_ins", ["action_id"], schema="financial")


def downgrade() -> None:
    op.drop_table("action_check_ins", schema="financial")
    op.drop_index("uq_one_active_action_plan_per_user", table_name="action_plans", schema="financial")
    for column in ("archived_at", "completed_at", "updated_at", "difficulty_label", "priority_label", "target_amount", "target_date", "start_date"):
        op.drop_column("planned_actions", column, schema="financial")
