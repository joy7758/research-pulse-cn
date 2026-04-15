"""Schemas for subscription self-service reserve APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_pulse_cn.domain.enums import (
    ChannelType,
    DigestDeliveryDecisionStatus,
    OfficialAccountBindingHandshakeSessionStatus,
    PulseDigestIssueStatus,
    SubscriptionSelfServiceGrantStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.schemas.common import ORMModel


class SubscriptionSelfServiceGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    binding_id: UUID | None = None
    channel: ChannelType = ChannelType.OFFICIAL_ACCOUNT
    grant_scope: dict[str, Any] | None = None
    display_label: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None


class SubscriptionSelfServiceGrantRead(ORMModel):
    id: UUID
    user_id: UUID
    binding_id: UUID | None
    channel: ChannelType
    grant_scope: dict[str, Any] | None = Field(
        default=None,
        validation_alias="grant_scope_json",
        serialization_alias="grant_scope",
    )
    status: SubscriptionSelfServiceGrantStatus
    display_label: str | None
    issued_by_admin_id: UUID | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SubscriptionSelfServiceGrantIssueResponse(BaseModel):
    grant: SubscriptionSelfServiceGrantRead
    plain_text_token: str
    expires_at: datetime | None


class SubscriptionSelfServiceGrantRevokeResponse(BaseModel):
    grant: SubscriptionSelfServiceGrantRead
    revoked_at: datetime


class SubscriptionSelfServiceGrantSummaryRead(BaseModel):
    id: UUID
    channel: ChannelType
    binding_id: UUID | None
    grant_scope: dict[str, Any] = Field(default_factory=dict)
    status: SubscriptionSelfServiceGrantStatus
    display_label: str | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class SubscriptionSelfServiceUserSummaryRead(BaseModel):
    id: UUID
    name: str
    email: str | None
    field: str | None


class SubscriptionSelfServiceBindingSummaryRead(BaseModel):
    id: UUID
    channel_type: WeChatBindingChannelType
    app_id: str
    display_label: str | None
    bind_state: WeChatBindingState
    subscribed: bool
    digest_enabled: bool
    subscribed_at: datetime | None
    unsubscribed_at: datetime | None
    last_seen_at: datetime | None


class SubscriptionSelfServiceDigestIssueSummaryRead(BaseModel):
    id: UUID
    issue_date: date
    status: PulseDigestIssueStatus
    title: str
    summary: str
    selected_card_count: int
    deep_link_path: str | None


class SubscriptionSelfServiceSettingsRead(BaseModel):
    subscription_policy_id: UUID | None
    user_id: UUID | None
    channel: ChannelType
    enabled: bool
    quiet_hours: dict[str, Any] | None
    timezone: str
    allowed_weekdays: list[int] = Field(default_factory=list)
    muted_until: datetime | None
    minimum_selected_cards: int | None
    skip_if_no_today_focus: bool
    updated_at: datetime | None


class SubscriptionSelfServiceSettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    quiet_hours: dict[str, Any] | None = None
    timezone: str | None = None
    allowed_weekdays: list[int] | None = None
    muted_until: datetime | None = None
    minimum_selected_cards: int | None = Field(default=None, ge=0)
    skip_if_no_today_focus: bool | None = None


class SubscriptionSelfServiceBootstrapResponse(BaseModel):
    grant: SubscriptionSelfServiceGrantSummaryRead
    user: SubscriptionSelfServiceUserSummaryRead
    binding: SubscriptionSelfServiceBindingSummaryRead | None = None
    subscription_settings: SubscriptionSelfServiceSettingsRead
    latest_digest_issue: SubscriptionSelfServiceDigestIssueSummaryRead | None = None


class SubscriptionSelfServiceHandshakeSessionRead(BaseModel):
    id: UUID
    user_id: UUID
    channel: ChannelType
    app_id: str
    display_label: str | None
    self_service_grant_id: UUID | None
    status: OfficialAccountBindingHandshakeSessionStatus
    matched_callback_event_id: UUID | None
    claimed_binding_id: UUID | None
    expires_at: datetime | None
    last_viewed_at: datetime | None
    matched_at: datetime | None
    claimed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SubscriptionSelfServiceHandshakeBootstrapResponse(BaseModel):
    user: SubscriptionSelfServiceUserSummaryRead
    binding: SubscriptionSelfServiceBindingSummaryRead | None = None
    active_session: SubscriptionSelfServiceHandshakeSessionRead | None = None
    candidate_count_hint: int | None = None
    notes: list[str] = Field(default_factory=list)


class SubscriptionSelfServiceHandshakeSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str | None = Field(default=None, min_length=1, max_length=255)
    display_label: str | None = Field(default=None, max_length=255)


class SubscriptionSelfServiceHandshakeSessionIssueResponse(BaseModel):
    session: SubscriptionSelfServiceHandshakeSessionRead
    plain_text_state_token: str
    expires_at: datetime | None


class SubscriptionSelfServiceHandshakeSessionResponse(BaseModel):
    session: SubscriptionSelfServiceHandshakeSessionRead | None = None


class SubscriptionSelfServiceDeliveryControlPreviewRead(BaseModel):
    decision: DigestDeliveryDecisionStatus
    reason_codes: list[str] = Field(default_factory=list)
    normalized_control_policy: dict[str, Any]
    current_local_time: datetime
    local_weekday: int
    next_allowed_at: datetime | None = None
    latest_digest_issue: SubscriptionSelfServiceDigestIssueSummaryRead | None = None
