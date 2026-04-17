export type AdminTokenSource = "query" | "fragment" | "manual" | "none";

export type AdminApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "network_error"
  | "request_failed";

export type GroupWorkspaceStatus = "active" | "archived";
export type GroupWorkspaceMemberRole = "owner" | "editor" | "viewer";
export type ResultShareGrantStatus = "active" | "revoked" | "expired";
export type ResultShareKind = "digest_issue" | "paper_snapshot" | "workspace_board";

export type GroupWorkspaceRead = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: GroupWorkspaceStatus;
  created_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
};

export type GroupWorkspaceMemberRead = {
  id: string;
  workspace_id: string;
  user_id: string;
  role: GroupWorkspaceMemberRole;
  joined_at: string;
  created_at: string;
  updated_at: string;
};

export type GroupWorkspacePaperRead = {
  id: string;
  workspace_id: string;
  paper_id: string;
  added_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
};

export type GroupWorkspaceMemberSummaryRead = {
  member_id: string;
  user_id: string;
  role: GroupWorkspaceMemberRole;
  name: string;
  email: string | null;
  joined_at: string;
};

export type WorkspacePaperSignalSummaryRead = {
  source: string;
  citation_count: number | null;
  download_count: number | null;
  read_count: number | null;
  inclusion_status: string | null;
  fetched_at: string;
};

export type WorkspacePaperSnapshotRead = {
  paper_id: string;
  user_id: string;
  owner_name: string | null;
  owner_email: string | null;
  title: string;
  type: string;
  stage: string;
  venue: string | null;
  priority: number;
  next_action: string | null;
  blocker: string | null;
  last_touch_at: string | null;
  progress_percentage: number;
  latest_signal_summary: WorkspacePaperSignalSummaryRead | null;
};

export type GroupWorkspaceBoardQuickStatsRead = {
  member_count: number;
  paper_count: number;
  blocked_paper_count: number;
  papers_with_signals_count: number;
};

export type GroupWorkspaceBoardRead = {
  workspace: GroupWorkspaceRead;
  member_count: number;
  paper_count: number;
  members: GroupWorkspaceMemberSummaryRead[];
  papers: WorkspacePaperSnapshotRead[];
  quick_stats: GroupWorkspaceBoardQuickStatsRead;
};

export type ResultShareGrantRead = {
  id: string;
  share_kind: ResultShareKind;
  workspace_id: string | null;
  digest_issue_id: string | null;
  paper_id: string | null;
  status: ResultShareGrantStatus;
  display_label: string | null;
  issued_by_admin_id: string | null;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ResultShareGrantIssueResponse = {
  grant: ResultShareGrantRead;
  plain_text_token: string;
  expires_at: string | null;
};

export type ResultShareGrantRevokeResponse = {
  grant: ResultShareGrantRead;
  revoked_at: string;
};

export type UserProfileRead = {
  id: string;
  name: string;
  email: string | null;
  field: string | null;
  interests: string[];
  watched_topics: string[];
  watched_venues: string[];
  reminder_preferences: Record<string, unknown>;
  risk_thresholds: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SignalSnapshotRead = {
  id: string;
  paper_id: string;
  source: string;
  citation_count: number | null;
  download_count: number | null;
  read_count: number | null;
  inclusion_status: string | null;
  fetched_at: string;
};

export type PaperProfileRead = {
  id: string;
  user_id: string;
  title: string;
  title_zh: string | null;
  title_en: string | null;
  type: string;
  stage: string;
  venue: string | null;
  identifiers: Record<string, unknown>;
  source_links: string[];
  last_touch_at: string | null;
  next_action: string | null;
  blocker: string | null;
  priority: number;
  created_at: string;
  updated_at: string;
  progress_events: unknown[];
  signal_snapshots: SignalSnapshotRead[];
};

export type WorkspaceCreateInput = {
  slug: string;
  name: string;
  description: string;
};

export type WorkspaceUpdateInput = {
  name: string;
  description: string;
  status: GroupWorkspaceStatus;
};

export type WorkspaceMemberAddInput = {
  user_id: string;
  role: GroupWorkspaceMemberRole;
};

export type WorkspacePaperAddInput = {
  paper_id: string;
};

export type WorkspaceBoardShareCreateInput = {
  display_label: string;
  expires_at: string | null;
};

export type GroupWorkspaceAdminApiErrorShape = {
  status: number | null;
  detail: string;
  body: unknown;
  kind: AdminApiErrorKind;
};

export type ApiErrorViewModel = {
  kind: AdminApiErrorKind;
  title: string;
  message: string;
};

export type WorkspaceListItemViewModel = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: GroupWorkspaceStatus;
  memberCount: number | null;
  paperCount: number | null;
};

export type WorkspaceBoardViewModel = {
  workspaceId: string;
  title: string;
  description: string | null;
  status: GroupWorkspaceStatus;
  memberCount: number;
  paperCount: number;
  blockedPaperCount: number;
  papersWithSignalsCount: number;
  members: GroupWorkspaceMemberSummaryRead[];
  papers: WorkspacePaperSnapshotRead[];
};

export type LookupOption = {
  id: string;
  label: string;
  hint: string | null;
};

export type ShareGrantOneTimeDisplayModel = {
  grantId: string;
  shareKind: ResultShareKind;
  displayLabel: string | null;
  plainTextToken: string;
  expiresAt: string | null;
  copyHint: string;
};

export type GroupWorkspaceSafeSummaryRead = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: GroupWorkspaceStatus;
};

export type GroupWorkspaceConversionAttributionRead = {
  direct_attribution_metrics: string[];
  workspace_level_aggregate_metrics: string[];
  notes: string[];
};

export type GroupWorkspaceConversionOverviewRead = {
  window_start: string | null;
  window_end: string | null;
  total_share_view_events: number;
  bootstrap_view_count: number;
  content_view_count: number;
  redirect_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  resolved_event_count: number;
  rejected_event_count: number;
  by_share_kind: Record<string, number>;
  by_access_mode: Record<string, number>;
  by_handoff_target: Record<string, number>;
  invite_claimed_count: number;
  invite_already_member_count: number;
  invite_rejected_count: number;
  collect_collected_count: number;
  collect_already_present_count: number;
  collect_rejected_count: number;
  unique_result_share_grant_count: number;
  unique_workspace_count: number;
  last_activity_at: string | null;
  attribution_scope: GroupWorkspaceConversionAttributionRead;
};

export type GroupWorkspaceWorkspaceConversionOverviewRead = {
  window_start: string | null;
  window_end: string | null;
  workspace: GroupWorkspaceSafeSummaryRead;
  active_workspace_board_share_grant_count: number;
  active_digest_issue_share_grant_count: number;
  active_paper_snapshot_share_grant_count: number;
  active_invite_grant_count: number;
  workspace_board_view_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  invite_claimed_count: number;
  invite_already_member_count: number;
  collect_collected_count: number;
  collect_already_present_count: number;
  unique_collected_paper_count: number;
  unique_collecting_user_count: number;
  last_activity_at: string | null;
  attribution_scope: GroupWorkspaceConversionAttributionRead;
};

export type ConversionDailyBucketRead = {
  day: string;
  share_view_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  invite_claimed_count: number;
  invite_already_member_count: number;
  collect_collected_count: number;
  collect_already_present_count: number;
};

export type ConversionTopWorkspaceRead = {
  workspace: GroupWorkspaceSafeSummaryRead;
  workspace_board_view_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  invite_claimed_count: number;
  collect_collected_count: number;
  last_activity_at: string | null;
};

export type ConversionTopResultShareGrantRead = {
  result_share_grant_id: string;
  share_kind: ResultShareKind;
  bootstrap_view_count: number;
  content_view_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  collect_collected_count: number;
  last_activity_at: string | null;
};

export type ConversionRecentShareEventRead = {
  id: string;
  result_share_grant_id: string | null;
  result_share_alias_id: string | null;
  share_kind: ResultShareKind;
  access_mode: string;
  event_type: string;
  outcome: string;
  handoff_target_kind: string | null;
  occurred_at: string;
};

export type GroupWorkspaceInviteClaimStatus = "claimed" | "already_member" | "rejected";

export type ConversionRecentInviteClaimRead = {
  id: string;
  invite_grant_id: string;
  workspace_id: string;
  user_id: string;
  claim_status: GroupWorkspaceInviteClaimStatus;
  role_assigned: GroupWorkspaceMemberRole | null;
  claimed_at: string | null;
  reason_codes: string[];
};

export type GroupWorkspaceResultCollectStatus =
  | "collected"
  | "already_present"
  | "rejected";

export type ConversionRecentCollectRecordRead = {
  id: string;
  workspace_id: string;
  user_id: string;
  result_share_grant_id: string | null;
  share_kind: ResultShareKind;
  collected_paper_id: string;
  status: GroupWorkspaceResultCollectStatus;
  reason_codes: string[];
  created_at: string;
};

export type ConversionActiveShareGrantSnapshotRead = {
  active_workspace_board_share_grant_count: number;
  active_digest_issue_share_grant_count: number;
  active_paper_snapshot_share_grant_count: number;
};

export type ConversionActiveInviteGrantSnapshotRead = {
  active_invite_grant_count: number;
};

export type GroupWorkspaceConversionDrilldownRead = {
  window_start: string | null;
  window_end: string | null;
  daily_buckets: ConversionDailyBucketRead[];
  top_workspaces: ConversionTopWorkspaceRead[];
  top_result_share_grants: ConversionTopResultShareGrantRead[];
  recent_share_events: ConversionRecentShareEventRead[];
  recent_invite_claims: ConversionRecentInviteClaimRead[];
  recent_collect_records: ConversionRecentCollectRecordRead[];
  attribution_scope: GroupWorkspaceConversionAttributionRead;
  notes: string[];
};

export type GroupWorkspaceWorkspaceConversionDrilldownRead = {
  window_start: string | null;
  window_end: string | null;
  workspace: GroupWorkspaceSafeSummaryRead;
  daily_buckets: ConversionDailyBucketRead[];
  recent_share_events: ConversionRecentShareEventRead[];
  recent_invite_claims: ConversionRecentInviteClaimRead[];
  recent_collect_records: ConversionRecentCollectRecordRead[];
  active_share_grant_snapshot: ConversionActiveShareGrantSnapshotRead;
  active_invite_grant_snapshot: ConversionActiveInviteGrantSnapshotRead;
  attribution_scope: GroupWorkspaceConversionAttributionRead;
  notes: string[];
};

export type ConversionMetricBucketViewModel = {
  key: string;
  label: string;
  count: number;
};

export type ConversionMetricSectionViewModel = {
  title: string;
  rows: ConversionMetricBucketViewModel[];
  emptyLabel: string;
};

export type ConversionSummaryMetricViewModel = {
  label: string;
  value: number;
  hint: string | null;
};

export type ConversionAttributionScopeViewModel = {
  directMetrics: string[];
  workspaceLevelAggregateMetrics: string[];
  notes: string[];
};

export type DrilldownAttributionScopeViewModel = {
  directMetrics: string[];
  workspaceLevelAggregateMetrics: string[];
  notes: string[];
};

export type ConversionDetailRowViewModel = {
  label: string;
  value: string;
};

export type ConversionDailyBucketViewModel = {
  day: string;
  metrics: ConversionMetricBucketViewModel[];
};

export type ConversionRecentShareEventViewModel = {
  id: string;
  title: string;
  subtitle: string;
  occurredAt: string;
  detailRows: ConversionDetailRowViewModel[];
};

export type ConversionRecentInviteClaimViewModel = {
  id: string;
  title: string;
  subtitle: string;
  occurredAt: string | null;
  detailRows: ConversionDetailRowViewModel[];
};

export type ConversionRecentCollectRecordViewModel = {
  id: string;
  title: string;
  subtitle: string;
  occurredAt: string;
  detailRows: ConversionDetailRowViewModel[];
};

export type ConversionTopWorkspaceViewModel = {
  workspaceId: string;
  title: string;
  subtitle: string;
  lastActivityAt: string | null;
  metrics: ConversionMetricBucketViewModel[];
};

export type ConversionTopResultShareGrantViewModel = {
  resultShareGrantId: string;
  title: string;
  subtitle: string;
  lastActivityAt: string | null;
  metrics: ConversionMetricBucketViewModel[];
};

export type GlobalConversionDrilldownViewModel = {
  summaryMetrics: ConversionSummaryMetricViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  dailyBuckets: ConversionDailyBucketViewModel[];
  topWorkspaces: ConversionTopWorkspaceViewModel[];
  topResultShareGrants: ConversionTopResultShareGrantViewModel[];
  recentShareEvents: ConversionRecentShareEventViewModel[];
  recentInviteClaims: ConversionRecentInviteClaimViewModel[];
  recentCollectRecords: ConversionRecentCollectRecordViewModel[];
  attributionScope: DrilldownAttributionScopeViewModel;
  notes: string[];
  empty: boolean;
};

export type WorkspaceConversionDrilldownViewModel = {
  workspace: GroupWorkspaceSafeSummaryRead;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  dailyBuckets: ConversionDailyBucketViewModel[];
  recentShareEvents: ConversionRecentShareEventViewModel[];
  recentInviteClaims: ConversionRecentInviteClaimViewModel[];
  recentCollectRecords: ConversionRecentCollectRecordViewModel[];
  activeShareGrantSnapshotRows: ConversionMetricBucketViewModel[];
  activeInviteGrantSnapshotRows: ConversionMetricBucketViewModel[];
  attributionScope: DrilldownAttributionScopeViewModel;
  notes: string[];
  empty: boolean;
};

export type GlobalConversionOverviewViewModel = {
  summaryMetrics: ConversionSummaryMetricViewModel[];
  sections: ConversionMetricSectionViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  attributionScope: ConversionAttributionScopeViewModel;
  empty: boolean;
};

export type WorkspaceConversionOverviewViewModel = {
  workspace: GroupWorkspaceSafeSummaryRead;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  sections: ConversionMetricSectionViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  attributionScope: ConversionAttributionScopeViewModel;
  empty: boolean;
};
