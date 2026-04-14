"""Schemas for WeChat bindings, digest issues, and publication reserve jobs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    DigestPublicationAttemptStatus,
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    OfficialAccountCallbackPayloadFormat,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
    OfficialAccountTransportKind,
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


class DigestPublicationAttemptRead(BaseModel):
    id: UUID
    digest_publication_job_id: UUID
    digest_issue_id: UUID
    user_id: UUID
    binding_id: UUID | None
    attempt_number: int
    provider_name: str
    provider_mode: OfficialAccountProviderMode
    status: DigestPublicationAttemptStatus
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    error_summary: str | None
    external_message_id: str | None
    provider_response_code: str | None
    provider_response_message: str | None
    started_at: datetime
    finished_at: datetime | None


class OfficialAccountProviderStatusRead(BaseModel):
    mode: OfficialAccountProviderMode
    transport_kind: OfficialAccountTransportKind
    readiness: bool
    readiness_checks: dict[str, bool]
    readiness_failures: list[str]
    callback_enabled: bool
    real_send_enabled: bool
    dispatch_timeout_seconds: int
    http_connect_timeout_seconds: int
    http_read_timeout_seconds: int
    max_retries: int
    outbound_send_enabled: bool
    token_cached: bool
    token_expires_at: datetime | None
    last_refresh_at: datetime | None
    cache_backend: str
    has_app_id: bool
    has_app_secret: bool
    has_digest_template_id: bool
    has_callback_token: bool
    has_callback_aes_key: bool
    has_template_field_mapping: bool
    default_mini_program_app_id: str | None
    default_article_base_url: str | None
    callback_path: str


class OfficialAccountProviderTokenRefreshResponse(BaseModel):
    action: str
    mode: OfficialAccountProviderMode
    transport_kind: OfficialAccountTransportKind
    token_cached: bool
    token_expires_at: datetime | None
    last_refresh_at: datetime | None
    cache_backend: str


class OfficialAccountCallbackEventRead(ORMModel):
    id: UUID
    app_id: str | None
    to_user_name: str | None
    from_openid: str | None
    msg_type: str | None
    event_type: str | None
    event_key: str | None
    event_time: datetime | None
    dedupe_key: str
    signature_valid: bool
    payload_format: OfficialAccountCallbackPayloadFormat
    raw_payload: str
    parsed_payload: dict[str, Any] | None = Field(
        default=None,
        validation_alias="parsed_payload_json",
        serialization_alias="parsed_payload",
    )
    processing_status: OfficialAccountCallbackProcessingStatus
    processing_note: str | None
    linked_binding_id: UUID | None
    created_at: datetime
    processed_at: datetime | None


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


class DigestPublicationDispatchResponse(BaseModel):
    action: str
    publication_job: DigestPublicationJobRead
    attempt: DigestPublicationAttemptRead | None = None
