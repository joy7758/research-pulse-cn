"""Add mini read grants for compact read-only mini-program reserve access."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import MiniReadGrantStatus, MiniReadGrantType

revision = "0007_mini_program_readonly_reserve"
down_revision = "0006_official_account_digest_reserve"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "mini_read_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=True),
        sa.Column(
            "grant_type",
            sa.Enum(MiniReadGrantType, native_enum=False),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(MiniReadGrantStatus, native_enum=False),
            nullable=False,
            server_default=MiniReadGrantStatus.ACTIVE.value,
        ),
        sa.Column("scope", json_variant, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["wechat_identity_bindings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admin_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"],
            ["pulse_digest_issues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_mini_read_grants_token_hash"),
    )
    op.create_index(
        "ix_mini_read_grants_user_id",
        "mini_read_grants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_mini_read_grants_status_expires_at",
        "mini_read_grants",
        ["status", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mini_read_grants_status_expires_at", table_name="mini_read_grants")
    op.drop_index("ix_mini_read_grants_user_id", table_name="mini_read_grants")
    op.drop_table("mini_read_grants")
