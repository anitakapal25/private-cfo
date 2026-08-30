"""Enforce one authoritative fact per user and fact type.

Revision ID: 90d4c2e8a731
Revises: 7b2c9e4d1a60
"""

from alembic import op
import sqlalchemy as sa

revision = "90d4c2e8a731"
down_revision = "7b2c9e4d1a60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_financial_facts_verified_type", "financial_facts",
        ["user_id", "fact_type"], unique=True, schema="financial",
        postgresql_where=sa.text("verification_status = 'verified'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_financial_facts_verified_type",
        table_name="financial_facts", schema="financial",
    )
