"""Refresh token repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import AdminRefreshToken


class AdminRefreshTokenRepository:
    """Persistence operations for admin refresh tokens."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, token: AdminRefreshToken) -> AdminRefreshToken:
        self.session.add(token)
        self.session.flush()
        self.session.refresh(token)
        return token

    def get(self, refresh_token_id: UUID) -> AdminRefreshToken | None:
        statement = (
            select(AdminRefreshToken)
            .options(selectinload(AdminRefreshToken.admin_account))
            .where(AdminRefreshToken.id == refresh_token_id)
        )
        return self.session.scalar(statement)

    def get_by_token_hash(self, token_hash: str) -> AdminRefreshToken | None:
        statement = (
            select(AdminRefreshToken)
            .options(selectinload(AdminRefreshToken.admin_account))
            .where(AdminRefreshToken.token_hash == token_hash)
        )
        return self.session.scalar(statement)

    def list_active_for_admin(
        self,
        admin_account_id: UUID,
        *,
        as_of: datetime,
    ) -> list[AdminRefreshToken]:
        statement = (
            select(AdminRefreshToken)
            .where(
                AdminRefreshToken.admin_account_id == admin_account_id,
                AdminRefreshToken.revoked_at.is_(None),
                AdminRefreshToken.expires_at > as_of,
            )
            .order_by(AdminRefreshToken.issued_at.desc())
        )
        return list(self.session.scalars(statement))
