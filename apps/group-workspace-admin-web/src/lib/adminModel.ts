import type {
  ApiErrorViewModel,
  GroupWorkspaceAdminApiErrorShape,
  GroupWorkspaceBoardRead,
  GroupWorkspaceRead,
  LookupOption,
  PaperProfileRead,
  ResultShareGrantIssueResponse,
  UserProfileRead,
  WorkspaceListItemViewModel,
  WorkspaceBoardViewModel,
  ShareGrantOneTimeDisplayModel,
} from "./types";

export function buildWorkspaceListItems(
  workspaces: GroupWorkspaceRead[],
  boardCache: Record<string, GroupWorkspaceBoardRead | undefined>,
): WorkspaceListItemViewModel[] {
  return workspaces.map((workspace) => {
    const cachedBoard = boardCache[workspace.id];
    return {
      id: workspace.id,
      slug: workspace.slug,
      name: workspace.name,
      description: workspace.description,
      status: workspace.status,
      memberCount: cachedBoard?.member_count ?? null,
      paperCount: cachedBoard?.paper_count ?? null,
    };
  });
}

export function buildWorkspaceBoardViewModel(board: GroupWorkspaceBoardRead): WorkspaceBoardViewModel {
  return {
    workspaceId: board.workspace.id,
    title: board.workspace.name,
    description: board.workspace.description,
    status: board.workspace.status,
    memberCount: board.member_count,
    paperCount: board.paper_count,
    blockedPaperCount: board.quick_stats.blocked_paper_count,
    papersWithSignalsCount: board.quick_stats.papers_with_signals_count,
    members: board.members,
    papers: board.papers,
  };
}

export function buildUserLookupOptions(users: UserProfileRead[]): LookupOption[] {
  return users.map((user) => ({
    id: user.id,
    label: user.email ? `${user.name} (${user.email})` : user.name,
    hint: user.field,
  }));
}

export function buildPaperLookupOptions(papers: PaperProfileRead[]): LookupOption[] {
  return papers.map((paper) => ({
    id: paper.id,
    label: paper.title,
    hint: [paper.stage, paper.venue].filter(Boolean).join(" · ") || null,
  }));
}

export function buildShareGrantIssueViewModel(
  response: ResultShareGrantIssueResponse,
): ShareGrantOneTimeDisplayModel {
  return {
    grantId: response.grant.id,
    shareKind: response.grant.share_kind,
    displayLabel: response.grant.display_label,
    plainTextToken: response.plain_text_token,
    expiresAt: response.expires_at,
    copyHint: "Copy this token now. It is only returned once at creation time.",
  };
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
        message: "This token can read some data but cannot perform this admin action.",
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
        message: "The admin shell could not reach the API.",
      };
    default:
      return {
        kind: shape.kind,
        title: "Request failed",
        message: shape.detail,
      };
  }
}
