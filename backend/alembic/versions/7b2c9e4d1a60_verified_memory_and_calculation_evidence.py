"""Add verified-memory evidence and calculation traceability.

Revision ID: 7b2c9e4d1a60
Revises: 4f8a1d7c2e91
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7b2c9e4d1a60"
down_revision = "4f8a1d7c2e91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_sources",
        sa.Column("evidence_source_id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_reference", sa.String(120)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema="financial",
    )
    op.create_index("ix_evidence_sources_user_id", "evidence_sources", ["user_id"], schema="financial")
    op.add_column("financial_facts", sa.Column("evidence_source_id", sa.UUID()), schema="financial")
    op.create_foreign_key(
        "fk_financial_facts_evidence_source", "financial_facts", "evidence_sources",
        ["evidence_source_id"], ["evidence_source_id"], source_schema="financial", referent_schema="financial",
    )
    op.add_column("calculation_records", sa.Column("input_provenance", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), schema="financial")
    op.add_column("calculation_records", sa.Column("rule_versions", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), schema="financial")
    op.add_column("calculation_records", sa.Column("limitations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), schema="financial")
    op.add_column("calculation_records", sa.Column("as_of", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), schema="financial")


def downgrade() -> None:
    for column in ("as_of", "limitations", "rule_versions", "input_provenance"):
        op.drop_column("calculation_records", column, schema="financial")
    op.drop_constraint("fk_financial_facts_evidence_source", "financial_facts", schema="financial", type_="foreignkey")
    op.drop_column("financial_facts", "evidence_source_id", schema="financial")
    op.drop_index("ix_evidence_sources_user_id", table_name="evidence_sources", schema="financial")
    op.drop_table("evidence_sources", schema="financial")
