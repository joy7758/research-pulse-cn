"""Add group workspace and result sharing tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    GroupWorkspaceMemberRole,
    GroupWorkspaceStatus,
    ResultShareGrantStatus,
    ResultShareKind,
)

revision = "0022_group_workspace_result_sharing"
down_revision = "0021_mini_self_service_editor_handoff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(GroupWorkspaceStatus, native_enum=False),
            nullable=False,
            server_default=GroupWorkspaceStatus.ACTIVE.value,
        ),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"], ["admin_accounts.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "group_workspace_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(GroupWorkspaceMemberRole, native_enum=False),
            nullable=False,
            server_default=GroupWorkspaceMemberRole.VIEWER.value,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_group_workspace_members_workspace_user",
        ),
    )
    op.create_table(
        "group_workspace_papers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["added_by_admin_id"], ["admin_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "paper_id",
            name="uq_group_workspace_papers_workspace_paper",
        ),
    )
    op.create_table(
        "result_share_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "share_kind",
            sa.Enum(ResultShareKind, native_enum=False),
            nullable=False,
        ),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=True),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(ResultShareGrantStatus, native_enum=False),
            nullable=False,
            server_default=ResultShareGrantStatus.ACTIVE.value,
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"], ["pulse_digest_issues.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["issued_by_admin_id"], ["admin_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_result_share_grants_kind_status_created_at",
        "result_share_grants",
        ["share_kind", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_result_share_grants_workspace_created_at",
        "result_share_grants",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_result_share_grants_workspace_created_at",
        table_name="result_share_grants",
    )
    op.drop_index(
        "ix_result_share_grants_kind_status_created_at",
        table_name="result_share_grants",
    )
    op.drop_table("result_share_grants")
    op.drop_table("group_workspace_papers")
    op.drop_table("group_workspace_members")
    op.drop_table("group_workspaces")
