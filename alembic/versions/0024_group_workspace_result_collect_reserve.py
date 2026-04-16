"""Add group workspace result collect reserve table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import GroupWorkspaceResultCollectStatus, ResultShareKind

revision = "0024_group_workspace_result_collect_reserve"
down_revision = "0023_group_workspace_invite_join"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_workspace_result_collect_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("result_share_grant_id", sa.Uuid(), nullable=True),
        sa.Column("share_kind", sa.Enum(ResultShareKind, native_enum=False), nullable=False),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=True),
        sa.Column("source_pulse_card_id", sa.Uuid(), nullable=True),
        sa.Column("source_paper_id", sa.Uuid(), nullable=True),
        sa.Column("collected_paper_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(GroupWorkspaceResultCollectStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("reason_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["result_share_grant_id"],
            ["result_share_grants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"],
            ["pulse_digest_issues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_pulse_card_id"],
            ["pulse_cards.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_paper_id"],
            ["paper_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["collected_paper_id"],
            ["paper_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_group_workspace_result_collect_idempotency",
        ),
    )
    op.create_index(
        "ix_group_workspace_result_collect_records_workspace_status_created_at",
        "group_workspace_result_collect_records",
        ["workspace_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_group_workspace_result_collect_records_workspace_status_created_at",
        table_name="group_workspace_result_collect_records",
    )
    op.drop_table("group_workspace_result_collect_records")
