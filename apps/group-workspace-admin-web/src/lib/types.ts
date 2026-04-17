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
