"""Extend official-account binding handshake sessions for OAuth completion."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from research_pulse_cn.domain.enums import OfficialAccountOAuthScope

revision = "0020_official_account_oauth_completion"
down_revision = "0019_official_account_binding_handshake_reserve"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column(
            "requested_scope",
            sa.Enum(OfficialAccountOAuthScope, native_enum=False),
            nullable=False,
            server_default=OfficialAccountOAuthScope.SNSAPI_BASE.value,
        ),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column(
            "authorized_scope",
            sa.Enum(OfficialAccountOAuthScope, native_enum=False),
            nullable=True,
        ),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column("oauth_openid_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column("authorization_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column("oauth_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column(
            "userinfo_fetched",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "official_account_binding_handshake_sessions",
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("official_account_binding_handshake_sessions", "last_error")
    op.drop_column("official_account_binding_handshake_sessions", "userinfo_fetched")
    op.drop_column("official_account_binding_handshake_sessions", "oauth_completed_at")
    op.drop_column("official_account_binding_handshake_sessions", "authorization_started_at")
    op.drop_column("official_account_binding_handshake_sessions", "oauth_openid_hash")
    op.drop_column("official_account_binding_handshake_sessions", "authorized_scope")
    op.drop_column("official_account_binding_handshake_sessions", "requested_scope")
