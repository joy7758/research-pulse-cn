"""Repositories for mini read grants and compact mini-read queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import MiniReadGrant
from research_pulse_cn.domain.enums import MiniReadGrantStatus, MiniReadGrantType


class MiniRepository:
    """Persistence access for mini-program read-only reserve objects."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        status: MiniReadGrantStatus | None = None,
        grant_type: MiniReadGrantType | None = None,
        digest_issue_id: UUID | None = None,
        binding_id: UUID | None = None,
    ) -> list[MiniReadGrant]:
        statement = (
            select(MiniReadGrant)
            .options(
                selectinload(MiniReadGrant.user),
                selectinload(MiniReadGrant.binding),
                selectinload(MiniReadGrant.digest_issue),
                selectinload(MiniReadGrant.created_by_admin),
            )
            .order_by(MiniReadGrant.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(MiniReadGrant.user_id == user_id)
        if status is not None:
            statement = statement.where(MiniReadGrant.status == status)
        if grant_type is not None:
            statement = statement.where(MiniReadGrant.grant_type == grant_type)
        if digest_issue_id is not None:
            statement = statement.where(MiniReadGrant.digest_issue_id == digest_issue_id)
        if binding_id is not None:
            statement = statement.where(MiniReadGrant.binding_id == binding_id)
        return list(self.session.scalars(statement))

    def get_grant(self, grant_id: UUID) -> MiniReadGrant | None:
        statement = (
            select(MiniReadGrant)
            .options(
                selectinload(MiniReadGrant.user),
                selectinload(MiniReadGrant.binding),
                selectinload(MiniReadGrant.digest_issue),
                selectinload(MiniReadGrant.created_by_admin),
            )
            .where(MiniReadGrant.id == grant_id)
        )
        return self.session.scalar(statement)

    def get_grant_by_token_hash(self, token_hash: str) -> MiniReadGrant | None:
        statement = (
            select(MiniReadGrant)
            .options(
                selectinload(MiniReadGrant.user),
                selectinload(MiniReadGrant.binding),
                selectinload(MiniReadGrant.digest_issue),
            )
            .where(MiniReadGrant.token_hash == token_hash)
        )
        return self.session.scalar(statement)

    def add_grant(self, grant: MiniReadGrant) -> MiniReadGrant:
        self.session.add(grant)
        self.session.flush()
        self.session.refresh(grant)
        return grant

    def list_active_grants(self, *, user_id: UUID, as_of: datetime) -> list[MiniReadGrant]:
        statement = (
            select(MiniReadGrant)
            .where(
                MiniReadGrant.user_id == user_id,
                MiniReadGrant.status == MiniReadGrantStatus.ACTIVE,
            )
            .where((MiniReadGrant.expires_at.is_(None)) | (MiniReadGrant.expires_at > as_of))
            .order_by(MiniReadGrant.created_at.desc())
        )
        return list(self.session.scalars(statement))
