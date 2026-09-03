"""Add public authentication controls.

Revision ID: a6c31d8e91f2
Revises: f3e84c1a2b90
"""

from alembic import op
import sqlalchemy as sa


revision = "a6c31d8e91f2"
down_revision = "f3e84c1a2b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "date_of_birth", nullable=True, schema="financial")
    op.alter_column("users", "employment_status", nullable=True, schema="financial")
    op.alter_column("profiles", "full_name", nullable=True, schema="financial")
    op.alter_column("profiles", "phone_number", nullable=True, schema="financial")
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"), schema="financial")
    op.add_column("users", sa.Column("lockout_count", sa.Integer(), nullable=False, server_default="0"), schema="financial")
    op.add_column("users", sa.Column("lockout_until", sa.DateTime(timezone=True)), schema="financial")

    op.create_table(
        "auth_sessions",
        sa.Column("session_id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("parent_session_id", sa.UUID(), sa.ForeignKey("financial.auth_sessions.session_id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_reason", sa.String(length=40)),
        schema="financial",
    )
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at"], schema="financial")
    op.create_table(
        "auth_challenges",
        sa.Column("challenge_id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False),
        sa.Column("challenge_type", sa.String(length=40), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        schema="financial",
    )
    op.create_index("ix_auth_challenges_user_type", "auth_challenges", ["user_id", "challenge_type"], schema="financial")
    op.create_table(
        "mfa_credentials",
        sa.Column("credential_id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("financial.users.user_id"), nullable=False),
        sa.Column("encrypted_totp_secret", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_used_step", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        schema="financial",
    )
    op.create_index("uq_mfa_credentials_user", "mfa_credentials", ["user_id"], unique=True, schema="financial")
    op.create_table(
        "auth_rate_limit_events",
        sa.Column("event_id", sa.UUID(), primary_key=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("subject_hash", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema="financial",
    )
    op.create_index("ix_auth_rate_limit_subject_time", "auth_rate_limit_events", ["subject_hash", "occurred_at"], schema="financial")


def downgrade() -> None:
    op.drop_index("ix_auth_rate_limit_subject_time", table_name="auth_rate_limit_events", schema="financial")
    op.drop_table("auth_rate_limit_events", schema="financial")
    op.drop_index("uq_mfa_credentials_user", table_name="mfa_credentials", schema="financial")
    op.drop_table("mfa_credentials", schema="financial")
    op.drop_index("ix_auth_challenges_user_type", table_name="auth_challenges", schema="financial")
    op.drop_table("auth_challenges", schema="financial")
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions", schema="financial")
    op.drop_table("auth_sessions", schema="financial")
    op.drop_column("users", "lockout_until", schema="financial")
    op.drop_column("users", "lockout_count", schema="financial")
    op.drop_column("users", "failed_login_count", schema="financial")
    op.alter_column("profiles", "phone_number", nullable=False, schema="financial")
    op.alter_column("profiles", "full_name", nullable=False, schema="financial")
    op.alter_column("users", "employment_status", nullable=False, schema="financial")
    op.alter_column("users", "date_of_birth", nullable=False, schema="financial")
