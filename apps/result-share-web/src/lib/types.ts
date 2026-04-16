export type ResultShareKind = "digest_issue" | "paper_snapshot" | "workspace_board" | string;
export type ResultShareAccessMode = "token" | "alias";
export type ResultShareGrantStatus = "active" | "revoked" | "expired" | string;
export type DigestFallbackMode = "structured" | "highlights_only" | "empty" | string;
export type GroupWorkspaceCollectStatus =
  | "collected"
  | "already_present"
  | "rejected"
  | string;
export type SharedTodaySectionKind =
  | "today_focus"
  | "yesterday_recap"
  | "signal_updates"
  | "related_papers"
  | "other_updates"
  | string;
export type GroupWorkspaceMembershipRole = "owner" | "editor" | "viewer" | string;

export type ShareGrantPublicSummaryRead = {
  id: string;
  share_kind: ResultShareKind;
  display_label: string | null;
  status: ResultShareGrantStatus;
  expires_at: string | null;
  created_at: string;
};

export type ShareGrantTargetSummaryRead = {
  workspace_id: string | null;
  digest_issue_id: string | null;
  paper_id: string | null;
  title: string | null;
};

export type ShareGrantCollectionReserveRead = {
  supported: boolean;
  share_kind_collectable: boolean;
  collect_supported_via_self_service: boolean;
  source_files_included: boolean;
  notes: string[];
};

export type WorkspaceInviteHandoffReserveRead = {
  supported: boolean;
  share_kind: "workspace_board";
  separate_invite_token_required: boolean;
  invite_bootstrap_available: boolean;
  self_service_claim_supported: boolean;
  direct_claim_via_share_page: boolean;
  handoff_redirect_supported: boolean;
  source_files_included: boolean;
  invite_shell_entry_url: string | null;
  invite_handoff_url: string | null;
  notes: string[];
};

export type ResultCollectHandoffReserveRead = {
  supported: boolean;
  share_kind: "workspace_board";
  separate_result_share_token_required: boolean;
  result_share_bootstrap_available: boolean;
  collect_supported_via_self_service: boolean;
  direct_collect_via_current_share: boolean;
  handoff_redirect_supported: boolean;
  source_files_included: boolean;
  supported_share_kinds: Array<"digest_issue" | "paper_snapshot">;
  result_share_shell_entry_url: string | null;
  collect_handoff_url: string | null;
  notes: string[];
};

export type ShareGrantBootstrapRead = {
  grant: ShareGrantPublicSummaryRead;
  target: ShareGrantTargetSummaryRead;
  collection_reserve: ShareGrantCollectionReserveRead | null;
  workspace_invite_handoff_reserve: WorkspaceInviteHandoffReserveRead | null;
  result_collect_handoff_reserve: ResultCollectHandoffReserveRead | null;
  notes: string[];
};

export type GroupWorkspaceSafeSummaryRead = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: string;
};

export type GroupWorkspaceRead = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: string;
  created_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
};

export type GroupWorkspaceMemberSummaryRead = {
  member_id: string;
  user_id: string;
  role: string;
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

export type SharedDigestItemRead = {
  sort_order: number;
  pulse_card_id: string;
  card_type: string;
  source_paper_id: string | null;
  title: string;
  summary: string;
  why_now: string | null;
  action_text: string | null;
  deep_link: string | null;
  paper: WorkspacePaperSnapshotRead | null;
};

export type SharedTodaySectionRead = {
  kind: SharedTodaySectionKind;
  title: string;
  item_count: number;
  items: SharedDigestItemRead[];
};

export type SharedTodayQuickStatsRead = {
  selected_card_count: number;
  related_paper_count: number;
  signal_update_count: number;
  touched_paper_count: number;
};

export type SharedTodayPublicationPreviewRead = {
  digest_title: string | null;
  digest_subtitle: string | null;
  digest_highlights: SharedDigestItemRead[];
  primary_cta_text: string | null;
  primary_cta_path: string | null;
  mini_program_path: string | null;
  article_url: string | null;
};

export type SharedDigestIssueRead = {
  share_kind: "digest_issue";
  id: string;
  issue_date: string;
  status: string;
  title: string;
  summary: string;
  highlight_count: number;
  selected_card_count: number;
  deep_link_path: string | null;
  highlights: SharedDigestItemRead[];
  is_structured: boolean;
  fallback_mode: DigestFallbackMode;
  section_order: SharedTodaySectionKind[];
  sections: SharedTodaySectionRead[];
  quick_stats: SharedTodayQuickStatsRead | null;
  focus_card: SharedDigestItemRead | null;
  publication_preview: SharedTodayPublicationPreviewRead | null;
  items: SharedDigestItemRead[];
};

export type SharedPaperSnapshotRead = WorkspacePaperSnapshotRead & {
  share_kind: "paper_snapshot";
};

export type SharedWorkspaceBoardRead = {
  share_kind: "workspace_board";
  workspace: GroupWorkspaceRead;
  member_count: number;
  paper_count: number;
  members: GroupWorkspaceMemberSummaryRead[];
  papers: WorkspacePaperSnapshotRead[];
  quick_stats: GroupWorkspaceBoardQuickStatsRead;
};

export type SharedResultContentRead =
  | SharedDigestIssueRead
  | SharedPaperSnapshotRead
  | SharedWorkspaceBoardRead;

export type ResultShareCollectablePaperRead = {
  paper_id: string;
  title: string;
  type: string;
  stage: string;
  venue: string | null;
  priority: number;
  next_action: string | null;
  blocker: string | null;
  progress_percentage: number;
  source_card_type: string | null;
  source_pulse_card_id: string | null;
  source_section_kind: string | null;
  notes: string[] | null;
};

export type ResultShareCollectEligibleWorkspaceRead = {
  workspace: GroupWorkspaceSafeSummaryRead;
  membership_role: GroupWorkspaceMembershipRole;
};

export type ResultShareCollectShareSummaryRead = {
  id: string;
  share_kind: ResultShareKind;
  status: ResultShareGrantStatus;
  display_label: string | null;
  expires_at: string | null;
  target: ShareGrantTargetSummaryRead;
};

export type ResultShareCollectPreviewRead = {
  share: ResultShareCollectShareSummaryRead | null;
  collectable_items: ResultShareCollectablePaperRead[];
  eligible_workspaces: ResultShareCollectEligibleWorkspaceRead[];
  can_collect: boolean;
  reason_codes: string[];
  notes: string[];
};

export type ResultShareCollectedPaperSummaryRead = {
  paper_id: string;
  title: string;
  type: string;
  stage: string;
  venue: string | null;
  priority: number;
  next_action: string | null;
  blocker: string | null;
  progress_percentage: number;
};

export type GroupWorkspaceResultCollectRecordRead = {
  id: string;
  workspace_id: string;
  user_id: string;
  result_share_grant_id: string | null;
  share_kind: ResultShareKind;
  digest_issue_id: string | null;
  source_pulse_card_id: string | null;
  source_paper_id: string | null;
  collected_paper_id: string;
  status: GroupWorkspaceCollectStatus;
  reason_codes: string[];
  created_at: string;
  updated_at: string;
};

export type ResultShareCollectItemResultRead = {
  paper_id: string;
  status: GroupWorkspaceCollectStatus;
  reason_codes: string[];
  collect_record: GroupWorkspaceResultCollectRecordRead | null;
  paper: ResultShareCollectedPaperSummaryRead;
};

export type ResultShareCollectResponseRead = {
  action: "collected" | "already_present" | "rejected";
  workspace: GroupWorkspaceSafeSummaryRead | null;
  collected_results: ResultShareCollectItemResultRead[];
  notes: string[];
};

export type GroupWorkspaceResultCollectionRead = {
  record: GroupWorkspaceResultCollectRecordRead;
  workspace: GroupWorkspaceSafeSummaryRead;
  paper: ResultShareCollectedPaperSummaryRead;
};

export type DigestDisplaySection = {
  kind: SharedTodaySectionKind;
  title: string;
  item_count: number;
  items: SharedDigestItemRead[];
};

export type ShareGrantViewModel = {
  shareKind: ResultShareKind;
  displayLabel: string | null;
  status: ResultShareGrantStatus;
  createdAt: string;
  expiresAt: string | null;
  targetTitle: string | null;
  notes: string[];
  collectionReserve: ShareGrantCollectionReserveRead | null;
  workspaceInviteHandoffReserve: WorkspaceInviteHandoffReserveRead | null;
  resultCollectHandoffReserve: ResultCollectHandoffReserveRead | null;
};

export type WorkspaceInviteHandoffViewModel = {
  supported: boolean;
  separateInviteTokenRequired: boolean;
  inviteBootstrapAvailable: boolean;
  selfServiceClaimSupported: boolean;
  directClaimViaSharePage: boolean;
  handoffRedirectSupported: boolean;
  sourceFilesIncluded: boolean;
  inviteShellEntryUrl: string | null;
  inviteHandoffUrl: string | null;
  notes: string[];
};

export type ResultCollectHandoffViewModel = {
  supported: boolean;
  separateResultShareTokenRequired: boolean;
  resultShareBootstrapAvailable: boolean;
  collectSupportedViaSelfService: boolean;
  directCollectViaCurrentShare: boolean;
  handoffRedirectSupported: boolean;
  sourceFilesIncluded: boolean;
  supportedShareKinds: Array<"digest_issue" | "paper_snapshot">;
  resultShareShellEntryUrl: string | null;
  collectHandoffUrl: string | null;
  notes: string[];
};

export type DigestShareViewModel = ShareGrantViewModel & {
  shareKind: "digest_issue";
  pageTitle: string;
  pageSubtitle: string;
  issueDate: string;
  highlightCount: number;
  selectedCardCount: number;
  deepLinkPath: string | null;
  isStructured: boolean;
  fallbackMode: DigestFallbackMode;
  sectionViews: DigestDisplaySection[];
  quickStats: SharedTodayQuickStatsRead | null;
  focusCard: SharedDigestItemRead | null;
  publicationPreview: SharedTodayPublicationPreviewRead | null;
  legacyHighlights: SharedDigestItemRead[];
};

export type PaperSnapshotViewModel = ShareGrantViewModel & {
  shareKind: "paper_snapshot";
  pageTitle: string;
  metadataRows: Array<{ label: string; value: string }>;
  nextAction: string | null;
  blocker: string | null;
  latestSignalSummary: WorkspacePaperSignalSummaryRead | null;
  ownerName: string | null;
};

export type WorkspaceBoardViewModel = ShareGrantViewModel & {
  shareKind: "workspace_board";
  pageTitle: string;
  description: string | null;
  statusLabel: string;
  memberCount: number;
  paperCount: number;
  quickStats: GroupWorkspaceBoardQuickStatsRead;
  members: GroupWorkspaceMemberSummaryRead[];
  papers: WorkspacePaperSnapshotRead[];
  workspaceInviteHandoff: WorkspaceInviteHandoffViewModel | null;
  resultCollectHandoff: ResultCollectHandoffViewModel | null;
};

export type ResultShareViewModel =
  | DigestShareViewModel
  | PaperSnapshotViewModel
  | WorkspaceBoardViewModel;

export type ShareTokenErrorKind =
  | "invalid_token"
  | "revoked_token"
  | "expired_token"
  | "unauthorized_self_service"
  | "network_error"
  | "request_failed";

export type ShareErrorViewModel = {
  kind: ShareTokenErrorKind;
  title: string;
  message: string;
};

export type CollectablePaperViewModel = {
  paperId: string;
  title: string;
  subtitle: string;
  nextAction: string | null;
  blocker: string | null;
  sourceSummary: string | null;
  notes: string[];
};

export type WorkspaceOptionViewModel = {
  workspaceId: string;
  label: string;
  description: string | null;
  membershipRole: GroupWorkspaceMembershipRole;
  status: string;
};

export type ResultCollectViewModel = {
  shareKind: ResultShareKind | null;
  collectionSupported: boolean;
  shareKindCollectable: boolean;
  collectSupportedViaSelfService: boolean;
  canCollect: boolean;
  requiresPaperSelection: boolean;
  reasonCodes: string[];
  notes: string[];
  collectableItems: CollectablePaperViewModel[];
  eligibleWorkspaces: WorkspaceOptionViewModel[];
};

export type CollectActionResultItemViewModel = {
  paperId: string;
  title: string;
  status: GroupWorkspaceCollectStatus;
  reasonCodes: string[];
};

export type CollectActionResultViewModel = {
  action: "collected" | "already_present" | "rejected";
  title: string;
  message: string;
  notes: string[];
  itemResults: CollectActionResultItemViewModel[];
};

export type ResultShareApiErrorShape = {
  status: number | null;
  detail: string;
  body: unknown;
  kind: ShareTokenErrorKind;
};
