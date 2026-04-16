export type AdminTokenSource = "query" | "fragment" | "manual" | "none";

export type AdminApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "network_error"
  | "request_failed";

export type UserWorkbenchUserSummaryRead = {
  id: string;
  name: string;
  email: string | null;
  field: string | null;
  paper_count: number;
  watch_profile_count: number;
  workspace_count: number;
  latest_digest_issue_summary: UserWorkbenchLatestDigestIssueSummaryRead | null;
};

export type UserWorkbenchLatestDigestIssueSummaryRead = {
  id: string;
  user_id: string;
  issue_date: string;
  status: string;
  title: string;
  summary: string;
  selected_card_count: number;
  published_at: string | null;
  deep_link_path: string | null;
};

export type UserWorkbenchPaperSignalSummaryRead = {
  source: string;
  citation_count: number | null;
  download_count: number | null;
  read_count: number | null;
  inclusion_status: string | null;
  fetched_at: string;
};

export type UserWorkbenchLinkedWatchProfileSummaryRead = {
  id: string;
  label: string;
  enabled: boolean;
  source_mode: string;
};

export type UserWorkbenchPaperSummaryRead = {
  id: string;
  user_id: string;
  user_name: string | null;
  user_email: string | null;
  title: string;
  type: string;
  stage: string;
  venue: string | null;
  priority: number;
  next_action: string | null;
  blocker: string | null;
  last_touch_at: string | null;
  progress_percentage: number;
  latest_signal_summary: UserWorkbenchPaperSignalSummaryRead | null;
  linked_watch_profiles: UserWorkbenchLinkedWatchProfileSummaryRead[];
};

export type UserWorkbenchWorkspaceMembershipRead = {
  workspace_id: string;
  slug: string;
  name: string;
  status: string;
  role: string;
  joined_at: string;
};

export type UserWorkbenchWatchProfileRead = {
  id: string;
  user_id: string;
  paper_id: string | null;
  label: string;
  enabled: boolean;
  source_mode: string;
  topics: string[];
  keywords: string[];
  venues: string[];
  authors_of_interest: string[] | null;
  user_name: string | null;
  user_email: string | null;
  paper_title: string | null;
  created_at: string;
  updated_at: string;
};

export type UserWorkbenchUserDetailRead = {
  user: UserWorkbenchUserSummaryRead;
  papers: UserWorkbenchPaperSummaryRead[];
  watch_profiles: UserWorkbenchWatchProfileRead[];
  workspace_memberships: UserWorkbenchWorkspaceMembershipRead[];
};

export type UserWorkbenchPaperOwnerRead = {
  id: string;
  name: string;
  email: string | null;
  field: string | null;
};

export type UserWorkbenchPaperDetailRead = {
  paper: UserWorkbenchPaperSummaryRead;
  owner: UserWorkbenchPaperOwnerRead;
  linked_watch_profiles: UserWorkbenchWatchProfileRead[];
};

export type UserWorkbenchUsersQuery = {
  q?: string;
  limit?: number;
};

export type UserWorkbenchPapersQuery = {
  q?: string;
  userId?: string;
  stage?: string;
  type?: string;
  limit?: number;
};

export type UserWorkbenchWatchProfilesQuery = {
  userId?: string;
  paperId?: string;
  enabled?: boolean;
  q?: string;
};

export type GroupWorkspaceLinkSummary = {
  workspaceId: string;
  label: string;
  role: string;
  status: string;
};

export type UserWorkbenchUserCardViewModel = {
  id: string;
  title: string;
  subtitle: string | null;
  paperCount: number;
  watchProfileCount: number;
  workspaceCount: number;
  latestDigestTitle: string | null;
};

export type UserWorkbenchPaperCardViewModel = {
  id: string;
  title: string;
  subtitle: string;
  ownerLabel: string | null;
  progressPercentage: number;
  linkedWatchProfileCount: number;
};

export type UserWorkbenchWatchProfileCardViewModel = {
  id: string;
  userId: string;
  paperId: string | null;
  title: string;
  subtitle: string | null;
  enabled: boolean;
  userLabel: string | null;
  paperLabel: string | null;
};

export type ApiErrorViewModel = {
  kind: AdminApiErrorKind;
  title: string;
  message: string;
};

export type GroupWorkspaceAdminApiErrorShape = {
  status: number | null;
  detail: string;
  body: unknown;
  kind: AdminApiErrorKind;
};
