"""Schemas for subscription self-service reserve APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_pulse_cn.domain.enums import (
    ChannelType,
    DigestDeliveryDecisionStatus,
    OfficialAccountBindingHandshakeSessionStatus,
    OfficialAccountOAuthScope,
    PulseDigestIssueStatus,
    SubscriptionEditorHandoffGrantStatus,
    SubscriptionEditorHandoffIssuedBy,
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

    enabled: Any | None = None
    quiet_hours: Any | None = None
    timezone: Any | None = None
    allowed_weekdays: Any | None = None
    muted_until: Any | None = None
    minimum_selected_cards: Any | None = None
    skip_if_no_today_focus: Any | None = None


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
    requested_scope: OfficialAccountOAuthScope
    authorized_scope: OfficialAccountOAuthScope | None
    status: OfficialAccountBindingHandshakeSessionStatus
    oauth_openid_hash: str | None
    matched_callback_event_id: UUID | None
    claimed_binding_id: UUID | None
    expires_at: datetime | None
    last_viewed_at: datetime | None
    authorization_started_at: datetime | None
    matched_at: datetime | None
    claimed_at: datetime | None
    oauth_completed_at: datetime | None
    userinfo_fetched: bool
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class SubscriptionSelfServiceHandshakeBootstrapResponse(BaseModel):
    user: SubscriptionSelfServiceUserSummaryRead
    binding: SubscriptionSelfServiceBindingSummaryRead | None = None
    active_session: SubscriptionSelfServiceHandshakeSessionRead | None = None
    candidate_count_hint: int | None = None
    oauth_start_supported: bool
    oauth_enabled: bool
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


class SubscriptionSelfServiceOAuthStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_id: str | None = Field(default=None, min_length=1, max_length=255)
    display_label: str | None = Field(default=None, max_length=255)
    requested_scope: OfficialAccountOAuthScope | None = None


class SubscriptionSelfServiceOAuthStartResponse(BaseModel):
    session: SubscriptionSelfServiceHandshakeSessionRead
    authorize_url: str
    requested_scope: OfficialAccountOAuthScope
    expires_at: datetime | None
    notes: list[str] = Field(default_factory=list)


class SubscriptionSelfServiceOAuthStatusResponse(BaseModel):
    oauth_start_supported: bool
    oauth_enabled: bool
    session: SubscriptionSelfServiceHandshakeSessionRead | None = None
    claimed_binding: SubscriptionSelfServiceBindingSummaryRead | None = None
    notes: list[str] = Field(default_factory=list)


class SubscriptionSelfServiceDeliveryControlPreviewRead(BaseModel):
    decision: DigestDeliveryDecisionStatus
    reason_codes: list[str] = Field(default_factory=list)
    normalized_control_policy: dict[str, Any]
    current_local_time: datetime
    local_weekday: int
    next_allowed_at: datetime | None = None
    latest_digest_issue: SubscriptionSelfServiceDigestIssueSummaryRead | None = None


class SubscriptionSelfServiceEditorEntryRead(BaseModel):
    supported: bool
    oauth_enabled: bool
    editor_contract_available: bool
    editor_preview_available: bool
    supported_editable_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SubscriptionSettingsDraftRead(SubscriptionSelfServiceSettingsRead):
    self_service_grant_status: SubscriptionSelfServiceGrantStatus


class SubscriptionEditorFieldRead(BaseModel):
    field_id: str
    label: str
    value_type: str
    editable: bool
    required: bool
    nullable: bool
    description: str | None = None
    validation_hints: dict[str, Any] = Field(default_factory=dict)


class SubscriptionEditorSectionRead(BaseModel):
    section_id: str
    title: str
    description: str | None = None
    editable: bool
    field_ids: list[str] = Field(default_factory=list)


class SubscriptionSelfServiceEditorContractRead(BaseModel):
    contract_version: str
    channel: ChannelType
    editable_section_ids: list[str] = Field(default_factory=list)
    weekday_numbering_note: str
    sections: list[SubscriptionEditorSectionRead] = Field(default_factory=list)
    fields: list[SubscriptionEditorFieldRead] = Field(default_factory=list)


class SubscriptionSettingsValidationIssueRead(BaseModel):
    field_id: str
    code: str
    message: str


class SubscriptionSettingsAuthoritativePreviewRead(BaseModel):
    state: Literal["ready", "no_digest_context", "invalid_input"] | str
    decision: DigestDeliveryDecisionStatus | None = None
    reason_codes: list[str] = Field(default_factory=list)
    normalized_control_policy: dict[str, Any] | None = None
    current_local_time: datetime | None = None
    local_weekday: int | None = None
    next_allowed_at: datetime | None = None
    latest_digest_issue: SubscriptionSelfServiceDigestIssueSummaryRead | None = None


class SubscriptionSettingsPreviewRead(BaseModel):
    contract_version: str
    normalized_draft: SubscriptionSettingsDraftRead
    changed_fields: list[str] = Field(default_factory=list)
    validation_errors: list[SubscriptionSettingsValidationIssueRead] = Field(default_factory=list)
    validation_warnings: list[SubscriptionSettingsValidationIssueRead] = Field(default_factory=list)
    authoritative_preview: SubscriptionSettingsAuthoritativePreviewRead


class SubscriptionSettingsSaveResultRead(BaseModel):
    contract_version: str
    saved_settings: SubscriptionSelfServiceSettingsRead
    changed_fields: list[str] = Field(default_factory=list)
    authoritative_preview: SubscriptionSettingsAuthoritativePreviewRead | None = None


class SubscriptionSelfServiceEditorBootstrapRead(BaseModel):
    contract_version: str
    grant: SubscriptionSelfServiceGrantSummaryRead
    user: SubscriptionSelfServiceUserSummaryRead
    official_account_binding_summary: SubscriptionSelfServiceBindingSummaryRead | None = None
    current_settings_draft: SubscriptionSettingsDraftRead
    latest_digest_summary: SubscriptionSelfServiceDigestIssueSummaryRead | None = None
    authoritative_preview_supported: bool
    self_service_entry: SubscriptionSelfServiceEditorEntryRead


class SubscriptionEditorHandoffGrantRead(BaseModel):
    id: UUID
    user_id: UUID
    channel: ChannelType
    binding_id: UUID | None
    mini_grant_id: UUID | None
    self_service_grant_id: UUID
    status: SubscriptionEditorHandoffGrantStatus
    display_label: str | None
    issued_by: SubscriptionEditorHandoffIssuedBy
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SubscriptionEditorLinkedSelfServiceGrantRead(BaseModel):
    id: UUID
    channel: ChannelType
    binding_id: UUID | None
    status: SubscriptionSelfServiceGrantStatus
    display_label: str | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime


class SubscriptionEditorBootstrapRead(BaseModel):
    contract_version: str
    handoff_grant: SubscriptionEditorHandoffGrantRead
    linked_self_service_grant: SubscriptionEditorLinkedSelfServiceGrantRead | None = None
    user: SubscriptionSelfServiceUserSummaryRead
    official_account_binding_summary: SubscriptionSelfServiceBindingSummaryRead | None = None
    current_settings_draft: SubscriptionSettingsDraftRead
    latest_digest_summary: SubscriptionSelfServiceDigestIssueSummaryRead | None = None
    authoritative_preview_supported: bool
    supported_editor_endpoints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SubscriptionEditorHandoffIssueResponse(BaseModel):
    handoff_grant: SubscriptionEditorHandoffGrantRead
    plain_text_token: str
    expires_at: datetime | None
    supported_editor_endpoints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SubscriptionEditorHandoffStatusResponse(BaseModel):
    handoff_grant: SubscriptionEditorHandoffGrantRead | None = None
    linked_self_service_grant: SubscriptionEditorLinkedSelfServiceGrantRead | None = None
    linked_binding: SubscriptionSelfServiceBindingSummaryRead | None = None
    supported_editor_endpoints: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class SubscriptionEditorHandoffGrantRevokeResponse(BaseModel):
    grant: SubscriptionEditorHandoffGrantRead
    revoked_at: datetime
