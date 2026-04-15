"""Add today-suggestion support to pulse card enums."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012_pulse_today_suggestion_card"
down_revision = "0011_pulse_yesterday_summary_card"
branch_labels = None
depends_on = None

old_pulse_card_type = sa.Enum(
    "signal_change",
    "stalled_progress",
    "deadline_risk",
    "next_action",
    "yesterday_summary",
    "related_paper",
    name="pulsecardtype",
    native_enum=False,
)

new_pulse_card_type = sa.Enum(
    "signal_change",
    "stalled_progress",
    "deadline_risk",
    "today_suggestion",
    "next_action",
    "yesterday_summary",
    "related_paper",
    name="pulsecardtype",
    native_enum=False,
)


def upgrade() -> None:
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.alter_column(
            "card_type",
            existing_type=old_pulse_card_type,
            type_=new_pulse_card_type,
            existing_nullable=False,
        )
    with op.batch_alter_table("pulse_digest_items") as batch_op:
        batch_op.alter_column(
            "card_type",
            existing_type=old_pulse_card_type,
            type_=new_pulse_card_type,
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("pulse_digest_items") as batch_op:
        batch_op.alter_column(
            "card_type",
            existing_type=new_pulse_card_type,
            type_=old_pulse_card_type,
            existing_nullable=False,
        )
    with op.batch_alter_table("pulse_cards") as batch_op:
        batch_op.alter_column(
            "card_type",
            existing_type=new_pulse_card_type,
            type_=old_pulse_card_type,
            existing_nullable=False,
        )
