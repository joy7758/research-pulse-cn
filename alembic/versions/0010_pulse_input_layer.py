"""Add work activity events and research watch profiles."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import (
    ResearchWatchProfileSourceMode,
    WorkActivitySource,
    WorkActivityType,
)

revision = "0010_pulse_input_layer"
down_revision = "0009_official_account_real_send"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "work_activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column(
            "activity_type",
            sa.Enum(WorkActivityType, native_enum=False),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata", json_variant, nullable=True),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.Enum(WorkActivitySource, native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_activity_events_user_happened_at",
        "work_activity_events",
        ["user_id", "happened_at"],
        unique=False,
    )
    op.create_index(
        "ix_work_activity_events_paper_happened_at",
        "work_activity_events",
        ["paper_id", "happened_at"],
        unique=False,
    )
    op.create_index(
        "ix_work_activity_events_activity_type",
        "work_activity_events",
        ["activity_type"],
        unique=False,
    )

    op.create_table(
        "research_watch_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("paper_id", sa.Uuid(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "source_mode",
            sa.Enum(ResearchWatchProfileSourceMode, native_enum=False),
            nullable=False,
            server_default=ResearchWatchProfileSourceMode.MANUAL.value,
        ),
        sa.Column("topics", json_variant, nullable=False),
        sa.Column("keywords", json_variant, nullable=False),
        sa.Column("venues", json_variant, nullable=False),
        sa.Column("authors_of_interest", json_variant, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["paper_id"], ["paper_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_research_watch_profiles_user_enabled",
        "research_watch_profiles",
        ["user_id", "enabled"],
        unique=False,
    )
    op.create_index(
        "ix_research_watch_profiles_paper",
        "research_watch_profiles",
        ["paper_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_research_watch_profiles_paper",
        table_name="research_watch_profiles",
    )
    op.drop_index(
        "ix_research_watch_profiles_user_enabled",
        table_name="research_watch_profiles",
    )
    op.drop_table("research_watch_profiles")

    op.drop_index(
        "ix_work_activity_events_activity_type",
        table_name="work_activity_events",
    )
    op.drop_index(
        "ix_work_activity_events_paper_happened_at",
        table_name="work_activity_events",
    )
    op.drop_index(
        "ix_work_activity_events_user_happened_at",
        table_name="work_activity_events",
    )
    op.drop_table("work_activity_events")
