"""Add group workspace invite grant and claim tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
)

revision = "0023_group_workspace_invite_join"
down_revision = "0022_group_workspace_result_sharing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_workspace_invite_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role_to_assign",
            sa.Enum(GroupWorkspaceInviteRole, native_enum=False),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(GroupWorkspaceInviteGrantStatus, native_enum=False),
            nullable=False,
            server_default=GroupWorkspaceInviteGrantStatus.ACTIVE.value,
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("max_claims", sa.Integer(), nullable=True),
        sa.Column("claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["issued_by_admin_id"], ["admin_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_group_workspace_invite_grants_workspace_status_created_at",
        "group_workspace_invite_grants",
        ["workspace_id", "status", "created_at"],
        unique=False,
    )

    op.create_table(
        "group_workspace_invite_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invite_grant_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=True),
        sa.Column(
            "role_assigned",
            sa.Enum(GroupWorkspaceInviteRole, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "claim_status",
            sa.Enum(GroupWorkspaceInviteClaimStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("reason_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["invite_grant_id"],
            ["group_workspace_invite_grants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["group_workspace_members.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["group_workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "invite_grant_id",
            "user_id",
            name="uq_group_workspace_invite_claims_grant_user",
        ),
    )
    op.create_index(
        "ix_group_workspace_invite_claims_workspace_created_at",
        "group_workspace_invite_claims",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_group_workspace_invite_claims_workspace_created_at",
        table_name="group_workspace_invite_claims",
    )
    op.drop_table("group_workspace_invite_claims")
    op.drop_index(
        "ix_group_workspace_invite_grants_workspace_status_created_at",
        table_name="group_workspace_invite_grants",
    )
    op.drop_table("group_workspace_invite_grants")
