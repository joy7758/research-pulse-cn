"""Add external reference persistence for related-paper pulse cards."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_pulse_related_paper_candidates"
down_revision = "0014_external_retrieval_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.add_column(sa.Column("external_reference_key", sa.String(length=500)))


def downgrade() -> None:
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.drop_column("external_reference_key")
