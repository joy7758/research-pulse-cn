"""Schemas for mini-program read-only reserve APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
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
    paper: MiniPaperSummaryRead | None = None


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
    section_order: list[str] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    quick_stats: dict[str, Any] = Field(default_factory=dict)
    focus_card: dict[str, Any] | None = None
    publication_preview: dict[str, Any] | None = None


class MiniDigestIssueDetailRead(MiniDigestIssueSummaryRead):
    items: list[MiniDigestItemRead] = Field(default_factory=list)


class MiniBootstrapResponse(BaseModel):
    grant: MiniGrantContextRead
    user: MiniUserSummaryRead
    available_routes: list[str] = Field(default_factory=list)
    available_resources: dict[str, Any] = Field(default_factory=dict)
    default_landing_path: str


class MiniTodayResponse(BaseModel):
    state: str
    default_landing_path: str
    digest_issue: MiniDigestIssueSummaryRead | None = None
    papers: list[MiniPaperSummaryRead] = Field(default_factory=list)
    message: str | None = None
