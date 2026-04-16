"""Add result share invite conversion bridge analytics fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import ResultShareHandoffTargetKind

revision = "0027_result_share_invite_conversion_bridge"
down_revision = "0026_result_share_analytics_reserve"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "result_share_view_events",
        sa.Column(
            "handoff_target_kind",
            sa.Enum(ResultShareHandoffTargetKind, native_enum=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("result_share_view_events", "handoff_target_kind")
