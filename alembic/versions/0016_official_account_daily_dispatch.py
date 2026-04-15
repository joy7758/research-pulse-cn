"""Add issue-level official-account digest dispatch runs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    DigestDispatchMode,
    DigestDispatchRunStatus,
    DigestPublicationTarget,
    OfficialAccountProviderMode,
)

revision = "0016_official_account_daily_dispatch"
down_revision = "0015_pulse_related_paper_candidates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digest_dispatch_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("digest_issue_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "publish_target",
            sa.Enum(DigestPublicationTarget, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "dispatch_mode",
            sa.Enum(DigestDispatchMode, native_enum=False),
            nullable=False,
            server_default=DigestDispatchMode.MANUAL.value,
        ),
        sa.Column(
            "provider_mode",
            sa.Enum(OfficialAccountProviderMode, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(DigestDispatchRunStatus, native_enum=False),
            nullable=False,
            server_default=DigestDispatchRunStatus.PENDING.value,
        ),
        sa.Column("total_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("previewed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["digest_issue_id"], ["pulse_digest_issues.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_digest_dispatch_runs_issue_target_status",
        "digest_dispatch_runs",
        ["digest_issue_id", "publish_target", "status"],
        unique=False,
    )
    op.create_index(
        "ix_digest_dispatch_runs_user_created_at",
        "digest_dispatch_runs",
        ["user_id", "created_at"],
        unique=False,
    )

    with op.batch_alter_table("digest_publication_attempts") as batch_op:
        batch_op.add_column(sa.Column("dispatch_run_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_digest_publication_attempts_dispatch_run_id",
            "digest_dispatch_runs",
            ["dispatch_run_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("digest_publication_attempts") as batch_op:
        batch_op.drop_constraint(
            "fk_digest_publication_attempts_dispatch_run_id",
            type_="foreignkey",
        )
        batch_op.drop_column("dispatch_run_id")

    op.drop_index("ix_digest_dispatch_runs_user_created_at", table_name="digest_dispatch_runs")
    op.drop_index(
        "ix_digest_dispatch_runs_issue_target_status",
        table_name="digest_dispatch_runs",
    )
    op.drop_table("digest_dispatch_runs")
