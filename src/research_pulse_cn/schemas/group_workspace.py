"""Schemas for group workspace and result sharing boundaries."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_pulse_cn.domain.enums import (
    GroupWorkspaceMemberRole,
    GroupWorkspaceStatus,
    PaperType,
    PulseDigestIssueStatus,
    ResultShareGrantStatus,
    ResultShareKind,
    SignalSource,
)
from research_pulse_cn.schemas.common import ORMModel


class GroupWorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class GroupWorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str | None = Field(default=None, min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: GroupWorkspaceStatus | None = None


class GroupWorkspaceMemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role: GroupWorkspaceMemberRole


class GroupWorkspacePaperCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: UUID


class ResultShareGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    share_kind: ResultShareKind
    workspace_id: UUID | None = None
    digest_issue_id: UUID | None = None
    paper_id: UUID | None = None
    display_label: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None


class GroupWorkspaceRead(ORMModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    status: GroupWorkspaceStatus
    created_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class GroupWorkspaceMemberRead(ORMModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: GroupWorkspaceMemberRole
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


class GroupWorkspacePaperRead(ORMModel):
    id: UUID
    workspace_id: UUID
    paper_id: UUID
    added_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class GroupWorkspaceMemberSummaryRead(BaseModel):
    member_id: UUID
    user_id: UUID
    role: GroupWorkspaceMemberRole
    name: str
    email: str | None = None
    joined_at: datetime


class WorkspacePaperSignalSummaryRead(BaseModel):
    source: SignalSource
    citation_count: int | None = None
    download_count: int | None = None
    read_count: int | None = None
    inclusion_status: str | None = None
    fetched_at: datetime


class WorkspacePaperSnapshotRead(BaseModel):
    paper_id: UUID
    user_id: UUID
    owner_name: str | None = None
    owner_email: str | None = None
    title: str
    type: PaperType
    stage: str
    venue: str | None = None
    priority: int
    next_action: str | None = None
    blocker: str | None = None
    last_touch_at: datetime | None = None
    progress_percentage: int
    latest_signal_summary: WorkspacePaperSignalSummaryRead | None = None


class GroupWorkspaceBoardQuickStatsRead(BaseModel):
    member_count: int
    paper_count: int
    blocked_paper_count: int
    papers_with_signals_count: int


class GroupWorkspaceBoardRead(BaseModel):
    workspace: GroupWorkspaceRead
    member_count: int
    paper_count: int
    members: list[GroupWorkspaceMemberSummaryRead] = Field(default_factory=list)
    papers: list[WorkspacePaperSnapshotRead] = Field(default_factory=list)
    quick_stats: GroupWorkspaceBoardQuickStatsRead


class ResultShareGrantRead(ORMModel):
    id: UUID
    share_kind: ResultShareKind
    workspace_id: UUID | None
    digest_issue_id: UUID | None
    paper_id: UUID | None
    status: ResultShareGrantStatus
    display_label: str | None
    issued_by_admin_id: UUID | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResultShareGrantIssueResponse(BaseModel):
    grant: ResultShareGrantRead
    plain_text_token: str
    expires_at: datetime | None


class ResultShareGrantRevokeResponse(BaseModel):
    grant: ResultShareGrantRead
    revoked_at: datetime


class ShareGrantPublicSummaryRead(BaseModel):
    id: UUID
    share_kind: ResultShareKind
    display_label: str | None
    status: ResultShareGrantStatus
    expires_at: datetime | None
    created_at: datetime


class ShareGrantTargetSummaryRead(BaseModel):
    workspace_id: UUID | None = None
    digest_issue_id: UUID | None = None
    paper_id: UUID | None = None
    title: str | None = None


class ShareGrantBootstrapRead(BaseModel):
    grant: ShareGrantPublicSummaryRead
    target: ShareGrantTargetSummaryRead
    notes: list[str] = Field(default_factory=list)


class SharedDigestItemRead(BaseModel):
    sort_order: int
    pulse_card_id: UUID
    card_type: str
    source_paper_id: UUID | None
    title: str
    summary: str
    why_now: str | None = None
    action_text: str | None = None
    deep_link: str | None = None
    paper: WorkspacePaperSnapshotRead | None = None


SharedTodaySectionKindRead = (
    Literal[
        "today_focus",
        "yesterday_recap",
        "signal_updates",
        "related_papers",
        "other_updates",
    ]
    | str
)


class SharedTodaySectionRead(BaseModel):
    kind: SharedTodaySectionKindRead
    title: str
    item_count: int
    items: list[SharedDigestItemRead] = Field(default_factory=list)


class SharedTodayQuickStatsRead(BaseModel):
    selected_card_count: int
    related_paper_count: int
    signal_update_count: int
    touched_paper_count: int


class SharedTodayPublicationPreviewRead(BaseModel):
    digest_title: str | None = None
    digest_subtitle: str | None = None
    digest_highlights: list[SharedDigestItemRead] = Field(default_factory=list)
    primary_cta_text: str | None = None
    primary_cta_path: str | None = None
    mini_program_path: str | None = None
    article_url: str | None = None


class SharedDigestIssueRead(BaseModel):
    share_kind: Literal["digest_issue"] = "digest_issue"
    id: UUID
    issue_date: date
    status: PulseDigestIssueStatus
    title: str
    summary: str
    highlight_count: int
    selected_card_count: int
    deep_link_path: str | None = None
    highlights: list[SharedDigestItemRead] = Field(default_factory=list)
    is_structured: bool = False
    fallback_mode: Literal["structured", "highlights_only", "empty"] | str = "empty"
    section_order: list[SharedTodaySectionKindRead] = Field(default_factory=list)
    sections: list[SharedTodaySectionRead] = Field(default_factory=list)
    quick_stats: SharedTodayQuickStatsRead | None = None
    focus_card: SharedDigestItemRead | None = None
    publication_preview: SharedTodayPublicationPreviewRead | None = None
    items: list[SharedDigestItemRead] = Field(default_factory=list)


class SharedPaperSnapshotRead(WorkspacePaperSnapshotRead):
    share_kind: Literal["paper_snapshot"] = "paper_snapshot"


class SharedWorkspaceBoardRead(BaseModel):
    share_kind: Literal["workspace_board"] = "workspace_board"
    workspace: GroupWorkspaceRead
    member_count: int
    paper_count: int
    members: list[GroupWorkspaceMemberSummaryRead] = Field(default_factory=list)
    papers: list[WorkspacePaperSnapshotRead] = Field(default_factory=list)
    quick_stats: GroupWorkspaceBoardQuickStatsRead


SharedResultContentRead = Annotated[
    SharedDigestIssueRead | SharedPaperSnapshotRead | SharedWorkspaceBoardRead,
    Field(discriminator="share_kind"),
]
