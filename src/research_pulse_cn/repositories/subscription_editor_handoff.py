"""Persistence operations for short-lived subscription editor handoff grants."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import SubscriptionEditorHandoffGrant
from research_pulse_cn.domain.enums import (
    ChannelType,
    SubscriptionEditorHandoffGrantStatus,
)


class SubscriptionEditorHandoffRepository:
    """Load and persist editor handoff grants."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: SubscriptionEditorHandoffGrantStatus | None = None,
        mini_grant_id: UUID | None = None,
        self_service_grant_id: UUID | None = None,
    ) -> list[SubscriptionEditorHandoffGrant]:
        statement = (
            select(SubscriptionEditorHandoffGrant)
            .options(
                selectinload(SubscriptionEditorHandoffGrant.user),
                selectinload(SubscriptionEditorHandoffGrant.binding),
                selectinload(SubscriptionEditorHandoffGrant.mini_grant),
                selectinload(SubscriptionEditorHandoffGrant.self_service_grant),
                selectinload(SubscriptionEditorHandoffGrant.issued_by_admin),
            )
            .order_by(
                SubscriptionEditorHandoffGrant.created_at.desc(),
                SubscriptionEditorHandoffGrant.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(SubscriptionEditorHandoffGrant.user_id == user_id)
        if channel is not None:
            statement = statement.where(SubscriptionEditorHandoffGrant.channel == channel)
        if status is not None:
            statement = statement.where(SubscriptionEditorHandoffGrant.status == status)
        if mini_grant_id is not None:
            statement = statement.where(
                SubscriptionEditorHandoffGrant.mini_grant_id == mini_grant_id
            )
        if self_service_grant_id is not None:
            statement = statement.where(
                SubscriptionEditorHandoffGrant.self_service_grant_id == self_service_grant_id
            )
        return list(self.session.scalars(statement))

    def get_grant(self, grant_id: UUID) -> SubscriptionEditorHandoffGrant | None:
        statement = (
            select(SubscriptionEditorHandoffGrant)
            .options(
                selectinload(SubscriptionEditorHandoffGrant.user),
                selectinload(SubscriptionEditorHandoffGrant.binding),
                selectinload(SubscriptionEditorHandoffGrant.mini_grant),
                selectinload(SubscriptionEditorHandoffGrant.self_service_grant),
                selectinload(SubscriptionEditorHandoffGrant.issued_by_admin),
            )
            .where(SubscriptionEditorHandoffGrant.id == grant_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_grant_by_token_hash(self, token_hash: str) -> SubscriptionEditorHandoffGrant | None:
        statement = (
            select(SubscriptionEditorHandoffGrant)
            .options(
                selectinload(SubscriptionEditorHandoffGrant.user),
                selectinload(SubscriptionEditorHandoffGrant.binding),
                selectinload(SubscriptionEditorHandoffGrant.mini_grant),
                selectinload(SubscriptionEditorHandoffGrant.self_service_grant),
            )
            .where(SubscriptionEditorHandoffGrant.token_hash == token_hash)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_grant(
        self,
        grant: SubscriptionEditorHandoffGrant,
    ) -> SubscriptionEditorHandoffGrant:
        self.session.add(grant)
        self.session.flush()
        self.session.refresh(grant)
        return grant

    def list_active_grants(
        self,
        *,
        user_id: UUID,
        channel: ChannelType,
        as_of: datetime,
        mini_grant_id: UUID | None = None,
    ) -> list[SubscriptionEditorHandoffGrant]:
        statement = (
            select(SubscriptionEditorHandoffGrant)
            .where(
                SubscriptionEditorHandoffGrant.user_id == user_id,
                SubscriptionEditorHandoffGrant.channel == channel,
                SubscriptionEditorHandoffGrant.status
                == SubscriptionEditorHandoffGrantStatus.ACTIVE,
            )
            .where(
                (SubscriptionEditorHandoffGrant.expires_at.is_(None))
                | (SubscriptionEditorHandoffGrant.expires_at > as_of)
            )
            .order_by(
                SubscriptionEditorHandoffGrant.created_at.desc(),
                SubscriptionEditorHandoffGrant.id.desc(),
            )
        )
        if mini_grant_id is not None:
            statement = statement.where(
                SubscriptionEditorHandoffGrant.mini_grant_id == mini_grant_id
            )
        return list(self.session.scalars(statement))
