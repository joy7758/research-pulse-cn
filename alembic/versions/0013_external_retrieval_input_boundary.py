"""Add external retrieval input planning table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ExternalRetrievalPlanStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
)

revision = "0013_external_retrieval_input_boundary"
down_revision = "0012_pulse_today_suggestion_card"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "external_retrieval_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.Column("watch_profile_id", sa.Uuid(), nullable=True),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column("plan_label", sa.String(length=255), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_payload", json_variant, nullable=False),
        sa.Column("effective_inputs", json_variant, nullable=False),
        sa.Column("reason_codes", json_variant, nullable=False),
        sa.Column("plan_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(ExternalRetrievalPlanStatus, native_enum=False),
            nullable=False,
            server_default=ExternalRetrievalPlanStatus.PLANNED.value,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["watch_profile_id"],
            ["research_watch_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_hash", name="uq_external_retrieval_plans_plan_hash"),
    )
    op.create_index(
        "ix_external_retrieval_plans_user_source",
        "external_retrieval_plans",
        ["user_id", "source_kind", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieval_plans_scope",
        "external_retrieval_plans",
        ["retrieval_scope"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieval_plans_paper",
        "external_retrieval_plans",
        ["paper_id"],
        unique=False,
    )
    op.create_index(
        "ix_external_retrieval_plans_watch_profile",
        "external_retrieval_plans",
        ["watch_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_external_retrieval_plans_watch_profile",
        table_name="external_retrieval_plans",
    )
    op.drop_index(
        "ix_external_retrieval_plans_paper",
        table_name="external_retrieval_plans",
    )
    op.drop_index(
        "ix_external_retrieval_plans_scope",
        table_name="external_retrieval_plans",
    )
    op.drop_index(
        "ix_external_retrieval_plans_user_source",
        table_name="external_retrieval_plans",
    )
    op.drop_table("external_retrieval_plans")
