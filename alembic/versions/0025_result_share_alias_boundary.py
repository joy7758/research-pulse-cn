"""Add result share alias boundary table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import ResultShareAliasStatus

revision = "0025_result_share_alias_boundary"
down_revision = "0024_group_workspace_result_collect_reserve"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "result_share_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("result_share_grant_id", sa.Uuid(), nullable=False),
        sa.Column("alias_hash", sa.String(length=255), nullable=False),
        sa.Column("alias_prefix", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(ResultShareAliasStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_share_grant_id"],
            ["result_share_grants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_admin_id"],
            ["admin_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias_hash"),
    )
    op.create_index(
        "ix_result_share_aliases_status_created_at",
        "result_share_aliases",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_result_share_aliases_result_share_grant_created_at",
        "result_share_aliases",
        ["result_share_grant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_result_share_aliases_result_share_grant_created_at",
        table_name="result_share_aliases",
    )
    op.drop_index(
        "ix_result_share_aliases_status_created_at",
        table_name="result_share_aliases",
    )
    op.drop_table("result_share_aliases")
