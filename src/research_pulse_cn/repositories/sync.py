"""Repositories for sync devices, tokens, events, cursors, and mutations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    ClientAccessToken,
    ClientDevice,
    SyncCursor,
    SyncEvent,
    SyncMutation,
)
from research_pulse_cn.domain.enums import ClientType


class SyncRepository:
    """Persistence operations for sync state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_devices(
        self,
        *,
        user_id: UUID | None = None,
        client_type: ClientType | None = None,
        is_active: bool | None = None,
    ) -> list[ClientDevice]:
        statement = (
            select(ClientDevice)
            .options(
                selectinload(ClientDevice.cursor),
                selectinload(ClientDevice.access_tokens),
                selectinload(ClientDevice.user),
            )
            .order_by(ClientDevice.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(ClientDevice.user_id == user_id)
        if client_type is not None:
            statement = statement.where(ClientDevice.client_type == client_type)
        if is_active is not None:
            statement = statement.where(ClientDevice.is_active.is_(is_active))
        return list(self.session.scalars(statement))

    def get_device(self, client_device_id: UUID) -> ClientDevice | None:
        statement = (
            select(ClientDevice)
            .options(
                selectinload(ClientDevice.cursor),
                selectinload(ClientDevice.access_tokens),
                selectinload(ClientDevice.user),
            )
            .where(ClientDevice.id == client_device_id)
        )
        return self.session.scalar(statement)

    def add_device(self, client_device: ClientDevice) -> ClientDevice:
        self.session.add(client_device)
        self.session.flush()
        self.session.refresh(client_device)
        return client_device

    def add_access_token(self, access_token: ClientAccessToken) -> ClientAccessToken:
        self.session.add(access_token)
        self.session.flush()
        self.session.refresh(access_token)
        return access_token

    def get_access_token_by_hash(self, token_hash: str) -> ClientAccessToken | None:
        statement = (
            select(ClientAccessToken)
            .options(
                selectinload(ClientAccessToken.client_device).selectinload(ClientDevice.user),
                selectinload(ClientAccessToken.client_device).selectinload(ClientDevice.cursor),
            )
            .where(ClientAccessToken.token_hash == token_hash)
        )
        return self.session.scalar(statement)

    def list_active_access_tokens(
        self,
        client_device_id: UUID,
        *,
        as_of: datetime,
    ) -> list[ClientAccessToken]:
        statement = (
            select(ClientAccessToken)
            .where(ClientAccessToken.client_device_id == client_device_id)
            .where(ClientAccessToken.revoked_at.is_(None))
            .where(
                (ClientAccessToken.expires_at.is_(None)) | (ClientAccessToken.expires_at > as_of)
            )
            .order_by(ClientAccessToken.issued_at.desc())
        )
        return list(self.session.scalars(statement))

    def get_cursor(self, client_device_id: UUID) -> SyncCursor | None:
        statement = select(SyncCursor).where(SyncCursor.client_device_id == client_device_id)
        return self.session.scalar(statement)

    def add_cursor(self, cursor: SyncCursor) -> SyncCursor:
        self.session.add(cursor)
        self.session.flush()
        self.session.refresh(cursor)
        return cursor

    def add_event(self, sync_event: SyncEvent) -> SyncEvent:
        sync_event.sequence = self.next_event_sequence()
        self.session.add(sync_event)
        self.session.flush()
        self.session.refresh(sync_event)
        return sync_event

    def next_event_sequence(self) -> int:
        statement = select(func.max(SyncEvent.sequence))
        return int(self.session.scalar(statement) or 0) + 1

    def list_events_after(
        self,
        *,
        user_id: UUID,
        after_sequence: int,
        limit: int,
    ) -> list[SyncEvent]:
        statement = (
            select(SyncEvent)
            .where(SyncEvent.user_id == user_id, SyncEvent.sequence > after_sequence)
            .order_by(SyncEvent.sequence.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def get_latest_event_for_entity(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: str,
    ) -> SyncEvent | None:
        statement = (
            select(SyncEvent)
            .where(
                SyncEvent.user_id == user_id,
                SyncEvent.entity_type == entity_type,
                SyncEvent.entity_id == entity_id,
            )
            .order_by(SyncEvent.sequence.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_mutation(self, mutation: SyncMutation) -> SyncMutation:
        self.session.add(mutation)
        self.session.flush()
        self.session.refresh(mutation)
        return mutation

    def get_mutation(
        self,
        *,
        client_device_id: UUID,
        client_mutation_id: str,
    ) -> SyncMutation | None:
        statement = (
            select(SyncMutation)
            .where(
                SyncMutation.client_device_id == client_device_id,
                SyncMutation.client_mutation_id == client_mutation_id,
            )
            .limit(1)
        )
        return self.session.scalar(statement)
