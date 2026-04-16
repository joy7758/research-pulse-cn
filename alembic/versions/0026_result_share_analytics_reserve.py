"""Add result share analytics reserve table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ResultShareKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
    ResultShareViewOutcome,
)

revision = "0026_result_share_analytics_reserve"
down_revision = "0025_result_share_alias_boundary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "result_share_view_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("result_share_grant_id", sa.Uuid(), nullable=True),
        sa.Column("result_share_alias_id", sa.Uuid(), nullable=True),
        sa.Column(
            "share_kind",
            sa.Enum(ResultShareKind, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "access_mode",
            sa.Enum(ResultShareViewAccessMode, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(ResultShareViewEventType, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.Enum(ResultShareViewOutcome, native_enum=False),
            nullable=False,
        ),
        sa.Column("request_fingerprint_hash", sa.String(length=255), nullable=True),
        sa.Column("referrer_host", sa.String(length=255), nullable=True),
        sa.Column("user_agent_family", sa.String(length=128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_share_grant_id"],
            ["result_share_grants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["result_share_alias_id"],
            ["result_share_aliases.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_result_share_view_events_occurred_at",
        "result_share_view_events",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_result_share_view_events_result_share_grant_occurred_at",
        "result_share_view_events",
        ["result_share_grant_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_result_share_view_events_result_share_alias_occurred_at",
        "result_share_view_events",
        ["result_share_alias_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_result_share_view_events_result_share_alias_occurred_at",
        table_name="result_share_view_events",
    )
    op.drop_index(
        "ix_result_share_view_events_result_share_grant_occurred_at",
        table_name="result_share_view_events",
    )
    op.drop_index(
        "ix_result_share_view_events_occurred_at",
        table_name="result_share_view_events",
    )
    op.drop_table("result_share_view_events")
