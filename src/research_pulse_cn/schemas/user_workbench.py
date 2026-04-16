"""Schemas for the read-only admin user workbench shell."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    GroupWorkspaceMemberRole,
    GroupWorkspaceStatus,
    PaperType,
    PulseDigestIssueStatus,
    ResearchWatchProfileSourceMode,
    SignalSource,
)


class UserWorkbenchLatestDigestIssueSummaryRead(BaseModel):
    id: UUID
    user_id: UUID
    issue_date: date
    status: PulseDigestIssueStatus
    title: str
    summary: str
    selected_card_count: int
    published_at: datetime | None = None
    deep_link_path: str | None = None


class UserWorkbenchPaperSignalSummaryRead(BaseModel):
    source: SignalSource
    citation_count: int | None = None
    download_count: int | None = None
    read_count: int | None = None
    inclusion_status: str | None = None
    fetched_at: datetime


class UserWorkbenchLinkedWatchProfileSummaryRead(BaseModel):
    id: UUID
    label: str
    enabled: bool
    source_mode: ResearchWatchProfileSourceMode


class UserWorkbenchWatchProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    paper_id: UUID | None = None
    label: str
    enabled: bool
    source_mode: ResearchWatchProfileSourceMode
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    authors_of_interest: list[str] | None = None
    user_name: str | None = None
    user_email: str | None = None
    paper_title: str | None = None
    created_at: datetime
    updated_at: datetime


class UserWorkbenchPaperSummaryRead(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str | None = None
    user_email: str | None = None
    title: str
    type: PaperType
    stage: str
    venue: str | None = None
    priority: int
    next_action: str | None = None
    blocker: str | None = None
    last_touch_at: datetime | None = None
    progress_percentage: int
    latest_signal_summary: UserWorkbenchPaperSignalSummaryRead | None = None
    linked_watch_profiles: list[UserWorkbenchLinkedWatchProfileSummaryRead] = Field(
        default_factory=list
    )


class UserWorkbenchWorkspaceMembershipRead(BaseModel):
    workspace_id: UUID
    slug: str
    name: str
    status: GroupWorkspaceStatus
    role: GroupWorkspaceMemberRole
    joined_at: datetime


class UserWorkbenchUserSummaryRead(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    field: str | None = None
    paper_count: int
    watch_profile_count: int
    workspace_count: int
    latest_digest_issue_summary: UserWorkbenchLatestDigestIssueSummaryRead | None = None


class UserWorkbenchUserDetailRead(BaseModel):
    user: UserWorkbenchUserSummaryRead
    papers: list[UserWorkbenchPaperSummaryRead] = Field(default_factory=list)
    watch_profiles: list[UserWorkbenchWatchProfileRead] = Field(default_factory=list)
    workspace_memberships: list[UserWorkbenchWorkspaceMembershipRead] = Field(default_factory=list)


class UserWorkbenchPaperOwnerRead(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    field: str | None = None


class UserWorkbenchPaperDetailRead(BaseModel):
    paper: UserWorkbenchPaperSummaryRead
    owner: UserWorkbenchPaperOwnerRead
    linked_watch_profiles: list[UserWorkbenchWatchProfileRead] = Field(default_factory=list)
