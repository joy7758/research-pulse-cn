"""Add digest delivery decisions for subscription boundary controls."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import ChannelType, DigestDeliveryDecisionStatus

revision = "0017_subscription_boundary_quiet_control"
down_revision = "0016_official_account_daily_dispatch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digest_delivery_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("subscription_policy_id", sa.Uuid(), nullable=True),
        sa.Column("dispatch_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "decision",
            sa.Enum(DigestDeliveryDecisionStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("reason_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("effective_timezone", sa.String(length=100), nullable=False),
        sa.Column("local_issue_weekday", sa.Integer(), nullable=True),
        sa.Column("selected_card_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_card_type", sa.String(length=100), nullable=True),
        sa.Column("quiet_hours", sa.JSON(), nullable=True),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"],
            ["pulse_digest_issues.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_policy_id"],
            ["subscription_policies.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["dispatch_run_id"],
            ["digest_dispatch_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_digest_delivery_decisions_issue_channel_created_at",
        "digest_delivery_decisions",
        ["digest_issue_id", "channel", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_digest_delivery_decisions_user_channel_created_at",
        "digest_delivery_decisions",
        ["user_id", "channel", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_digest_delivery_decisions_user_channel_created_at",
        table_name="digest_delivery_decisions",
    )
    op.drop_index(
        "ix_digest_delivery_decisions_issue_channel_created_at",
        table_name="digest_delivery_decisions",
    )
    op.drop_table("digest_delivery_decisions")
