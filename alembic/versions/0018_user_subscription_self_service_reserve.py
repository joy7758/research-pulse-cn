"""Add subscription self-service reserve grants."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import ChannelType, SubscriptionSelfServiceGrantStatus

revision = "0018_user_subscription_self_service_reserve"
down_revision = "0017_subscription_boundary_quiet_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_self_service_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("grant_scope", sa.JSON(), nullable=True),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(SubscriptionSelfServiceGrantStatus, native_enum=False),
            nullable=False,
            server_default=SubscriptionSelfServiceGrantStatus.ACTIVE.value,
        ),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["wechat_identity_bindings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_admin_id"],
            ["admin_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_subscription_self_service_grants_token_hash"),
    )
    op.create_index(
        "ix_subscription_self_service_grants_user_channel_created_at",
        "subscription_self_service_grants",
        ["user_id", "channel", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_self_service_grants_status_expires_at",
        "subscription_self_service_grants",
        ["status", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_subscription_self_service_grants_status_expires_at",
        table_name="subscription_self_service_grants",
    )
    op.drop_index(
        "ix_subscription_self_service_grants_user_channel_created_at",
        table_name="subscription_self_service_grants",
    )
    op.drop_table("subscription_self_service_grants")
