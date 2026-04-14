"""Add sync devices, tokens, events, cursors, and mutations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ClientType,
    SyncEventSource,
    SyncEventType,
    SyncMutationStatus,
)

revision = "0005_sync_foundation"
down_revision = "0004_auth_admin_boundary"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "client_devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_type", sa.Enum(ClientType, native_enum=False), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_devices_user_id", "client_devices", ["user_id"], unique=False)

    op.create_table(
        "client_access_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_device_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_ip", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["client_device_id"], ["client_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_client_access_tokens_token_hash"),
    )

    op.create_table(
        "sync_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.Enum(SyncEventType, native_enum=False), nullable=False),
        sa.Column("payload", json_variant, nullable=False),
        sa.Column("event_source", sa.Enum(SyncEventSource, native_enum=False), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sequence", name="uq_sync_events_sequence"),
    )
    op.create_index(
        "ix_sync_events_user_sequence",
        "sync_events",
        ["user_id", "sequence"],
        unique=False,
    )

    op.create_table(
        "sync_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_device_id", sa.Uuid(), nullable=False),
        sa.Column(
            "last_event_sequence",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_device_id"], ["client_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_device_id", name="uq_sync_cursors_client_device_id"),
    )

    op.create_table(
        "sync_mutations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_device_id", sa.Uuid(), nullable=False),
        sa.Column("client_mutation_id", sa.String(length=255), nullable=False),
        sa.Column("mutation_type", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("payload", json_variant, nullable=False),
        sa.Column(
            "status",
            sa.Enum(SyncMutationStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("resulting_event_sequence", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_device_id"], ["client_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_device_id",
            "client_mutation_id",
            name="uq_sync_mutations_device_client_mutation",
        ),
    )


def downgrade() -> None:
    op.drop_table("sync_mutations")
    op.drop_table("sync_cursors")
    op.drop_index("ix_sync_events_user_sequence", table_name="sync_events")
    op.drop_table("sync_events")
    op.drop_table("client_access_tokens")
    op.drop_index("ix_client_devices_user_id", table_name="client_devices")
    op.drop_table("client_devices")
