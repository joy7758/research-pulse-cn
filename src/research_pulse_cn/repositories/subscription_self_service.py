"""Persistence operations for subscription self-service grants."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import SubscriptionSelfServiceGrant
from research_pulse_cn.domain.enums import ChannelType, SubscriptionSelfServiceGrantStatus


class SubscriptionSelfServiceRepository:
    """Load and persist subscription self-service grants."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: SubscriptionSelfServiceGrantStatus | None = None,
        binding_id: UUID | None = None,
    ) -> list[SubscriptionSelfServiceGrant]:
        statement = (
            select(SubscriptionSelfServiceGrant)
            .options(
                selectinload(SubscriptionSelfServiceGrant.user),
                selectinload(SubscriptionSelfServiceGrant.binding),
                selectinload(SubscriptionSelfServiceGrant.issued_by_admin),
            )
            .order_by(
                SubscriptionSelfServiceGrant.created_at.desc(),
                SubscriptionSelfServiceGrant.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(SubscriptionSelfServiceGrant.user_id == user_id)
        if channel is not None:
            statement = statement.where(SubscriptionSelfServiceGrant.channel == channel)
        if status is not None:
            statement = statement.where(SubscriptionSelfServiceGrant.status == status)
        if binding_id is not None:
            statement = statement.where(SubscriptionSelfServiceGrant.binding_id == binding_id)
        return list(self.session.scalars(statement))

    def get_grant(self, grant_id: UUID) -> SubscriptionSelfServiceGrant | None:
        statement = (
            select(SubscriptionSelfServiceGrant)
            .options(
                selectinload(SubscriptionSelfServiceGrant.user),
                selectinload(SubscriptionSelfServiceGrant.binding),
                selectinload(SubscriptionSelfServiceGrant.issued_by_admin),
            )
            .where(SubscriptionSelfServiceGrant.id == grant_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_grant_by_token_hash(self, token_hash: str) -> SubscriptionSelfServiceGrant | None:
        statement = (
            select(SubscriptionSelfServiceGrant)
            .options(
                selectinload(SubscriptionSelfServiceGrant.user),
                selectinload(SubscriptionSelfServiceGrant.binding),
                selectinload(SubscriptionSelfServiceGrant.issued_by_admin),
            )
            .where(SubscriptionSelfServiceGrant.token_hash == token_hash)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_grant(
        self,
        grant: SubscriptionSelfServiceGrant,
    ) -> SubscriptionSelfServiceGrant:
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
    ) -> list[SubscriptionSelfServiceGrant]:
        statement = (
            select(SubscriptionSelfServiceGrant)
            .where(
                SubscriptionSelfServiceGrant.user_id == user_id,
                SubscriptionSelfServiceGrant.channel == channel,
                SubscriptionSelfServiceGrant.status == SubscriptionSelfServiceGrantStatus.ACTIVE,
            )
            .where(
                (SubscriptionSelfServiceGrant.expires_at.is_(None))
                | (SubscriptionSelfServiceGrant.expires_at > as_of)
            )
            .order_by(
                SubscriptionSelfServiceGrant.created_at.desc(),
                SubscriptionSelfServiceGrant.id.desc(),
            )
        )
        return list(self.session.scalars(statement))
