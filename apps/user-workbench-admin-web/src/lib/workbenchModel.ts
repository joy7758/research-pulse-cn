import type {
  ApiErrorViewModel,
  GroupWorkspaceAdminApiErrorShape,
  UserWorkbenchPaperCardViewModel,
  UserWorkbenchPaperDetailRead,
  UserWorkbenchUserCardViewModel,
  UserWorkbenchUserDetailRead,
  UserWorkbenchUserSummaryRead,
  UserWorkbenchWatchProfileCardViewModel,
  UserWorkbenchWatchProfileRead,
} from "./types";

export function buildUserCardViewModels(
  users: UserWorkbenchUserSummaryRead[],
): UserWorkbenchUserCardViewModel[] {
  return users.map((user) => ({
    id: user.id,
    title: user.name,
    subtitle: user.email ?? user.field,
    paperCount: user.paper_count,
    watchProfileCount: user.watch_profile_count,
    workspaceCount: user.workspace_count,
    latestDigestTitle: user.latest_digest_issue_summary?.title ?? null,
  }));
}

export function buildUserDetailViewModel(detail: UserWorkbenchUserDetailRead) {
  return {
    title: detail.user.name,
    subtitle: detail.user.email ?? detail.user.field,
    latestDigestTitle: detail.user.latest_digest_issue_summary?.title ?? null,
    workspaceLabels: detail.workspace_memberships.map(
      (membership) => `${membership.name} (${membership.role})`,
    ),
    paperTitles: detail.papers.map((paper) => paper.title),
    watchLabels: detail.watch_profiles.map((profile) => profile.label),
  };
}

export function buildPaperCardViewModels(
  papers: UserWorkbenchPaperDetailRead["paper"][],
): UserWorkbenchPaperCardViewModel[] {
  return papers.map((paper) => ({
    id: paper.id,
    title: paper.title,
    subtitle: [paper.stage, paper.venue].filter(Boolean).join(" · ") || paper.type,
    ownerLabel: paper.user_name ?? paper.user_email,
    progressPercentage: paper.progress_percentage,
    linkedWatchProfileCount: paper.linked_watch_profiles.length,
  }));
}

export function buildPaperDetailViewModel(detail: UserWorkbenchPaperDetailRead) {
  return {
    title: detail.paper.title,
    subtitle: [detail.paper.stage, detail.paper.venue].filter(Boolean).join(" · ") || detail.paper.type,
    ownerLabel: detail.owner.email ? `${detail.owner.name} (${detail.owner.email})` : detail.owner.name,
    linkedWatchLabels: detail.linked_watch_profiles.map((profile) => profile.label),
  };
}

export function buildWatchProfileCardViewModels(
  profiles: UserWorkbenchWatchProfileRead[],
): UserWorkbenchWatchProfileCardViewModel[] {
  return profiles.map((profile) => ({
    id: profile.id,
    userId: profile.user_id,
    paperId: profile.paper_id,
    title: profile.label,
    subtitle: profile.source_mode,
    enabled: profile.enabled,
    userLabel: profile.user_email ? `${profile.user_name} (${profile.user_email})` : profile.user_name,
    paperLabel: profile.paper_title,
  }));
}

export function buildApiErrorViewModel(
  shape: Pick<GroupWorkspaceAdminApiErrorShape, "kind" | "detail">,
): ApiErrorViewModel {
  switch (shape.kind) {
    case "unauthorized":
      return {
        kind: shape.kind,
        title: "Unauthorized admin token",
        message: "Paste a valid admin/operator bearer token and try again.",
      };
    case "forbidden":
      return {
        kind: shape.kind,
        title: "Forbidden action",
        message: "This token cannot access the read-only user workbench.",
      };
    case "not_found":
      return {
        kind: shape.kind,
        title: "Resource not found",
        message: shape.detail,
      };
    case "conflict":
      return {
        kind: shape.kind,
        title: "Conflict",
        message: shape.detail,
      };
    case "network_error":
      return {
        kind: shape.kind,
        title: "Network failure",
        message: "The workbench could not reach the API.",
      };
    default:
      return {
        kind: shape.kind,
        title: "Request failed",
        message: shape.detail,
      };
  }
}
