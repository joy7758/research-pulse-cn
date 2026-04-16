export type ResultShareKind = "digest_issue" | "paper_snapshot" | "workspace_board" | string;
export type ResultShareGrantStatus = "active" | "revoked" | "expired" | string;
export type DigestFallbackMode = "structured" | "highlights_only" | "empty" | string;
export type SharedTodaySectionKind =
  | "today_focus"
  | "yesterday_recap"
  | "signal_updates"
  | "related_papers"
  | "other_updates"
  | string;

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

export type ShareGrantBootstrapRead = {
  grant: ShareGrantPublicSummaryRead;
  target: ShareGrantTargetSummaryRead;
  notes: string[];
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
};

export type ResultShareViewModel =
  | DigestShareViewModel
  | PaperSnapshotViewModel
  | WorkspaceBoardViewModel;

export type ShareTokenErrorKind =
  | "invalid_token"
  | "revoked_token"
  | "expired_token"
  | "network_error"
  | "request_failed";

export type ShareErrorViewModel = {
  kind: ShareTokenErrorKind;
  title: string;
  message: string;
};

export type ResultShareApiErrorShape = {
  status: number | null;
  detail: string;
  body: unknown;
  kind: ShareTokenErrorKind;
};
