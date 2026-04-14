"""Add official-account callback events and publication attempts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    DigestPublicationAttemptStatus,
    OfficialAccountCallbackPayloadFormat,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
)

revision = "0008_official_account_provider_boundary"
down_revision = "0007_mini_program_readonly_reserve"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "digest_publication_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(length=255), nullable=False),
        sa.Column(
            "provider_mode",
            sa.Enum(OfficialAccountProviderMode, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(DigestPublicationAttemptStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("request_payload", json_variant, nullable=True),
        sa.Column("response_payload", json_variant, nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["digest_publication_job_id"],
            ["digest_publication_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "digest_publication_job_id",
            "attempt_number",
            name="uq_digest_publication_attempts_job_attempt",
        ),
    )
    op.create_index(
        "ix_digest_publication_attempts_job_started_at",
        "digest_publication_attempts",
        ["digest_publication_job_id", "started_at"],
        unique=False,
    )

    op.create_table(
        "official_account_callback_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("app_id", sa.String(length=255), nullable=True),
        sa.Column("to_user_name", sa.String(length=255), nullable=True),
        sa.Column("from_openid", sa.String(length=255), nullable=True),
        sa.Column("msg_type", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=True),
        sa.Column("event_key", sa.String(length=255), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "payload_format",
            sa.Enum(OfficialAccountCallbackPayloadFormat, native_enum=False),
            nullable=False,
            server_default=OfficialAccountCallbackPayloadFormat.UNKNOWN.value,
        ),
        sa.Column("raw_payload", sa.Text(), nullable=False),
        sa.Column("parsed_payload", json_variant, nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum(OfficialAccountCallbackProcessingStatus, native_enum=False),
            nullable=False,
            server_default=OfficialAccountCallbackProcessingStatus.ACCEPTED.value,
        ),
        sa.Column("processing_note", sa.Text(), nullable=True),
        sa.Column("linked_binding_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["linked_binding_id"],
            ["wechat_identity_bindings.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dedupe_key",
            name="uq_official_account_callback_events_dedupe_key",
        ),
    )
    op.create_index(
        "ix_official_account_callback_events_binding_created_at",
        "official_account_callback_events",
        ["linked_binding_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_official_account_callback_events_from_openid",
        "official_account_callback_events",
        ["from_openid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_official_account_callback_events_from_openid",
        table_name="official_account_callback_events",
    )
    op.drop_index(
        "ix_official_account_callback_events_binding_created_at",
        table_name="official_account_callback_events",
    )
    op.drop_table("official_account_callback_events")
    op.drop_index(
        "ix_digest_publication_attempts_job_started_at",
        table_name="digest_publication_attempts",
    )
    op.drop_table("digest_publication_attempts")
