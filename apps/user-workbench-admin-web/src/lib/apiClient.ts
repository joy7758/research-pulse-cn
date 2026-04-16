import type {
  AdminApiErrorKind,
  GroupWorkspaceAdminApiErrorShape,
  UserWorkbenchPaperDetailRead,
  UserWorkbenchPaperSummaryRead,
  UserWorkbenchPapersQuery,
  UserWorkbenchUserDetailRead,
  UserWorkbenchUserSummaryRead,
  UserWorkbenchUsersQuery,
  UserWorkbenchWatchProfileRead,
  UserWorkbenchWatchProfilesQuery,
} from "./types";

export type UserWorkbenchAdminApiClientConfig = {
  apiBaseUrl: string;
  accessToken: string;
  fetchImpl?: typeof fetch;
};

export class UserWorkbenchAdminApiError extends Error {
  readonly status: number | null;
  readonly detail: string;
  readonly body: unknown;
  readonly kind: AdminApiErrorKind;

  constructor(shape: GroupWorkspaceAdminApiErrorShape) {
    super(shape.detail);
    this.name = "UserWorkbenchAdminApiError";
    this.status = shape.status;
    this.detail = shape.detail;
    this.body = shape.body;
    this.kind = shape.kind;
  }
}

export type UserWorkbenchAdminApiClient = ReturnType<typeof createUserWorkbenchAdminApiClient>;

type RequestMethod = "GET";

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

function toApiError(response: Response, body: unknown): UserWorkbenchAdminApiError {
  const detail =
    body && typeof body === "object" && "detail" in body && typeof body.detail === "string"
      ? body.detail
      : `user workbench admin request failed with status ${response.status}`;
  return new UserWorkbenchAdminApiError({
    status: response.status,
    detail,
    body,
    kind: inferErrorKind(response.status, detail),
  });
}

export function createUserWorkbenchAdminApiClient(config: UserWorkbenchAdminApiClientConfig) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>({
    method,
    path,
    query,
  }: {
    method: RequestMethod;
    path: string;
    query?: URLSearchParams;
  }): Promise<T> {
    const url = buildEndpointUrl(config.apiBaseUrl, path, query);
    const headers: HeadersInit = {
      Authorization: `Bearer ${config.accessToken}`,
      "X-Request-ID": crypto.randomUUID(),
    };

    try {
      const response = await fetchImpl(url, {
        method,
        headers,
      });
      const responseBody = await parseResponseBody(response);
      if (!response.ok) {
        throw toApiError(response, responseBody);
      }
      return responseBody as T;
    } catch (error) {
      if (error instanceof UserWorkbenchAdminApiError) {
        throw error;
      }
      const detail = error instanceof Error ? error.message : "network request failed";
      throw new UserWorkbenchAdminApiError({
        status: null,
        detail,
        body: null,
        kind: inferErrorKind(null, detail),
      });
    }
  }

  return {
    listUsers: (params: UserWorkbenchUsersQuery) => {
      const query = new URLSearchParams();
      if (params.q) {
        query.set("q", params.q);
      }
      if (params.limit !== undefined) {
        query.set("limit", String(params.limit));
      }
      return request<UserWorkbenchUserSummaryRead[]>({
        method: "GET",
        path: "/admin/user-workbench/users",
        query,
      });
    },
    getUserDetail: (userId: string) =>
      request<UserWorkbenchUserDetailRead>({
        method: "GET",
        path: `/admin/user-workbench/users/${encodeURIComponent(userId)}`,
      }),
    listPapers: (params: UserWorkbenchPapersQuery) => {
      const query = new URLSearchParams();
      if (params.q) {
        query.set("q", params.q);
      }
      if (params.userId) {
        query.set("user_id", params.userId);
      }
      if (params.stage) {
        query.set("stage", params.stage);
      }
      if (params.type) {
        query.set("type", params.type);
      }
      if (params.limit !== undefined) {
        query.set("limit", String(params.limit));
      }
      return request<UserWorkbenchPaperSummaryRead[]>({
        method: "GET",
        path: "/admin/user-workbench/papers",
        query,
      });
    },
    getPaperDetail: (paperId: string) =>
      request<UserWorkbenchPaperDetailRead>({
        method: "GET",
        path: `/admin/user-workbench/papers/${encodeURIComponent(paperId)}`,
      }),
    listWatchProfiles: (params: UserWorkbenchWatchProfilesQuery) => {
      const query = new URLSearchParams();
      if (params.userId) {
        query.set("user_id", params.userId);
      }
      if (params.paperId) {
        query.set("paper_id", params.paperId);
      }
      if (params.enabled !== undefined) {
        query.set("enabled", String(params.enabled));
      }
      if (params.q) {
        query.set("q", params.q);
      }
      return request<UserWorkbenchWatchProfileRead[]>({
        method: "GET",
        path: "/admin/user-workbench/watch-profiles",
        query,
      });
    },
  };
}
