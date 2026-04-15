"""Add external retrieval execution run and result tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ExternalRetrievalRunStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
)

revision = "0014_external_retrieval_execution"
down_revision = "0013_external_retrieval_input_boundary"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "external_retrieval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_kind",
            sa.Enum(ExternalRetrievalSourceKind, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "retrieval_scope",
            sa.Enum(ExternalRetrievalScope, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(ExternalRetrievalRunStatus, native_enum=False),
            nullable=False,
            server_default=ExternalRetrievalRunStatus.PENDING.value,
        ),
        sa.Column("request_url", sa.Text(), nullable=True),
        sa.Column("request_payload", json_variant, nullable=True),
        sa.Column("response_summary", json_variant, nullable=True),
        sa.Column("raw_result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("normalized_result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["external_retrieval_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_retrieval_runs_plan_status",
        "external_retrieval_runs",
        ["plan_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieval_runs_user_source",
        "external_retrieval_runs",
        ["user_id", "source_kind", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieval_runs_scope",
        "external_retrieval_runs",
        ["retrieval_scope"],
        unique=False,
    )

    op.create_table(
        "external_retrieved_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_kind",
            sa.Enum(ExternalRetrievalSourceKind, native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "retrieval_scope",
            sa.Enum(ExternalRetrievalScope, native_enum=False),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=500), nullable=False),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract_snippet", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("publication_date", sa.String(length=64), nullable=True),
        sa.Column("source_title", sa.String(length=500), nullable=True),
        sa.Column("authors", json_variant, nullable=True),
        sa.Column("matched_reason_codes", json_variant, nullable=True),
        sa.Column("raw_payload", json_variant, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["external_retrieval_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["external_retrieval_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "external_id",
            name="uq_external_retrieved_records_run_external_id",
        ),
    )
    op.create_index(
        "ix_external_retrieved_records_user_source",
        "external_retrieved_records",
        ["user_id", "source_kind", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieved_records_run_sort",
        "external_retrieved_records",
        ["run_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieved_records_plan",
        "external_retrieved_records",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieved_records_scope",
        "external_retrieved_records",
        ["retrieval_scope"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_external_retrieved_records_scope",
        table_name="external_retrieved_records",
    )
    op.drop_index(
        "ix_external_retrieved_records_plan",
        table_name="external_retrieved_records",
    )
    op.drop_index(
        "ix_external_retrieved_records_run_sort",
        table_name="external_retrieved_records",
    )
    op.drop_index(
        "ix_external_retrieved_records_user_source",
        table_name="external_retrieved_records",
    )
    op.drop_table("external_retrieved_records")

    op.drop_index(
        "ix_external_retrieval_runs_scope",
        table_name="external_retrieval_runs",
    )
    op.drop_index(
        "ix_external_retrieval_runs_user_source",
        table_name="external_retrieval_runs",
    )
    op.drop_index(
        "ix_external_retrieval_runs_plan_status",
        table_name="external_retrieval_runs",
    )
    op.drop_table("external_retrieval_runs")
