"""Schemas for group workspace and result sharing boundaries."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from research_pulse_cn.domain.enums import (
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
    GroupWorkspaceMemberRole,
    GroupWorkspaceResultCollectStatus,
    GroupWorkspaceStatus,
    PaperType,
    PulseDigestIssueStatus,
    ResultShareAliasStatus,
    ResultShareGrantStatus,
    ResultShareHandoffTargetKind,
    ResultShareKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
    ResultShareViewOutcome,
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


class GroupWorkspaceInviteGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    role_to_assign: GroupWorkspaceInviteRole
    display_label: str | None = Field(default=None, max_length=255)
    max_claims: int | None = Field(default=None, ge=1)
    expires_at: datetime | None = None


class ResultShareGrantCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    share_kind: ResultShareKind
    workspace_id: UUID | None = None
    digest_issue_id: UUID | None = None
    paper_id: UUID | None = None
    display_label: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None


class ResultShareAliasCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_share_grant_id: UUID
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


class GroupWorkspaceSafeSummaryRead(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    status: GroupWorkspaceStatus


class GroupWorkspaceMemberRead(ORMModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: GroupWorkspaceMemberRole
    joined_at: datetime
    created_at: datetime
    updated_at: datetime


class GroupWorkspaceMembershipSummaryRead(BaseModel):
    member_id: UUID
    workspace_id: UUID
    user_id: UUID
    role: GroupWorkspaceMemberRole
    joined_at: datetime
    workspace_summary: GroupWorkspaceSafeSummaryRead
    result_collect_handoff_reserve: ResultCollectHandoffReserveRead | None = None


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


class ResultShareAliasRead(ORMModel):
    id: UUID
    result_share_grant_id: UUID
    share_kind: ResultShareKind
    status: ResultShareAliasStatus
    display_label: str | None
    alias_prefix: str | None
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GroupWorkspaceInviteGrantRead(ORMModel):
    id: UUID
    workspace_id: UUID
    role_to_assign: GroupWorkspaceInviteRole
    status: GroupWorkspaceInviteGrantStatus
    display_label: str | None
    max_claims: int | None
    claim_count: int
    expires_at: datetime | None
    last_used_at: datetime | None
    issued_by_admin_id: UUID | None
    created_at: datetime
    updated_at: datetime


class GroupWorkspaceInviteGrantIssueResponse(BaseModel):
    grant: GroupWorkspaceInviteGrantRead
    plain_text_token: str
    expires_at: datetime | None


class GroupWorkspaceInviteGrantRevokeResponse(BaseModel):
    grant: GroupWorkspaceInviteGrantRead
    revoked_at: datetime


class GroupWorkspaceInviteClaimRead(ORMModel):
    id: UUID
    invite_grant_id: UUID
    workspace_id: UUID
    user_id: UUID
    membership_id: UUID | None
    role_assigned: GroupWorkspaceInviteRole
    claim_status: GroupWorkspaceInviteClaimStatus
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None


class GroupWorkspaceInvitePublicSummaryRead(BaseModel):
    id: UUID
    workspace_id: UUID
    role_to_assign: GroupWorkspaceInviteRole
    status: GroupWorkspaceInviteGrantStatus
    display_label: str | None
    max_claims: int | None
    claim_count: int
    expires_at: datetime | None
    created_at: datetime


class GroupWorkspaceInviteBootstrapRead(BaseModel):
    invite: GroupWorkspaceInvitePublicSummaryRead
    workspace: GroupWorkspaceSafeSummaryRead
    role_to_assign: GroupWorkspaceInviteRole
    remaining_claims: int | None = None
    expires_at: datetime | None
    result_collect_handoff_reserve: ResultCollectHandoffReserveRead | None = None
    notes: list[str] = Field(default_factory=list)


class GroupWorkspaceInviteClaimPreviewRead(BaseModel):
    can_claim: bool
    reason_codes: list[str] = Field(default_factory=list)
    current_membership: GroupWorkspaceMembershipSummaryRead | None = None
    invite: GroupWorkspaceInvitePublicSummaryRead | None = None
    workspace: GroupWorkspaceSafeSummaryRead | None = None
    result_collect_handoff_reserve: ResultCollectHandoffReserveRead | None = None


class GroupWorkspaceInviteClaimResponse(BaseModel):
    action: Literal["claimed", "already_member", "rejected"]
    membership: GroupWorkspaceMembershipSummaryRead | None = None
    invite_claim: GroupWorkspaceInviteClaimRead | None = None
    invite: GroupWorkspaceInvitePublicSummaryRead | None = None
    workspace: GroupWorkspaceSafeSummaryRead | None = None
    result_collect_handoff_reserve: ResultCollectHandoffReserveRead | None = None


class ResultShareGrantIssueResponse(BaseModel):
    grant: ResultShareGrantRead
    plain_text_token: str
    expires_at: datetime | None


class ResultShareAliasIssueResponse(BaseModel):
    alias: ResultShareAliasRead
    plain_text_alias: str
    expires_at: datetime | None


class ResultShareGrantRevokeResponse(BaseModel):
    grant: ResultShareGrantRead
    revoked_at: datetime


class ResultShareAliasRevokeResponse(BaseModel):
    alias: ResultShareAliasRead
    revoked_at: datetime


class ResultShareAnalyticsSummaryRead(BaseModel):
    total_events: int
    resolved_events: int
    rejected_events: int
    bootstrap_view_count: int
    content_view_count: int
    redirect_count: int
    invite_handoff_redirect_count: int
    distinct_fingerprint_count: int | None = None
    by_share_kind: dict[str, int] = Field(default_factory=dict)
    by_access_mode: dict[str, int] = Field(default_factory=dict)
    by_handoff_target: dict[str, int] = Field(default_factory=dict)
    last_event_at: datetime | None = None


class ResultShareViewEventRead(ORMModel):
    id: UUID
    result_share_grant_id: UUID | None = None
    result_share_alias_id: UUID | None = None
    share_kind: ResultShareKind
    access_mode: ResultShareViewAccessMode
    event_type: ResultShareViewEventType
    outcome: ResultShareViewOutcome
    handoff_target_kind: ResultShareHandoffTargetKind | None = None
    referrer_host: str | None = None
    user_agent_family: str | None = None
    occurred_at: datetime
    created_at: datetime


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


class ShareGrantCollectionReserveRead(BaseModel):
    supported: bool
    share_kind_collectable: bool
    collect_supported_via_self_service: bool
    source_files_included: bool
    notes: list[str] = Field(default_factory=list)


class ResultCollectHandoffReserveRead(BaseModel):
    supported: bool
    separate_result_share_token_required: bool
    result_share_bootstrap_available: bool
    collect_supported_via_self_service: bool
    direct_collect_via_invite_page: bool
    source_files_included: bool
    supported_share_kinds: list[Literal["digest_issue", "paper_snapshot"]] = Field(
        default_factory=list
    )
    result_share_shell_entry_url: str | None = None
    notes: list[str] = Field(default_factory=list)


class ShareGrantWorkspaceInviteHandoffReserveRead(BaseModel):
    supported: bool
    share_kind: Literal["workspace_board"]
    separate_invite_token_required: bool
    invite_bootstrap_available: bool
    self_service_claim_supported: bool
    direct_claim_via_share_page: bool
    handoff_redirect_supported: bool
    source_files_included: bool
    invite_shell_entry_url: str | None = None
    invite_handoff_url: str | None = None
    notes: list[str] = Field(default_factory=list)


class ShareGrantResultCollectHandoffReserveRead(BaseModel):
    supported: bool
    share_kind: Literal["workspace_board"]
    separate_result_share_token_required: bool
    result_share_bootstrap_available: bool
    collect_supported_via_self_service: bool
    direct_collect_via_current_share: bool
    source_files_included: bool
    supported_share_kinds: list[Literal["digest_issue", "paper_snapshot"]] = Field(
        default_factory=list
    )
    result_share_shell_entry_url: str | None = None
    notes: list[str] = Field(default_factory=list)


class ShareGrantBootstrapRead(BaseModel):
    grant: ShareGrantPublicSummaryRead
    target: ShareGrantTargetSummaryRead
    collection_reserve: ShareGrantCollectionReserveRead | None = None
    workspace_invite_handoff_reserve: ShareGrantWorkspaceInviteHandoffReserveRead | None = None
    result_collect_handoff_reserve: ShareGrantResultCollectHandoffReserveRead | None = None
    notes: list[str] = Field(default_factory=list)


class ResultShareCollectablePaperRead(BaseModel):
    paper_id: UUID
    title: str
    type: PaperType
    stage: str
    venue: str | None = None
    priority: int
    next_action: str | None = None
    blocker: str | None = None
    progress_percentage: int
    source_card_type: str | None = None
    source_pulse_card_id: UUID | None = None
    source_section_kind: str | None = None
    notes: list[str] | None = None


class ResultShareCollectEligibleWorkspaceRead(BaseModel):
    workspace: GroupWorkspaceSafeSummaryRead
    membership_role: GroupWorkspaceMemberRole


class ResultShareCollectShareSummaryRead(BaseModel):
    id: UUID
    share_kind: ResultShareKind
    status: ResultShareGrantStatus
    display_label: str | None = None
    expires_at: datetime | None = None
    target: ShareGrantTargetSummaryRead


class ResultShareCollectPreviewRead(BaseModel):
    share: ResultShareCollectShareSummaryRead | None = None
    collectable_items: list[ResultShareCollectablePaperRead] = Field(default_factory=list)
    eligible_workspaces: list[ResultShareCollectEligibleWorkspaceRead] = Field(default_factory=list)
    can_collect: bool
    reason_codes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ResultShareCollectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    paper_ids: list[UUID] | None = None


class ResultShareCollectedPaperSummaryRead(BaseModel):
    paper_id: UUID
    title: str
    type: PaperType
    stage: str
    venue: str | None = None
    priority: int
    next_action: str | None = None
    blocker: str | None = None
    progress_percentage: int


class GroupWorkspaceResultCollectRecordRead(ORMModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    result_share_grant_id: UUID | None = None
    share_kind: ResultShareKind
    digest_issue_id: UUID | None = None
    source_pulse_card_id: UUID | None = None
    source_paper_id: UUID | None = None
    collected_paper_id: UUID
    status: GroupWorkspaceResultCollectStatus
    reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ResultShareCollectItemResultRead(BaseModel):
    paper_id: UUID
    status: GroupWorkspaceResultCollectStatus
    reason_codes: list[str] = Field(default_factory=list)
    collect_record: GroupWorkspaceResultCollectRecordRead | None = None
    paper: ResultShareCollectedPaperSummaryRead


class ResultShareCollectResponse(BaseModel):
    action: Literal["collected", "already_present", "rejected"]
    workspace: GroupWorkspaceSafeSummaryRead | None = None
    collected_results: list[ResultShareCollectItemResultRead] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GroupWorkspaceResultCollectionRead(BaseModel):
    record: GroupWorkspaceResultCollectRecordRead
    workspace: GroupWorkspaceSafeSummaryRead
    paper: ResultShareCollectedPaperSummaryRead


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
