"""Add proactive review traceability and lifecycle.

Revision ID: b52d6f91e804
Revises: a41f7832c9d0
"""

from alembic import op
import sqlalchemy as sa

revision = "b52d6f91e804"
down_revision = "a41f7832c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proactive_reviews", sa.Column("rule_version", sa.String(30), server_default="proactive-review-v1", nullable=False), schema="financial")
    op.add_column("proactive_reviews", sa.Column("dedup_key", sa.String(64), server_default="legacy", nullable=False), schema="financial")
    op.add_column("proactive_reviews", sa.Column("dismissed_at", sa.DateTime(timezone=True)), schema="financial")
    op.create_index("ix_proactive_reviews_dedup_key", "proactive_reviews", ["dedup_key"], schema="financial")


def downgrade() -> None:
    op.drop_index("ix_proactive_reviews_dedup_key", table_name="proactive_reviews", schema="financial")
    op.drop_column("proactive_reviews", "dismissed_at", schema="financial")
    op.drop_column("proactive_reviews", "dedup_key", schema="financial")
    op.drop_column("proactive_reviews", "rule_version", schema="financial")
