"""Schemas for mini-program read-only reserve APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    ChannelType,
    DigestDeliveryDecisionStatus,
    MiniReadGrantStatus,
    MiniReadGrantType,
    PaperType,
    SignalSource,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.schemas.common import ORMModel


class MiniReadGrantCreateRequest(BaseModel):
    user_id: UUID
    binding_id: UUID | None = None
    digest_issue_id: UUID | None = None
    grant_type: MiniReadGrantType
    scope: dict[str, Any] | None = None
    expires_at: datetime | None = None


class MiniReadGrantRead(ORMModel):
    id: UUID
    user_id: UUID
    binding_id: UUID | None
    digest_issue_id: UUID | None
    grant_type: MiniReadGrantType
    status: MiniReadGrantStatus
    scope: dict[str, Any] | None = Field(
        default=None,
        validation_alias="scope_json",
        serialization_alias="scope",
    )
    expires_at: datetime | None
    last_used_at: datetime | None
    created_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime
    preview_landing_path: str


class MiniReadGrantIssueResponse(BaseModel):
    grant: MiniReadGrantRead
    plain_text_token: str
    preview_landing_path: str
    expires_at: datetime | None


class MiniReadGrantRevokeResponse(BaseModel):
    grant: MiniReadGrantRead
    revoked_at: datetime


class MiniUserSummaryRead(BaseModel):
    id: UUID
    name: str
    email: str | None
    field: str | None


class MiniBindingSummaryRead(BaseModel):
    id: UUID
    channel_type: WeChatBindingChannelType
    app_id: str
    display_label: str | None
    bind_state: WeChatBindingState
    subscribed: bool
    digest_enabled: bool
    subscribed_at: datetime | None = None
    unsubscribed_at: datetime | None = None
    last_seen_at: datetime | None = None


class MiniGrantContextRead(BaseModel):
    id: UUID
    user_id: UUID
    binding_id: UUID | None
    digest_issue_id: UUID | None
    grant_type: MiniReadGrantType
    status: MiniReadGrantStatus
    scope: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None
    last_used_at: datetime | None
    preview_landing_path: str
    binding: MiniBindingSummaryRead | None = None


class MiniPaperSummaryRead(BaseModel):
    id: UUID
    title: str
    type: PaperType
    stage: str
    venue: str | None
    priority: int
    next_action: str | None
    blocker: str | None
    last_touch_at: datetime | None
    progress_percentage: int


class MiniProgressEventRead(BaseModel):
    id: UUID
    stage: str
    happened_at: datetime
    summary: str
    owner: str | None


class MiniSignalSnapshotRead(BaseModel):
    id: UUID
    source: SignalSource
    citation_count: int | None
    download_count: int | None
    read_count: int | None
    inclusion_status: str | None
    fetched_at: datetime


class MiniPaperDetailRead(MiniPaperSummaryRead):
    user_id: UUID
    identifiers: dict[str, Any]
    source_links: list[str]
    progress_events: list[MiniProgressEventRead] = Field(default_factory=list)
    signal_snapshots: list[MiniSignalSnapshotRead] = Field(default_factory=list)


class MiniDigestItemRead(BaseModel):
    sort_order: int
    pulse_card_id: UUID
    card_type: str
    source_paper_id: UUID | None
    title: str
    summary: str
    why_now: str | None
    action_text: str | None = None
    deep_link: str | None = None
    paper: MiniPaperSummaryRead | None = None


MiniTodaySectionKindRead = (
    Literal[
        "today_focus",
        "yesterday_recap",
        "signal_updates",
        "related_papers",
        "other_updates",
    ]
    | str
)


class MiniTodaySectionItemRead(MiniDigestItemRead):
    pass


class MiniTodaySectionRead(BaseModel):
    kind: MiniTodaySectionKindRead
    title: str
    item_count: int
    items: list[MiniTodaySectionItemRead] = Field(default_factory=list)


class MiniTodayQuickStatsRead(BaseModel):
    selected_card_count: int
    related_paper_count: int
    signal_update_count: int
    touched_paper_count: int


MiniTodayFocusCardRead = MiniTodaySectionItemRead


class MiniTodayPublicationPreviewRead(BaseModel):
    digest_title: str | None = None
    digest_subtitle: str | None = None
    digest_highlights: list[MiniDigestItemRead] = Field(default_factory=list)
    primary_cta_text: str | None = None
    primary_cta_path: str | None = None
    mini_program_path: str | None = None
    article_url: str | None = None


class MiniDigestIssueSummaryRead(BaseModel):
    id: UUID
    issue_date: str
    status: str
    title: str
    summary: str
    highlight_count: int
    selected_card_count: int
    deep_link_path: str | None
    highlights: list[MiniDigestItemRead] = Field(default_factory=list)
    is_structured: bool = False
    fallback_mode: Literal["structured", "highlights_only", "empty"] | str = "empty"
    section_order: list[MiniTodaySectionKindRead] = Field(default_factory=list)
    sections: list[MiniTodaySectionRead] = Field(default_factory=list)
    quick_stats: MiniTodayQuickStatsRead | None = None
    focus_card: MiniTodayFocusCardRead | None = None
    publication_preview: MiniTodayPublicationPreviewRead | None = None


class MiniDigestIssueDetailRead(MiniDigestIssueSummaryRead):
    items: list[MiniDigestItemRead] = Field(default_factory=list)


class MiniSubscriptionSettingsSummaryRead(BaseModel):
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


class MiniDeliveryControlPreviewRead(BaseModel):
    state: Literal["ready", "empty"] | str
    decision: DigestDeliveryDecisionStatus | None = None
    reason_codes: list[str] = Field(default_factory=list)
    normalized_control_policy: dict[str, Any]
    current_local_time: datetime | None
    local_weekday: int | None
    next_allowed_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)


class MiniSelfServiceReserveRead(BaseModel):
    supported: bool
    oauth_enabled: bool
    editable_via_current_mini_grant: bool
    separate_self_service_grant_required: bool
    editor_contract_available: bool = False
    editor_preview_available: bool = False
    supported_editable_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MiniBindingHandoffReserveRead(BaseModel):
    supported: bool
    oauth_enabled: bool
    active_session_status: str | None = None
    separate_self_service_grant_required: bool
    notes: list[str] = Field(default_factory=list)


class MiniEditorHandoffReserveRead(BaseModel):
    supported: bool
    enabled: bool
    editable_via_current_mini_grant: bool
    handoff_grant_required: bool
    active_handoff_status: str | None = None
    supported_editor_endpoints: list[str] = Field(default_factory=list)
    supported_editable_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class MiniSubscriptionReserveSummaryRead(BaseModel):
    has_official_account_binding: bool
    has_official_account_subscription_settings: bool
    delivery_preview_state: Literal["ready", "empty"] | str
    latest_digest_issue_id: UUID | None = None
    self_service_reserve: MiniSelfServiceReserveRead
    self_service_entry: MiniSelfServiceReserveRead | None = None


class MiniSubscriptionReserveRead(BaseModel):
    grant: MiniGrantContextRead
    user: MiniUserSummaryRead
    official_account_binding: MiniBindingSummaryRead | None = None
    subscription_settings: MiniSubscriptionSettingsSummaryRead
    delivery_control_preview: MiniDeliveryControlPreviewRead
    latest_digest_issue: MiniDigestIssueSummaryRead | None = None
    self_service_reserve: MiniSelfServiceReserveRead
    self_service_entry: MiniSelfServiceReserveRead | None = None
    binding_handoff_reserve: MiniBindingHandoffReserveRead
    editor_handoff_reserve: MiniEditorHandoffReserveRead


class MiniBootstrapResponse(BaseModel):
    grant: MiniGrantContextRead
    user: MiniUserSummaryRead
    available_routes: list[str] = Field(default_factory=list)
    available_resources: dict[str, Any] = Field(default_factory=dict)
    default_landing_path: str
    subscription_reserve_summary: MiniSubscriptionReserveSummaryRead | None = None


class MiniTodayResponse(BaseModel):
    state: str
    default_landing_path: str
    digest_issue: MiniDigestIssueSummaryRead | None = None
    papers: list[MiniPaperSummaryRead] = Field(default_factory=list)
    message: str | None = None
