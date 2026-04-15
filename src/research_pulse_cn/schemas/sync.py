"""Sync device and event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    ClientType,
    SyncEventSource,
    SyncEventType,
    SyncMutationStatus,
)
from research_pulse_cn.schemas.common import ORMModel


class ClientDeviceCreateRequest(BaseModel):
    user_id: UUID
    client_type: ClientType
    display_name: str = Field(min_length=1, max_length=255)


class ClientDeviceRead(BaseModel):
    id: UUID
    user_id: UUID
    client_type: ClientType
    display_name: str
    is_active: bool
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_event_sequence: int = 0
    last_synced_at: datetime | None = None


class ClientDeviceTokenIssueResponse(BaseModel):
    device: ClientDeviceRead
    plain_text_token: str
    expires_at: datetime | None


class ClientDeviceRevokeResponse(BaseModel):
    device: ClientDeviceRead
    revoked_at: datetime


class SyncUserSummary(BaseModel):
    id: UUID
    name: str
    email: str | None
    field: str | None


class SyncMeResponse(BaseModel):
    device: ClientDeviceRead
    user: SyncUserSummary


class SyncEventRead(ORMModel):
    id: UUID
    sequence: int
    user_id: UUID
    entity_type: str
    entity_id: str
    event_type: SyncEventType
    payload: dict[str, Any]
    event_source: SyncEventSource
    occurred_at: datetime


class SyncFeedResponse(BaseModel):
    events: list[SyncEventRead]
    next_after_sequence: int
    has_more: bool


class SyncAckRequest(BaseModel):
    last_event_sequence: int = Field(ge=0)


class SyncAckResponse(BaseModel):
    last_event_sequence: int
    last_synced_at: datetime | None


class SyncMutationRequest(BaseModel):
    client_mutation_id: str = Field(min_length=1, max_length=255)
    mutation_type: str = Field(min_length=1, max_length=100)
    resource_type: str = Field(min_length=1, max_length=100)
    resource_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class SyncPushRequest(BaseModel):
    mutations: list[SyncMutationRequest] = Field(default_factory=list)


class SyncMutationResultRead(BaseModel):
    client_mutation_id: str
    status: SyncMutationStatus
    error_message: str | None
    resulting_event_sequence: int | None


class SyncPushResponse(BaseModel):
    results: list[SyncMutationResultRead]
