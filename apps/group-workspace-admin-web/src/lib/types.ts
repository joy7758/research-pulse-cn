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
export type ResultShareAliasStatus = "active" | "revoked" | "expired";
export type ResultShareKind = "digest_issue" | "paper_snapshot" | "workspace_board";
export type ResultShareViewAccessMode = "share_token" | "alias" | "alias_redirect";
export type ResultShareViewEventType =
  | "bootstrap_view"
  | "content_view"
  | "redirect"
  | "invite_handoff_redirect"
  | "collect_handoff_redirect";
export type ResultShareViewOutcome = "resolved" | "rejected";
export type ResultShareHandoffTargetKind =
  | "group_workspace_invite_entry"
  | "result_share_collect_entry";

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

export type ResultShareAliasRead = {
  id: string;
  result_share_grant_id: string;
  share_kind: ResultShareKind;
  status: ResultShareAliasStatus;
  display_label: string | null;
  alias_prefix: string | null;
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

export type ResultShareGrantSummaryRead = {
  grant_id: string;
  share_kind: ResultShareKind;
  workspace_id: string | null;
  digest_issue_id: string | null;
  paper_id: string | null;
  status: ResultShareGrantStatus;
  display_label: string | null;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
};

export type ResultShareAliasSummaryRead = {
  alias_id: string;
  result_share_grant_id: string;
  share_kind: ResultShareKind;
  alias_prefix: string | null;
  status: ResultShareAliasStatus;
  display_label: string | null;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
};

export type ResultShareRecentEventRead = {
  id: string;
  result_share_grant_id: string | null;
  result_share_alias_id: string | null;
  share_kind: ResultShareKind;
  access_mode: ResultShareViewAccessMode;
  event_type: ResultShareViewEventType;
  outcome: ResultShareViewOutcome;
  handoff_target_kind: ResultShareHandoffTargetKind | null;
  occurred_at: string;
};

export type ResultShareDirectCollectRecordRead = {
  id: string;
  workspace_id: string;
  user_id: string;
  result_share_grant_id: string;
  share_kind: ResultShareKind;
  collected_paper_id: string;
  status: GroupWorkspaceResultCollectStatus;
  reason_codes: string[];
  created_at: string;
};

export type ResultShareAttributionScopeRead = {
  direct_event_metrics: string[];
  direct_collect_metrics: string[];
  non_attribution_fields: string[];
  notes: string[];
};

export type ResultShareGrantConversionDrilldownRead = {
  share_grant: ResultShareGrantSummaryRead;
  window_start: string | null;
  window_end: string | null;
  total_events: number;
  bootstrap_view_count: number;
  content_view_count: number;
  redirect_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  resolved_event_count: number;
  rejected_event_count: number;
  by_access_mode: Record<string, number>;
  by_event_type: Record<string, number>;
  by_outcome: Record<string, number>;
  active_alias_count: number;
  aliases: ResultShareAliasSummaryRead[];
  recent_events: ResultShareRecentEventRead[];
  direct_collect_records: ResultShareDirectCollectRecordRead[];
  direct_collect_collected_count: number;
  direct_collect_already_present_count: number;
  direct_collect_rejected_count: number;
  unique_collecting_user_count: number;
  last_activity_at: string | null;
  attribution_scope: ResultShareAttributionScopeRead;
  notes: string[];
};

export type ResultShareAliasConversionDrilldownRead = {
  alias: ResultShareAliasSummaryRead;
  result_share_grant: ResultShareGrantSummaryRead;
  window_start: string | null;
  window_end: string | null;
  total_events: number;
  bootstrap_view_count: number;
  content_view_count: number;
  redirect_count: number;
  invite_handoff_redirect_count: number;
  collect_handoff_redirect_count: number;
  resolved_event_count: number;
  rejected_event_count: number;
  by_event_type: Record<string, number>;
  by_outcome: Record<string, number>;
  recent_events: ResultShareRecentEventRead[];
  last_activity_at: string | null;
  attribution_scope: ResultShareAttributionScopeRead;
  notes: string[];
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
  access_mode: ResultShareViewAccessMode;
  event_type: ResultShareViewEventType;
  outcome: ResultShareViewOutcome;
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

export type ConversionFilterInput = {
  dateFrom: string | null;
  dateTo: string | null;
  shareKind: ResultShareKind | null;
  accessMode: ResultShareViewAccessMode | null;
  eventType: ResultShareViewEventType | null;
  outcome: ResultShareViewOutcome | null;
  limit: number | null;
};

export type ConversionFilterSupportViewModel = {
  overviewSupportsDimensions: boolean;
  overviewSupportsOutcome: boolean;
  drilldownSupportsDimensions: boolean;
  drilldownSupportsOutcome: boolean;
  drilldownSupportsLimit: boolean;
  dimensionScopeLabel?: string;
  showShareKind?: boolean;
  showAccessMode?: boolean;
  showEventType?: boolean;
};

export type ConversionFilterChipViewModel = {
  key: string;
  label: string;
  value: string;
};

export type ConversionFilterSummaryViewModel = {
  windowLabel: string;
  chips: ConversionFilterChipViewModel[];
  scopeNotes: string[];
  hasActiveFilters: boolean;
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

export type ResultShareAttributionScopeViewModel = {
  directEventMetrics: string[];
  directCollectMetrics: string[];
  nonAttributionFields: string[];
  notes: string[];
};

export type ResultShareGrantSummaryViewModel = {
  grantId: string;
  title: string;
  subtitle: string;
  shareKind: ResultShareKind;
  status: ResultShareGrantStatus;
  displayLabel: string | null;
  expiresAt: string | null;
  lastUsedAt: string | null;
  createdAt: string;
};

export type ResultShareAliasSummaryViewModel = {
  aliasId: string;
  title: string;
  subtitle: string;
  shareKind: ResultShareKind;
  status: ResultShareAliasStatus;
  displayLabel: string | null;
  aliasPrefix: string | null;
  expiresAt: string | null;
  lastUsedAt: string | null;
  createdAt: string;
};

export type ResultShareRecentEventViewModel = {
  id: string;
  title: string;
  subtitle: string;
  occurredAt: string;
  detailRows: ConversionDetailRowViewModel[];
};

export type ResultShareDirectCollectRecordViewModel = {
  id: string;
  title: string;
  subtitle: string;
  occurredAt: string;
  detailRows: ConversionDetailRowViewModel[];
};

export type ResultShareGrantDrilldownViewModel = {
  shareGrant: ResultShareGrantSummaryViewModel;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  byAccessModeRows: ConversionMetricBucketViewModel[];
  byEventTypeRows: ConversionMetricBucketViewModel[];
  byOutcomeRows: ConversionMetricBucketViewModel[];
  aliases: ResultShareAliasSummaryViewModel[];
  recentEvents: ResultShareRecentEventViewModel[];
  directCollectRecords: ResultShareDirectCollectRecordViewModel[];
  attributionScope: ResultShareAttributionScopeViewModel;
  notes: string[];
  empty: boolean;
};

export type ResultShareAliasDrilldownViewModel = {
  alias: ResultShareAliasSummaryViewModel;
  resultShareGrant: ResultShareGrantSummaryViewModel;
  summaryMetrics: ConversionSummaryMetricViewModel[];
  windowStart: string | null;
  windowEnd: string | null;
  lastActivityAt: string | null;
  byEventTypeRows: ConversionMetricBucketViewModel[];
  byOutcomeRows: ConversionMetricBucketViewModel[];
  recentEvents: ResultShareRecentEventViewModel[];
  attributionScope: ResultShareAttributionScopeViewModel;
  notes: string[];
  empty: boolean;
};

export type ResultShareRegistryFilterInput = {
  shareKind: ResultShareKind | null;
  grantStatus: ResultShareGrantStatus | null;
  aliasStatus: ResultShareAliasStatus | null;
  workspaceId: string | null;
  resultShareGrantId: string | null;
};

export type ResultShareRegistrySortField =
  | "createdAt"
  | "lastUsedAt"
  | "expiresAt"
  | "shareKind"
  | "status";

export type ResultShareRegistrySortDirection = "asc" | "desc";

export type ResultShareRegistrySectionSortInput = {
  field: ResultShareRegistrySortField;
  direction: ResultShareRegistrySortDirection;
};

export type ResultShareRegistrySortInput = {
  grants: ResultShareRegistrySectionSortInput;
  aliases: ResultShareRegistrySectionSortInput;
};

export type ResultShareRegistrySavedViewScope = "grant_registry" | "alias_registry";
export type ResultShareRegistrySavedViewApplyMode =
  | "registry_only"
  | "registry_and_drilldown";

export type ResultShareRegistrySavedViewDrilldownContext = {
  dateFrom: string | null;
  dateTo: string | null;
  accessMode: ResultShareViewAccessMode | null;
  eventType: ResultShareViewEventType | null;
  outcome: ResultShareViewOutcome | null;
  limit: number | null;
};

export type ResultShareRegistrySavedView = {
  id: string;
  name: string;
  scope: ResultShareRegistrySavedViewScope;
  filters: ResultShareRegistryFilterInput;
  sort: ResultShareRegistrySectionSortInput;
  drilldownContext: ResultShareRegistrySavedViewDrilldownContext | null;
  createdAt: string;
  updatedAt: string;
};

export type ResultShareRegistrySavedViewDraft = {
  name: string;
  scope: ResultShareRegistrySavedViewScope;
  filters: ResultShareRegistryFilterInput;
  sort: ResultShareRegistrySectionSortInput;
  drilldownContext: ResultShareRegistrySavedViewDrilldownContext | null;
};

export type ResultShareRegistrySavedViewSummary = {
  id: string;
  name: string;
  scope: ResultShareRegistrySavedViewScope;
  summaryItems: string[];
  drilldownSummaryItems: string[];
  hasDrilldownContext: boolean;
  createdAt: string;
  updatedAt: string;
  isDefault: boolean;
  isPinned: boolean;
};

export type ResultShareRegistrySavedViewStoreState = {
  grantPresets: ResultShareRegistrySavedView[];
  aliasPresets: ResultShareRegistrySavedView[];
  defaultPresetId: string | null;
};

export type ResultShareRegistryPresetImportMode = "merge" | "replace";

export type ResultShareRegistryPresetExportPayload = {
  schemaVersion: "result-share-registry-presets.v1";
  exportedAt: string;
  app: "research-pulse-cn";
  source: "group-workspace-admin-web";
  presets: {
    grantRegistry: ResultShareRegistrySavedView[];
    aliasRegistry: ResultShareRegistrySavedView[];
  };
};

export type ResultShareRegistryPresetImportPreview = {
  schemaVersion: string | null;
  validPresetCount: number;
  invalidPresetCount: number;
  grantPresetCount: number;
  aliasPresetCount: number;
  warnings: string[];
  errors: string[];
  canApply: boolean;
  importedScopes: {
    grantRegistry: boolean;
    aliasRegistry: boolean;
  };
  presets: {
    grantRegistry: ResultShareRegistrySavedView[];
    aliasRegistry: ResultShareRegistrySavedView[];
  };
};

export type ResultShareRegistryPresetImportApplyResult = {
  store: ResultShareRegistrySavedViewStoreState;
  importedGrantCount: number;
  importedAliasCount: number;
  defaultPresetCleared: boolean;
};

export type ResultShareRegistryPresetIntegrityIssueCode =
  | "invalid_json"
  | "invalid_schema_version"
  | "invalid_scope"
  | "unsafe_field_detected"
  | "invalid_filter_shape"
  | "invalid_sort_shape"
  | "invalid_drilldown_context"
  | "missing_required_field"
  | "duplicate_preset_id"
  | "dangling_default_preset"
  | "storage_key_unreadable"
  | "storage_key_not_array";

export type ResultShareRegistryPresetIntegrityIssue = {
  severity: "warning" | "error";
  scope: ResultShareRegistrySavedViewScope | "storage";
  presetId: string | null;
  presetName: string | null;
  code: ResultShareRegistryPresetIntegrityIssueCode;
  message: string;
  safeDetails: string | null;
};

export type ResultShareRegistryPresetIntegrityReport = {
  checkedAt: string;
  grantPresetCount: number;
  aliasPresetCount: number;
  validPresetCount: number;
  invalidPresetCount: number;
  warningCount: number;
  errorCount: number;
  issues: ResultShareRegistryPresetIntegrityIssue[];
  canAutoRepair: boolean;
  canResetGrantScope: boolean;
  canResetAliasScope: boolean;
  notes: string[];
};

export type ResultShareRegistryPresetRecoveryAction =
  | "discard_invalid_grant_presets"
  | "discard_invalid_alias_presets"
  | "clear_dangling_default_preset"
  | "reset_grant_scope"
  | "reset_alias_scope"
  | "reset_all_presets"
  | "restore_last_good_backup";

export type ResultShareRegistryPresetBackupSnapshot = {
  schemaVersion: "result-share-registry-presets-backup.v1";
  createdAt: string;
  reason: string;
  grantRegistry: ResultShareRegistrySavedView[];
  aliasRegistry: ResultShareRegistrySavedView[];
  defaultPresetId: string | null;
};

export type ResultShareRegistryPresetStorageDiagnostics = {
  checkedAt: string;
  storageKeysPresent: {
    grantPresets: boolean;
    aliasPresets: boolean;
    defaultPresetId: boolean;
    lastGoodBackup: boolean;
    workspaceState: boolean;
  };
  grantPresetCount: number;
  aliasPresetCount: number;
  validPresetCount: number;
  invalidPresetCount: number;
  defaultPresetIdPresent: boolean;
  lastBackupPresent: boolean;
  workspaceStatePresent: boolean;
  workspaceStateWarning: string | null;
  latestValidationAt: string | null;
  warningCount: number;
  errorCount: number;
  notes: string[];
};

export type ResultShareRegistryPresetLocalAuditActionType =
  | "preset_saved"
  | "preset_applied"
  | "preset_overwritten"
  | "preset_deleted"
  | "preset_pinned"
  | "preset_unpinned"
  | "preset_workspace_health_checked"
  | "preset_workspace_health_thresholds_updated"
  | "preset_workspace_health_thresholds_reset"
  | "preset_workspace_health_threshold_validation_failed"
  | "preset_workspace_export_created"
  | "preset_workspace_import_dry_run"
  | "preset_workspace_import_merge"
  | "preset_workspace_import_replace"
  | "preset_workspace_backup_created"
  | "preset_workspace_backup_restored"
  | "preset_workspace_import_validation_failed"
  | "default_set"
  | "default_cleared"
  | "import_dry_run"
  | "import_merge"
  | "import_replace"
  | "export_created"
  | "integrity_checked"
  | "invalid_presets_discarded"
  | "scope_reset"
  | "all_presets_reset"
  | "dangling_default_cleared"
  | "backup_created"
  | "backup_restored"
  | "recovery_failed"
  | "validation_failed"
  | "preset_workspace_reset"
  | "stale_pins_cleaned";

export type ResultShareRegistryPresetLocalAuditStatus =
  | "success"
  | "warning"
  | "failed";

export type ResultShareRegistryPresetLocalAuditEvent = {
  id: string;
  occurredAt: string;
  actionType: ResultShareRegistryPresetLocalAuditActionType;
  scope: ResultShareRegistrySavedViewScope | "storage" | null;
  presetId: string | null;
  presetName: string | null;
  status: ResultShareRegistryPresetLocalAuditStatus;
  summary: string;
  safeDetails: string | null;
};

export type ResultShareRegistryPresetLocalAuditSummary = {
  totalEvents: number;
  successCount: number;
  warningCount: number;
  failedCount: number;
  lastEventAt: string | null;
  byActionType: Record<ResultShareRegistryPresetLocalAuditActionType, number>;
  byScope: {
    grant_registry: number;
    alias_registry: number;
    storage: number;
    unscoped: number;
  };
  recentEvents: ResultShareRegistryPresetLocalAuditEvent[];
  backupRelatedCount: number;
  recoveryRelatedCount: number;
  importRelatedCount: number;
  exportRelatedCount: number;
  storageWarning: string | null;
};

export type ResultShareRegistryPresetLocalAuditLoadResult = {
  events: ResultShareRegistryPresetLocalAuditEvent[];
  storageWarning: string | null;
};

export type ResultShareRegistryPresetWorkspaceState = {
  pinnedGrantPresetIds: string[];
  pinnedAliasPresetIds: string[];
  lastActivePresetScope: ResultShareRegistrySavedViewScope | null;
  lastActivePresetId: string | null;
  collapsedSections: {
    pinnedGrantPresets: boolean;
    pinnedAliasPresets: boolean;
    recentGrantPresets: boolean;
    recentAliasPresets: boolean;
    recentActivity: boolean;
    storageHealth: boolean;
  } | null;
  updatedAt: string;
};

export type ResultShareRegistryPresetWorkspaceLoadResult = {
  state: ResultShareRegistryPresetWorkspaceState;
  storageWarning: string | null;
  keyPresent: boolean;
};

export type ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey =
  | "storageInvalidJson"
  | "workspaceStateWarning"
  | "unsafeFieldDetected"
  | "invalidSchemaVersion"
  | "danglingDefaultPreset"
  | "stalePinnedPreset"
  | "allPinnedPresetsStale"
  | "missingPresetBackup"
  | "missingWorkspaceBackup"
  | "corruptedAuditHistory"
  | "recentFailedImport"
  | "recentFailedRecovery"
  | "noSavedPresets"
  | "invalidDrilldownContext"
  | "importPreviewHasErrors";

export type ResultShareRegistryPresetWorkspaceHealthThresholdPreferences = {
  statusThresholds: {
    healthyMin: number;
    attentionMin: number;
    riskMin: number;
    criticalMin: number;
  };
  findingPenaltyOverrides: Partial<
    Record<ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey, number>
  >;
  recommendationVisibility: {
    showInfo: boolean;
    showWarnings: boolean;
    showErrors: boolean;
    showCritical: boolean;
  };
  updatedAt: string;
};

export type ResultShareRegistryPresetWorkspaceHealthThresholdDraft = {
  statusThresholds: {
    healthyMin: string;
    attentionMin: string;
    riskMin: string;
    criticalMin: string;
  };
  findingPenaltyOverrides: Partial<
    Record<ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey, string>
  >;
  recommendationVisibility: {
    showInfo: boolean;
    showWarnings: boolean;
    showErrors: boolean;
    showCritical: boolean;
  };
};

export type ResultShareRegistryPresetWorkspaceHealthThresholdPreview = {
  currentScore: number;
  currentStatus: ResultShareRegistryPresetWorkspaceHealthStatus;
  draftScore: number;
  draftStatus: ResultShareRegistryPresetWorkspaceHealthStatus;
  scoreChanged: boolean;
  statusChanged: boolean;
  summary: string;
};

export type ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult = {
  valid: boolean;
  warnings: string[];
  errors: string[];
  normalizedPreferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences | null;
  previewStatusImpact: ResultShareRegistryPresetWorkspaceHealthThresholdPreview | null;
};

export type ResultShareRegistryPresetWorkspaceHealthThresholdLoadResult = {
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences;
  storageWarning: string | null;
  keyPresent: boolean;
  source: "default" | "local";
};

export type ResultShareRegistryPresetWorkspaceViewModel = {
  overviewSummary: ResultShareRegistrySummaryViewModel[];
  lastActivePresetLabel: string | null;
  pinnedGrantPresets: ResultShareRegistrySavedViewSummary[];
  pinnedAliasPresets: ResultShareRegistrySavedViewSummary[];
  recentGrantPresets: ResultShareRegistrySavedViewSummary[];
  recentAliasPresets: ResultShareRegistrySavedViewSummary[];
  staleGrantPinIds: string[];
  staleAliasPinIds: string[];
  recentActivity: ResultShareRegistryPresetLocalAuditEvent[];
  storageHealth: {
    issueCount: number;
    lastBackupLabel: string;
    workspaceBackupLabel: string;
    auditWarning: string | null;
    workspaceWarning: string | null;
    latestValidationAt: string | null;
  };
};

export type ResultShareRegistryPresetWorkspaceHealthStatus =
  | "healthy"
  | "attention"
  | "risk"
  | "critical";

export type ResultShareRegistryPresetWorkspaceHealthFindingSeverity =
  | "info"
  | "warning"
  | "error"
  | "critical";

export type ResultShareRegistryPresetWorkspaceHealthFindingCode =
  | "storage_invalid_json"
  | "unsafe_field_detected"
  | "invalid_schema_version"
  | "dangling_default_preset"
  | "stale_pinned_presets"
  | "missing_last_good_backup"
  | "corrupted_audit_history"
  | "recent_failed_import"
  | "recent_failed_recovery"
  | "no_saved_presets"
  | "no_pinned_presets"
  | "invalid_drilldown_context"
  | "import_preview_has_errors";

export type ResultShareRegistryPresetWorkspaceHealthRecommendationKind =
  | "run_integrity_check"
  | "discard_invalid_presets"
  | "clean_stale_pins"
  | "create_backup"
  | "restore_last_good_backup"
  | "validate_import_before_apply"
  | "reset_workspace_state"
  | "review_recent_audit_failures"
  | "add_pinned_presets";

export type ResultShareRegistryPresetWorkspaceHealthBreakdown = {
  storageIntegrity: number;
  presetValidity: number;
  pinnedPresetHygiene: number;
  backupReadiness: number;
  auditReliability: number;
  importExportSafety: number;
  drilldownContextCompleteness: number;
};

export type ResultShareRegistryPresetWorkspaceHealthFinding = {
  severity: ResultShareRegistryPresetWorkspaceHealthFindingSeverity;
  code: ResultShareRegistryPresetWorkspaceHealthFindingCode;
  summary: string;
  detail: string;
};

export type ResultShareRegistryPresetWorkspaceHealthRecommendation = {
  kind: ResultShareRegistryPresetWorkspaceHealthRecommendationKind;
  label: string;
  detail: string;
};

export type ResultShareRegistryPresetWorkspaceHealthScore = {
  score: number;
  status: ResultShareRegistryPresetWorkspaceHealthStatus;
  checkedAt: string;
  summary: string;
  thresholdPreferenceSource: "default" | "local";
  thresholdSummary: string[];
  thresholdWarnings: string[];
  breakdown: ResultShareRegistryPresetWorkspaceHealthBreakdown;
  findings: ResultShareRegistryPresetWorkspaceHealthFinding[];
  recommendations: ResultShareRegistryPresetWorkspaceHealthRecommendation[];
  notes: string[];
};

export type ResultShareRegistryPresetWorkspaceExportPayload = {
  schemaVersion: "result-share-registry-preset-workspace.v1";
  exportedAt: string;
  app: "research-pulse-cn";
  source: "group-workspace-admin-web";
  workspaceState: ResultShareRegistryPresetWorkspaceState;
};

export type ResultShareRegistryPresetWorkspaceImportPreview = {
  schemaVersion: string | null;
  valid: boolean;
  canApply: boolean;
  warnings: string[];
  errors: string[];
  pinnedGrantPresetCount: number;
  pinnedAliasPresetCount: number;
  stalePinnedGrantPresetIds: string[];
  stalePinnedAliasPresetIds: string[];
  lastActivePresetExists: boolean;
  workspaceState: ResultShareRegistryPresetWorkspaceState | null;
};

export type ResultShareRegistryPresetWorkspaceImportApplyResult = {
  workspaceState: ResultShareRegistryPresetWorkspaceState;
  stalePinnedGrantPresetIds: string[];
  stalePinnedAliasPresetIds: string[];
  lastActivePresetCleared: boolean;
};

export type ResultShareRegistryPresetWorkspaceBackupSnapshot = {
  schemaVersion: "result-share-registry-preset-workspace-backup.v1";
  createdAt: string;
  reason: string;
  workspaceState: ResultShareRegistryPresetWorkspaceState;
};

export type ResultShareRegistryFilterChipViewModel = {
  key: string;
  label: string;
  value: string;
};

export type ResultShareRegistryFilterSummaryViewModel = {
  chips: ResultShareRegistryFilterChipViewModel[];
  scopeNotes: string[];
  hasActiveFilters: boolean;
};

export type ResultShareRegistrySummaryViewModel = {
  label: string;
  value: number;
  hint: string | null;
};

export type ResultShareGrantRegistryItemViewModel = {
  grantId: string;
  title: string;
  subtitle: string;
  shareKind: ResultShareKind;
  status: ResultShareGrantStatus;
  displayLabel: string | null;
  workspaceId: string | null;
  digestIssueId: string | null;
  paperId: string | null;
  expiresAt: string | null;
  lastUsedAt: string | null;
  createdAt: string;
  aliasCount: number;
  activeAliasCount: number;
  hasRecentAliasUsage: boolean;
  relationshipHint: string;
};

export type ResultShareAliasRegistryItemViewModel = {
  aliasId: string;
  grantId: string;
  title: string;
  subtitle: string;
  shareKind: ResultShareKind;
  status: ResultShareAliasStatus;
  displayLabel: string | null;
  aliasPrefix: string | null;
  expiresAt: string | null;
  lastUsedAt: string | null;
  createdAt: string;
  grantTitle: string;
  grantStatus: ResultShareGrantStatus | null;
  linkedGrantInRegistry: boolean;
  relationshipHint: string;
};

export type ResultShareRegistryEmptyStateViewModel = {
  title: string;
  message: string;
};

export type ResultShareRegistrySectionViewModel<TItem> = {
  title: string;
  description: string;
  summaryMetrics: ResultShareRegistrySummaryViewModel[];
  items: TItem[];
  emptyState: ResultShareRegistryEmptyStateViewModel;
};

export type ResultShareRegistryViewModel = {
  grants: ResultShareRegistrySectionViewModel<ResultShareGrantRegistryItemViewModel>;
  aliases: ResultShareRegistrySectionViewModel<ResultShareAliasRegistryItemViewModel>;
};
