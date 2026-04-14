"""Add scheduler lifecycle, heartbeat, and delivery observability tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryAttemptStatus,
    PulseJobScheduledReason,
    WorkerRole,
    WorkerStatus,
)

revision = "0003_ops_observability_scheduler"
down_revision = "0002_pulse_scoring_fields"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("subscription_policies") as batch_op:
        batch_op.create_index(
            "ix_subscription_policies_frequency_enabled",
            ["frequency", "enabled"],
            unique=False,
        )

    with op.batch_alter_table("pulse_jobs") as batch_op:
        batch_op.add_column(sa.Column("subscription_policy_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("source_pulse_job_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "scheduled_reason",
                sa.Enum(PulseJobScheduledReason, native_enum=False),
                nullable=False,
                server_default=PulseJobScheduledReason.MANUAL_RUN.value,
            )
        )
        batch_op.add_column(sa.Column("schedule_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("lease_owner", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_pulse_jobs_subscription_policy_id_subscription_policies",
            "subscription_policies",
            ["subscription_policy_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_pulse_jobs_source_pulse_job_id_pulse_jobs",
            "pulse_jobs",
            ["source_pulse_job_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint("uq_pulse_jobs_schedule_key", ["schedule_key"])

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worker_name", sa.String(length=255), nullable=False),
        sa.Column("worker_role", sa.Enum(WorkerRole, native_enum=False), nullable=False),
        sa.Column("status", sa.Enum(WorkerStatus, native_enum=False), nullable=False),
        sa.Column("hostname_or_instance", sa.String(length=255), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", json_variant, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "worker_name",
            "hostname_or_instance",
            name="uq_worker_heartbeat_name_host",
        ),
    )

    op.create_table(
        "delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delivery_job_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Enum(ChannelType, native_enum=False), nullable=False),
        sa.Column("adapter_name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(DeliveryAttemptStatus, native_enum=False),
            nullable=False,
        ),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["delivery_job_id"], ["delivery_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "delivery_job_id",
            "attempt_number",
            name="uq_delivery_attempt_job_number",
        ),
    )


def downgrade() -> None:
    op.drop_table("delivery_attempts")
    op.drop_table("worker_heartbeats")

    with op.batch_alter_table("pulse_jobs") as batch_op:
        batch_op.drop_constraint("uq_pulse_jobs_schedule_key", type_="unique")
        batch_op.drop_constraint(
            "fk_pulse_jobs_source_pulse_job_id_pulse_jobs",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_pulse_jobs_subscription_policy_id_subscription_policies",
            type_="foreignkey",
        )
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_owner")
        batch_op.drop_column("failed_at")
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("schedule_key")
        batch_op.drop_column("scheduled_reason")
        batch_op.drop_column("source_pulse_job_id")
        batch_op.drop_column("subscription_policy_id")

    with op.batch_alter_table("subscription_policies") as batch_op:
        batch_op.drop_index("ix_subscription_policies_frequency_enabled")
