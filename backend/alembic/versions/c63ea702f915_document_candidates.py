"""Add normalized document candidates.

Revision ID: c63ea702f915
Revises: b52d6f91e804
"""

from alembic import op
import sqlalchemy as sa

revision = "c63ea702f915"
down_revision = "b52d6f91e804"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_document_storage_document_id",
        "document_storage",
        ["document_id"],
        schema="documents",
    )
    op.create_table("document_candidates", sa.Column("candidate_id", sa.UUID(), primary_key=True), sa.Column("document_id", sa.UUID(), sa.ForeignKey("documents.document_storage.document_id"), nullable=False), sa.Column("user_id", sa.UUID(), nullable=False), sa.Column("fact_type", sa.String(60), nullable=False), sa.Column("value", sa.Numeric(20, 4), nullable=False), sa.Column("unit", sa.String(12), nullable=False), sa.Column("confidence", sa.Numeric(5, 4), nullable=False), sa.Column("source_location", sa.String(100)), sa.Column("status", sa.String(20), nullable=False), sa.Column("linked_fact_id", sa.UUID(), sa.ForeignKey("financial.financial_facts.fact_id")), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False), sa.Column("decided_at", sa.DateTime(timezone=True)), schema="documents")
    op.create_index("ix_document_candidates_document_id", "document_candidates", ["document_id"], schema="documents")
    op.create_index("ix_document_candidates_user_id", "document_candidates", ["user_id"], schema="documents")


def downgrade() -> None:
    op.drop_table("document_candidates", schema="documents")
    op.drop_constraint(
        "uq_document_storage_document_id",
        "document_storage",
        schema="documents",
        type_="unique",
    )
