import type {
  AdminApiErrorKind,
  ConversionFilterInput,
  GroupWorkspaceAdminApiErrorShape,
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionDrilldownRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceMemberRead,
  GroupWorkspacePaperRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionDrilldownRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  PaperProfileRead,
  ResultShareAliasConversionDrilldownRead,
  ResultShareGrantIssueResponse,
  ResultShareGrantConversionDrilldownRead,
  ResultShareGrantRead,
  ResultShareGrantRevokeResponse,
  ResultShareGrantStatus,
  ResultShareKind,
  UserProfileRead,
  WorkspaceBoardShareCreateInput,
  WorkspaceCreateInput,
  WorkspaceMemberAddInput,
  WorkspacePaperAddInput,
  WorkspaceUpdateInput,
} from "./types";
import { buildConversionFilterQuery } from "./conversionFilters";

export type GroupWorkspaceAdminApiClientConfig = {
  apiBaseUrl: string;
  accessToken: string;
  fetchImpl?: typeof fetch;
};

export class GroupWorkspaceAdminApiError extends Error {
  readonly status: number | null;
  readonly detail: string;
  readonly body: unknown;
  readonly kind: AdminApiErrorKind;

  constructor(shape: GroupWorkspaceAdminApiErrorShape) {
    super(shape.detail);
    this.name = "GroupWorkspaceAdminApiError";
    this.status = shape.status;
    this.detail = shape.detail;
    this.body = shape.body;
    this.kind = shape.kind;
  }
}

export type GroupWorkspaceAdminApiClient = ReturnType<typeof createGroupWorkspaceAdminApiClient>;

type RequestMethod = "GET" | "POST" | "PATCH" | "DELETE";

function buildEndpointUrl(apiBaseUrl: string, path: string, query?: URLSearchParams): string {
  const base = `${apiBaseUrl.replace(/\/+$/, "")}${path}`;
  const queryString = query?.toString();
  return queryString ? `${base}?${queryString}` : base;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

function inferErrorKind(status: number | null, detail: string): AdminApiErrorKind {
  const normalized = detail.toLowerCase();
  if (status === null) {
    return "network_error";
  }
  if (status === 401) {
    return "unauthorized";
  }
  if (status === 403) {
    return "forbidden";
  }
  if (status === 404 || normalized.includes("not found")) {
    return "not_found";
  }
  if (status === 409 || normalized.includes("already")) {
    return "conflict";
  }
  return "request_failed";
}

function toApiError(response: Response, body: unknown): GroupWorkspaceAdminApiError {
  const detail =
    body && typeof body === "object" && "detail" in body && typeof body.detail === "string"
      ? body.detail
      : `group workspace admin request failed with status ${response.status}`;
  return new GroupWorkspaceAdminApiError({
    status: response.status,
    detail,
    body,
    kind: inferErrorKind(response.status, detail),
  });
}

export function createGroupWorkspaceAdminApiClient(
  config: GroupWorkspaceAdminApiClientConfig,
) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>({
    method,
    path,
    query,
    body,
  }: {
    method: RequestMethod;
    path: string;
    query?: URLSearchParams;
    body?: unknown;
  }): Promise<T> {
    const url = buildEndpointUrl(config.apiBaseUrl, path, query);
    const headers: HeadersInit = {
      Authorization: `Bearer ${config.accessToken}`,
      "X-Request-ID": crypto.randomUUID(),
    };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetchImpl(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const responseBody = await parseResponseBody(response);
      if (!response.ok) {
        throw toApiError(response, responseBody);
      }
      return responseBody as T;
    } catch (error) {
      if (error instanceof GroupWorkspaceAdminApiError) {
        throw error;
      }
      const detail = error instanceof Error ? error.message : "network request failed";
      throw new GroupWorkspaceAdminApiError({
        status: null,
        detail,
        body: null,
        kind: inferErrorKind(null, detail),
      });
    }
  }

  return {
    listWorkspaces: () =>
      request<GroupWorkspaceRead[]>({ method: "GET", path: "/admin/group-workspaces" }),
    createWorkspace: (payload: WorkspaceCreateInput) =>
      request<GroupWorkspaceRead>({
        method: "POST",
        path: "/admin/group-workspaces",
        body: payload,
      }),
    getWorkspace: (workspaceId: string) =>
      request<GroupWorkspaceRead>({
        method: "GET",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}`,
      }),
    updateWorkspace: (workspaceId: string, payload: Partial<WorkspaceUpdateInput>) =>
      request<GroupWorkspaceRead>({
        method: "PATCH",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}`,
        body: payload,
      }),
    getWorkspaceBoard: (workspaceId: string) =>
      request<GroupWorkspaceBoardRead>({
        method: "GET",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/board`,
      }),
    getConversionOverview: (filters?: Partial<ConversionFilterInput>) =>
      request<GroupWorkspaceConversionOverviewRead>({
        method: "GET",
        path: "/admin/group-workspace-conversion-overview",
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
              includeLimit: false,
            })
          : undefined,
      }),
    getConversionDrilldown: (filters?: Partial<ConversionFilterInput>) =>
      request<GroupWorkspaceConversionDrilldownRead>({
        method: "GET",
        path: "/admin/group-workspace-conversion-drilldown",
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
              includeLimit: true,
            })
          : undefined,
      }),
    getWorkspaceConversionOverview: (
      workspaceId: string,
      filters?: Partial<ConversionFilterInput>,
    ) =>
      request<GroupWorkspaceWorkspaceConversionOverviewRead>({
        method: "GET",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/conversion-overview`,
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
              includeLimit: false,
            })
          : undefined,
      }),
    getWorkspaceConversionDrilldown: (
      workspaceId: string,
      filters?: Partial<ConversionFilterInput>,
    ) =>
      request<GroupWorkspaceWorkspaceConversionDrilldownRead>({
        method: "GET",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/conversion-drilldown`,
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
            includeLimit: true,
          })
          : undefined,
      }),
    getResultShareGrantConversionDrilldown: (
      grantId: string,
      filters?: Partial<ConversionFilterInput>,
    ) =>
      request<ResultShareGrantConversionDrilldownRead>({
        method: "GET",
        path: `/admin/result-share-grants/${encodeURIComponent(grantId)}/conversion-drilldown`,
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
              includeLimit: true,
            })
          : undefined,
      }),
    getResultShareAliasConversionDrilldown: (
      aliasId: string,
      filters?: Partial<ConversionFilterInput>,
    ) =>
      request<ResultShareAliasConversionDrilldownRead>({
        method: "GET",
        path: `/admin/result-share-aliases/${encodeURIComponent(aliasId)}/conversion-drilldown`,
        query: filters
          ? buildConversionFilterQuery(filters, {
              includeDimensions: true,
              includeOutcome: true,
              includeLimit: true,
            })
          : undefined,
      }),
    addWorkspaceMember: (workspaceId: string, payload: WorkspaceMemberAddInput) =>
      request<GroupWorkspaceMemberRead>({
        method: "POST",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/members`,
        body: payload,
      }),
    removeWorkspaceMember: (workspaceId: string, memberId: string) =>
      request<void>({
        method: "DELETE",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/members/${encodeURIComponent(memberId)}`,
      }),
    addWorkspacePaper: (workspaceId: string, payload: WorkspacePaperAddInput) =>
      request<GroupWorkspacePaperRead>({
        method: "POST",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/papers`,
        body: payload,
      }),
    removeWorkspacePaper: (workspaceId: string, paperId: string) =>
      request<void>({
        method: "DELETE",
        path: `/admin/group-workspaces/${encodeURIComponent(workspaceId)}/papers/${encodeURIComponent(paperId)}`,
      }),
    listResultShareGrants: (params: {
      workspaceId?: string;
      userId?: string;
      shareKind?: ResultShareKind;
      status?: ResultShareGrantStatus;
    }) => {
      const query = new URLSearchParams();
      if (params.workspaceId) {
        query.set("workspace_id", params.workspaceId);
      }
      if (params.userId) {
        query.set("user_id", params.userId);
      }
      if (params.shareKind) {
        query.set("share_kind", params.shareKind);
      }
      if (params.status) {
        query.set("status", params.status);
      }
      return request<ResultShareGrantRead[]>({
        method: "GET",
        path: "/admin/result-share-grants",
        query,
      });
    },
    createWorkspaceBoardShareGrant: (
      workspaceId: string,
      payload: WorkspaceBoardShareCreateInput,
    ) =>
      request<ResultShareGrantIssueResponse>({
        method: "POST",
        path: "/admin/result-share-grants",
        body: {
          share_kind: "workspace_board",
          workspace_id: workspaceId,
          display_label: payload.display_label || null,
          expires_at: payload.expires_at,
        },
      }),
    revokeResultShareGrant: (grantId: string) =>
      request<ResultShareGrantRevokeResponse>({
        method: "POST",
        path: `/admin/result-share-grants/${encodeURIComponent(grantId)}/revoke`,
      }),
    listUsers: () => request<UserProfileRead[]>({ method: "GET", path: "/users" }),
    listPapers: (userId?: string) => {
      const query = new URLSearchParams();
      if (userId) {
        query.set("user_id", userId);
      }
      return request<PaperProfileRead[]>({
        method: "GET",
        path: "/papers",
        query,
      });
    },
  };
}
