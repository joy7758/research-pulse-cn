"""Add mini self-service editor handoff grants."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ChannelType,
    SubscriptionEditorHandoffGrantStatus,
    SubscriptionEditorHandoffIssuedBy,
)

revision = "0021_mini_self_service_editor_handoff"
down_revision = "0020_official_account_oauth_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_editor_handoff_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(ChannelType, native_enum=False),
            nullable=False,
        ),
        sa.Column("mini_grant_id", sa.Uuid(), nullable=True),
        sa.Column("self_service_grant_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(SubscriptionEditorHandoffGrantStatus, native_enum=False),
            nullable=False,
            server_default=SubscriptionEditorHandoffGrantStatus.ACTIVE.value,
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column(
            "issued_by",
            sa.Enum(SubscriptionEditorHandoffIssuedBy, native_enum=False),
            nullable=False,
            server_default=SubscriptionEditorHandoffIssuedBy.MINI_HANDOFF.value,
        ),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["binding_id"], ["wechat_identity_bindings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["issued_by_admin_id"], ["admin_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mini_grant_id"], ["mini_read_grants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["self_service_grant_id"],
            ["subscription_self_service_grants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        "ix_subscription_editor_handoff_grants_user_channel_created_at",
        "subscription_editor_handoff_grants",
        ["user_id", "channel", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_editor_handoff_grants_status_expires_at",
        "subscription_editor_handoff_grants",
        ["status", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_editor_handoff_grants_status_expires_at",
        table_name="subscription_editor_handoff_grants",
    )
    op.drop_index(
        "ix_subscription_editor_handoff_grants_user_channel_created_at",
        table_name="subscription_editor_handoff_grants",
    )
    op.drop_table("subscription_editor_handoff_grants")
