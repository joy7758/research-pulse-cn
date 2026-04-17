import type {
  GroupWorkspaceInviteApiErrorShape,
  GroupWorkspaceInviteBootstrapRead,
  GroupWorkspaceInviteClaimPreviewRead,
  GroupWorkspaceInviteClaimResponse,
  GroupWorkspaceMembershipRead,
  InviteApiErrorKind,
} from "./types";

export type GroupWorkspaceInviteApiClientConfig = {
  apiBaseUrl: string;
  fetchImpl?: typeof fetch;
};

export class GroupWorkspaceInviteApiError extends Error {
  readonly status: number | null;
  readonly detail: string;
  readonly body: unknown;
  readonly kind: InviteApiErrorKind;

  constructor(shape: GroupWorkspaceInviteApiErrorShape) {
    super(shape.detail);
    this.name = "GroupWorkspaceInviteApiError";
    this.status = shape.status;
    this.detail = shape.detail;
    this.body = shape.body;
    this.kind = shape.kind;
  }
}

export type GroupWorkspaceInviteApiClient = ReturnType<
  typeof createGroupWorkspaceInviteApiClient
>;

function buildEndpointUrl(apiBaseUrl: string, path: string): string {
  return `${apiBaseUrl.replace(/\/+$/, "")}${path}`;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

function normalizeDetail(body: unknown, fallbackStatus: number): string {
  if (body && typeof body === "object") {
    if ("detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") {
        return detail;
      }
      if (Array.isArray(detail)) {
        return detail
          .map((entry) => (typeof entry === "string" ? entry : JSON.stringify(entry)))
          .join("; ");
      }
    }
  }
  return `workspace invite request failed with status ${fallbackStatus}`;
}

function inferErrorKind(status: number | null, detail: string): InviteApiErrorKind {
  const normalized = detail.toLowerCase();
  if (status === null) {
    return "network_error";
  }
  if (normalized.includes("revoked")) {
    return "revoked_invite";
  }
  if (normalized.includes("expired")) {
    return "expired_invite";
  }
  if (normalized.includes("exhausted")) {
    return "invite_exhausted";
  }
  if (
    status === 401 &&
    (normalized.includes("credentials")
      || normalized.includes("bearer")
      || normalized.includes("not authenticated"))
  ) {
    return "unauthorized_self_service";
  }
  if (status === 401 || status === 404 || normalized.includes("not found")) {
    return "invalid_invite";
  }
  return "request_failed";
}

function toApiError(response: Response, body: unknown): GroupWorkspaceInviteApiError {
  const detail = normalizeDetail(body, response.status);
  return new GroupWorkspaceInviteApiError({
    status: response.status,
    detail,
    body,
    kind: inferErrorKind(response.status, detail),
  });
}

export function createGroupWorkspaceInviteApiClient(
  config: GroupWorkspaceInviteApiClientConfig,
) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>({
    path,
    method = "GET",
    selfServiceToken,
  }: {
    path: string;
    method?: "GET" | "POST";
    selfServiceToken?: string;
  }): Promise<T> {
    const url = buildEndpointUrl(config.apiBaseUrl, path);
    const headers = new Headers();
    if (selfServiceToken) {
      headers.set("Authorization", `Bearer ${selfServiceToken}`);
    }

    try {
      const response = await fetchImpl(url, {
        method,
        headers,
      });
      const body = await parseResponseBody(response);
      if (!response.ok) {
        throw toApiError(response, body);
      }
      return body as T;
    } catch (error) {
      if (error instanceof GroupWorkspaceInviteApiError) {
        throw error;
      }
      const detail =
        error instanceof Error ? error.message : "network request failed";
      throw new GroupWorkspaceInviteApiError({
        status: null,
        detail,
        body: null,
        kind: inferErrorKind(null, detail),
      });
    }
  }

  return {
    getInviteBootstrap: (inviteToken: string) =>
      request<GroupWorkspaceInviteBootstrapRead>({
        path: `/workspace-invites/${encodeURIComponent(inviteToken)}/bootstrap`,
      }),
    getClaimPreview: (inviteToken: string, selfServiceToken: string) =>
      request<GroupWorkspaceInviteClaimPreviewRead>({
        path: `/subscription-self-service/workspace-invites/${encodeURIComponent(inviteToken)}/claim-preview`,
        selfServiceToken,
      }),
    claimInvite: (inviteToken: string, selfServiceToken: string) =>
      request<GroupWorkspaceInviteClaimResponse>({
        path: `/subscription-self-service/workspace-invites/${encodeURIComponent(inviteToken)}/claim`,
        method: "POST",
        selfServiceToken,
      }),
    getWorkspaceMemberships: (selfServiceToken: string) =>
      request<GroupWorkspaceMembershipRead[]>({
        path: "/subscription-self-service/workspace-memberships",
        selfServiceToken,
      }),
  };
}
