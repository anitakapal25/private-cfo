"""Add period-aware verified financial memory.

Revision ID: e7c41b92d5a0
Revises: a6c31d8e91f2
"""

from alembic import op
import sqlalchemy as sa


revision = "e7c41b92d5a0"
down_revision = "a6c31d8e91f2"
branch_labels = None
depends_on = None

MONTHLY_TYPES = "'monthly_income', 'monthly_expenses', 'monthly_debt_payments'"


def upgrade() -> None:
    op.add_column("financial_facts", sa.Column("period_kind", sa.String(12)), schema="financial")
    op.add_column("financial_facts", sa.Column("period_start", sa.Date()), schema="financial")
    op.execute(sa.text(
        f"""UPDATE financial.financial_facts
        SET period_kind = CASE WHEN fact_type IN ({MONTHLY_TYPES}) THEN 'monthly' ELSE 'as_of' END,
            period_start = CASE WHEN fact_type IN ({MONTHLY_TYPES})
                THEN date_trunc('month', observed_at)::date ELSE observed_at::date END"""
    ))
    op.alter_column("financial_facts", "period_kind", nullable=False, schema="financial")
    op.alter_column("financial_facts", "period_start", nullable=False, schema="financial")
    op.drop_index("uq_financial_facts_verified_type", table_name="financial_facts", schema="financial")
    op.create_check_constraint(
        "ck_financial_facts_period_kind", "financial_facts",
        "period_kind IN ('monthly', 'as_of')", schema="financial",
    )
    op.create_index(
        "uq_financial_facts_verified_month", "financial_facts",
        ["user_id", "fact_type", "period_start"], unique=True, schema="financial",
        postgresql_where=sa.text("verification_status = 'verified' AND period_kind = 'monthly'"),
    )
    op.create_index(
        "uq_financial_facts_verified_snapshot", "financial_facts",
        ["user_id", "fact_type"], unique=True, schema="financial",
        postgresql_where=sa.text("verification_status = 'verified' AND period_kind = 'as_of'"),
    )


def downgrade() -> None:
    op.drop_index("uq_financial_facts_verified_snapshot", table_name="financial_facts", schema="financial")
    op.drop_index("uq_financial_facts_verified_month", table_name="financial_facts", schema="financial")
    op.drop_constraint("ck_financial_facts_period_kind", "financial_facts", schema="financial", type_="check")
    op.execute(sa.text("""
        WITH ranked AS (
            SELECT fact_id, row_number() OVER (
                PARTITION BY user_id, fact_type
                ORDER BY period_start DESC, observed_at DESC, created_at DESC
            ) AS position
            FROM financial.financial_facts
            WHERE verification_status = 'verified'
        )
        UPDATE financial.financial_facts AS facts
        SET verification_status = 'superseded'
        FROM ranked
        WHERE facts.fact_id = ranked.fact_id AND ranked.position > 1
    """))
    op.create_index(
        "uq_financial_facts_verified_type", "financial_facts", ["user_id", "fact_type"],
        unique=True, schema="financial", postgresql_where=sa.text("verification_status = 'verified'"),
    )
    op.drop_column("financial_facts", "period_start", schema="financial")
    op.drop_column("financial_facts", "period_kind", schema="financial")
