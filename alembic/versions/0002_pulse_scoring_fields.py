"""Add explainable scoring fields to pulse cards."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_pulse_scoring_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

json_variant = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.add_column(sa.Column("source_paper_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column("score_total", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column(
                "score_breakdown",
                json_variant,
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch_op.add_column(sa.Column("candidate_metadata", json_variant, nullable=True))
        batch_op.create_foreign_key(
            "fk_pulse_cards_source_paper_id_paper_profiles",
            "paper_profiles",
            ["source_paper_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.drop_constraint(
            "fk_pulse_cards_source_paper_id_paper_profiles",
            type_="foreignkey",
        )
        batch_op.drop_column("candidate_metadata")
        batch_op.drop_column("score_breakdown")
        batch_op.drop_column("score_total")
        batch_op.drop_column("source_paper_id")
