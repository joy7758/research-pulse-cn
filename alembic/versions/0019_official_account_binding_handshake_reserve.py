"""Add official-account binding handshake reserve sessions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ChannelType,
    OfficialAccountBindingHandshakeSessionStatus,
)

revision = "0019_official_account_binding_handshake_reserve"
down_revision = "0018_user_subscription_self_service_reserve"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_account_binding_handshake_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("app_id", sa.String(length=255), nullable=False),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("self_service_grant_id", sa.Uuid(), nullable=True),
        sa.Column("issued_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("state_token_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(OfficialAccountBindingHandshakeSessionStatus, native_enum=False),
            nullable=False,
            server_default=OfficialAccountBindingHandshakeSessionStatus.PENDING.value,
        ),
        sa.Column("matched_callback_event_id", sa.Uuid(), nullable=True),
        sa.Column("claimed_binding_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["claimed_binding_id"],
            ["wechat_identity_bindings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_admin_id"],
            ["admin_accounts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["matched_callback_event_id"],
            ["official_account_callback_events.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["self_service_grant_id"],
            ["subscription_self_service_grants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "state_token_hash",
            name="uq_official_account_binding_handshake_sessions_state_token_hash",
        ),
    )
    op.create_index(
        "ix_oa_binding_handshake_sessions_user_channel_created_at",
        "official_account_binding_handshake_sessions",
        ["user_id", "channel", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_oa_binding_handshake_sessions_status_expires_at",
        "official_account_binding_handshake_sessions",
        ["status", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_oa_binding_handshake_sessions_status_expires_at",
        table_name="official_account_binding_handshake_sessions",
    )
    op.drop_index(
        "ix_oa_binding_handshake_sessions_user_channel_created_at",
        table_name="official_account_binding_handshake_sessions",
    )
    op.drop_table("official_account_binding_handshake_sessions")
