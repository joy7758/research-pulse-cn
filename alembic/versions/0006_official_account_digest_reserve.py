"""Add WeChat binding, digest issue, digest item, and publication reserve tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    PulseCardType,
    PulseDigestIssueStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
)

revision = "0006_official_account_digest_reserve"
down_revision = "0005_sync_foundation"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "wechat_identity_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel_type",
            sa.Enum(WeChatBindingChannelType, native_enum=False),
            nullable=False,
        ),
        sa.Column("app_id", sa.String(length=255), nullable=False),
        sa.Column("openid", sa.String(length=255), nullable=False),
        sa.Column("unionid", sa.String(length=255), nullable=True),
        sa.Column(
            "bind_state",
            sa.Enum(WeChatBindingState, native_enum=False),
            nullable=False,
            server_default=WeChatBindingState.PENDING.value,
        ),
        sa.Column("subscribed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_label", sa.String(length=255), nullable=True),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", json_variant, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel_type",
            "app_id",
            "openid",
            name="uq_wechat_identity_bindings_channel_app_openid",
        ),
    )
    op.create_index(
        "ix_wechat_identity_bindings_unionid",
        "wechat_identity_bindings",
        ["unionid"],
        unique=False,
    )
    op.create_index(
        "ix_wechat_identity_bindings_user_id",
        "wechat_identity_bindings",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "pulse_digest_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("source_pulse_job_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(PulseDigestIssueStatus, native_enum=False),
            nullable=False,
            server_default=PulseDigestIssueStatus.DRAFT.value,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("highlight_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_card_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deep_link_path", sa.String(length=500), nullable=True),
        sa.Column("content_payload", json_variant, nullable=False),
        sa.Column("build_metadata", json_variant, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_pulse_job_id"], ["pulse_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "issue_date", name="uq_pulse_digest_issues_user_issue_date"),
    )
    op.create_index(
        "ix_pulse_digest_issues_user_date",
        "pulse_digest_issues",
        ["user_id", "issue_date"],
        unique=False,
    )

    op.create_table(
        "pulse_digest_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=False),
        sa.Column("pulse_card_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("card_type", sa.Enum(PulseCardType, native_enum=False), nullable=False),
        sa.Column("source_paper_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("why_now", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"], ["pulse_digest_issues.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pulse_card_id"], ["pulse_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_paper_id"], ["paper_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "digest_issue_id",
            "pulse_card_id",
            name="uq_pulse_digest_items_issue_card",
        ),
    )
    op.create_index(
        "ix_pulse_digest_items_issue_sort_order",
        "pulse_digest_items",
        ["digest_issue_id", "sort_order"],
        unique=False,
    )

    op.create_table(
        "digest_publication_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column(
            "publish_target",
            sa.Enum(DigestPublicationTarget, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(DigestPublicationStatus, native_enum=False),
            nullable=False,
            server_default=DigestPublicationStatus.PENDING.value,
        ),
        sa.Column(
            "publish_mode",
            sa.Enum(DigestPublicationMode, native_enum=False),
            nullable=False,
            server_default=DigestPublicationMode.MANUAL_PREVIEW.value,
        ),
        sa.Column("provider_name", sa.String(length=255), nullable=False, server_default="stub"),
        sa.Column("payload", json_variant, nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["binding_id"], ["wechat_identity_bindings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"], ["pulse_digest_issues.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "digest_issue_id",
            "binding_id",
            "publish_target",
            name="uq_digest_publication_jobs_issue_binding_target",
        ),
    )
    op.create_index(
        "ix_digest_publication_jobs_issue_status",
        "digest_publication_jobs",
        ["digest_issue_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_digest_publication_jobs_issue_status", table_name="digest_publication_jobs")
    op.drop_table("digest_publication_jobs")
    op.drop_index("ix_pulse_digest_items_issue_sort_order", table_name="pulse_digest_items")
    op.drop_table("pulse_digest_items")
    op.drop_index("ix_pulse_digest_issues_user_date", table_name="pulse_digest_issues")
    op.drop_table("pulse_digest_issues")
    op.drop_index(
        "ix_wechat_identity_bindings_user_id",
        table_name="wechat_identity_bindings",
    )
    op.drop_index(
        "ix_wechat_identity_bindings_unionid",
        table_name="wechat_identity_bindings",
    )
    op.drop_table("wechat_identity_bindings")
