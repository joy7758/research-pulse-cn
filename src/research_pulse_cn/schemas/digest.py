"""Schemas for WeChat bindings, digest issues, and publication reserve jobs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    PulseCardType,
    PulseDigestIssueStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.schemas.common import ORMModel


class WeChatIdentityBindingCreate(BaseModel):
    user_id: UUID
    channel_type: WeChatBindingChannelType
    app_id: str = Field(min_length=1, max_length=255)
    openid: str = Field(min_length=1, max_length=255)
    unionid: str | None = Field(default=None, max_length=255)
    bind_state: WeChatBindingState = WeChatBindingState.PENDING
    subscribed: bool = False
    digest_enabled: bool = True
    display_label: str | None = Field(default=None, max_length=255)
    subscribed_at: datetime | None = None
    unsubscribed_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class WeChatIdentityBindingUpdate(BaseModel):
    unionid: str | None = Field(default=None, max_length=255)
    bind_state: WeChatBindingState | None = None
    subscribed: bool | None = None
    digest_enabled: bool | None = None
    display_label: str | None = Field(default=None, max_length=255)
    subscribed_at: datetime | None = None
    unsubscribed_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class WeChatIdentityBindingRead(ORMModel):
    id: UUID
    user_id: UUID
    channel_type: WeChatBindingChannelType
    app_id: str
    openid: str
    unionid: str | None
    bind_state: WeChatBindingState
    subscribed: bool
    digest_enabled: bool
    display_label: str | None
    subscribed_at: datetime | None
    unsubscribed_at: datetime | None
    last_seen_at: datetime | None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class PulseDigestItemRead(ORMModel):
    id: UUID
    digest_issue_id: UUID
    pulse_card_id: UUID
    sort_order: int
    card_type: PulseCardType
    source_paper_id: UUID | None
    title: str
    summary: str
    why_now: str | None
    created_at: datetime


class DigestPublicationJobRead(ORMModel):
    id: UUID
    digest_issue_id: UUID
    binding_id: UUID | None
    publish_target: DigestPublicationTarget
    status: DigestPublicationStatus
    publish_mode: DigestPublicationMode
    provider_name: str
    payload: dict[str, Any] | None
    external_message_id: str | None
    last_error: str | None
    prepared_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PulseDigestIssueRead(ORMModel):
    id: UUID
    user_id: UUID
    issue_date: date
    source_pulse_job_id: UUID | None
    status: PulseDigestIssueStatus
    title: str
    summary: str
    highlight_count: int
    selected_card_count: int
    deep_link_path: str | None
    content_payload: dict[str, Any]
    build_metadata: dict[str, Any] | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PulseDigestIssueDetailRead(PulseDigestIssueRead):
    items: list[PulseDigestItemRead] = Field(default_factory=list)
    publication_jobs: list[DigestPublicationJobRead] = Field(default_factory=list)


class DigestIssueBuildRequest(BaseModel):
    issue_date: date | None = None
    source_pulse_job_id: UUID | None = None


class DigestIssueBuildResponse(BaseModel):
    action: str
    issue: PulseDigestIssueDetailRead


class DigestPublicationPrepareResponse(BaseModel):
    issue: PulseDigestIssueDetailRead
    publication_jobs: list[DigestPublicationJobRead] = Field(default_factory=list)
