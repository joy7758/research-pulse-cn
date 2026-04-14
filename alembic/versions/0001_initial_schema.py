"""Initial schema for Research Pulse CN."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryJobStatus,
    PaperType,
    PulseCardType,
    PulseJobStatus,
    SignalSource,
    SubscriptionFrequency,
)

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("field", sa.String(length=255), nullable=True),
        sa.Column("interests", json_variant, nullable=False),
        sa.Column("watched_topics", json_variant, nullable=False),
        sa.Column("watched_venues", json_variant, nullable=False),
        sa.Column("reminder_preferences", json_variant, nullable=False),
        sa.Column("risk_thresholds", json_variant, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "paper_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("title_zh", sa.String(length=500), nullable=True),
        sa.Column("title_en", sa.String(length=500), nullable=True),
        sa.Column("type", sa.Enum(PaperType, native_enum=False), nullable=False),
        sa.Column("stage", sa.String(length=255), nullable=False),
        sa.Column("venue", sa.String(length=255), nullable=True),
        sa.Column("identifiers", json_variant, nullable=False),
        sa.Column("source_links", json_variant, nullable=False),
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_action", sa.String(length=500), nullable=True),
        sa.Column("blocker", sa.String(length=500), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "subscription_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("frequency", sa.Enum(SubscriptionFrequency, native_enum=False), nullable=False),
        sa.Column("quiet_hours", json_variant, nullable=True),
        sa.Column("frequency_cap", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("policy", json_variant, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pulse_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum(PulseJobStatus, native_enum=False), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "progress_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(length=255), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_links", json_variant, nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "signal_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.Enum(SignalSource, native_enum=False), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=True),
        sa.Column("read_count", sa.Integer(), nullable=True),
        sa.Column("inclusion_status", sa.String(length=255), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pulse_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pulse_job_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("card_type", sa.Enum(PulseCardType, native_enum=False), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("why_now", sa.Text(), nullable=False),
        sa.Column("action_text", sa.String(length=500), nullable=True),
        sa.Column("deep_link", sa.String(length=500), nullable=True),
        sa.Column("evidence_refs", json_variant, nullable=False),
        sa.Column("generated_by", json_variant, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pulse_job_id"], ["pulse_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "delivery_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pulse_card_id", sa.Uuid(), nullable=True),
        sa.Column("pulse_job_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("idem_key", sa.String(length=255), nullable=False),
        sa.Column("payload", json_variant, nullable=False),
        sa.Column("status", sa.Enum(DeliveryJobStatus, native_enum=False), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pulse_card_id"], ["pulse_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pulse_job_id"], ["pulse_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idem_key"),
    )


def downgrade() -> None:
    op.drop_table("delivery_jobs")
    op.drop_table("pulse_cards")
    op.drop_table("signal_snapshots")
    op.drop_table("progress_events")
    op.drop_table("pulse_jobs")
    op.drop_table("subscription_policies")
    op.drop_table("paper_profiles")
    op.drop_table("user_profiles")
