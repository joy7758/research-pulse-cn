import type {
  GroupWorkspaceResultCollectionRead,
  ResultShareCollectPreviewRead,
  ResultShareCollectResponseRead,
  ResultShareApiErrorShape,
  SharedResultContentRead,
  ShareGrantBootstrapRead,
  ShareTokenErrorKind,
} from "./types";

export type ResultShareApiClientConfig = {
  apiBaseUrl: string;
  fetchImpl?: typeof fetch;
};

export class ResultShareApiError extends Error {
  readonly status: number | null;
  readonly detail: string;
  readonly body: unknown;
  readonly kind: ShareTokenErrorKind;

  constructor(shape: ResultShareApiErrorShape) {
    super(shape.detail);
    this.name = "ResultShareApiError";
    this.status = shape.status;
    this.detail = shape.detail;
    this.body = shape.body;
    this.kind = shape.kind;
  }
}

export type ResultShareApiClient = ReturnType<typeof createResultShareApiClient>;

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
  if (body && typeof body === "object" && "detail" in body) {
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
  return `result share request failed with status ${fallbackStatus}`;
}

function inferErrorKind(status: number | null, detail: string): ShareTokenErrorKind {
  const normalized = detail.toLowerCase();
  if (status === null) {
    return "network_error";
  }
  if (normalized.includes("revoked")) {
    return "revoked_token";
  }
  if (normalized.includes("expired")) {
    return "expired_token";
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
    return "invalid_token";
  }
  return "request_failed";
}

function toApiError(response: Response, body: unknown): ResultShareApiError {
  const detail = normalizeDetail(body, response.status);
  return new ResultShareApiError({
    status: response.status,
    detail,
    body,
    kind: inferErrorKind(response.status, detail),
  });
}

export function createResultShareApiClient(config: ResultShareApiClientConfig) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>({
    path,
    method = "GET",
    selfServiceToken,
    jsonBody,
  }: {
    path: string;
    method?: "GET" | "POST";
    selfServiceToken?: string;
    jsonBody?: unknown;
  }): Promise<T> {
    const url = buildEndpointUrl(config.apiBaseUrl, path);
    const headers = new Headers();
    if (selfServiceToken) {
      headers.set("Authorization", `Bearer ${selfServiceToken}`);
    }
    if (jsonBody !== undefined) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetchImpl(url, {
        method,
        headers,
        body: jsonBody === undefined ? undefined : JSON.stringify(jsonBody),
      });
      const body = await parseResponseBody(response);
      if (!response.ok) {
        throw toApiError(response, body);
      }
      return body as T;
    } catch (error) {
      if (error instanceof ResultShareApiError) {
        throw error;
      }
      const detail =
        error instanceof Error ? error.message : "network request failed";
      throw new ResultShareApiError({
        status: null,
        detail,
        body: null,
        kind: inferErrorKind(null, detail),
      });
    }
  }

  return {
    getShareBootstrap: (shareToken: string) =>
      request<ShareGrantBootstrapRead>({
        path: `/result-shares/${encodeURIComponent(shareToken)}/bootstrap`,
      }),
    getShareContent: (shareToken: string) =>
      request<SharedResultContentRead>({
        path: `/result-shares/${encodeURIComponent(shareToken)}/content`,
      }),
    getCollectPreview: (shareToken: string, selfServiceToken: string) =>
      request<ResultShareCollectPreviewRead>({
        path: `/subscription-self-service/result-shares/${encodeURIComponent(shareToken)}/collect-preview`,
        selfServiceToken,
      }),
    postCollect: (
      shareToken: string,
      selfServiceToken: string,
      payload: { workspace_id: string; paper_ids?: string[] },
    ) =>
      request<ResultShareCollectResponseRead>({
        path: `/subscription-self-service/result-shares/${encodeURIComponent(shareToken)}/collect`,
        method: "POST",
        selfServiceToken,
        jsonBody: payload,
      }),
    listWorkspaceResultCollections: (selfServiceToken: string) =>
      request<GroupWorkspaceResultCollectionRead[]>({
        path: "/subscription-self-service/workspace-result-collections",
        selfServiceToken,
      }),
  };
}
