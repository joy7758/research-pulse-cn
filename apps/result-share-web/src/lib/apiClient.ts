import type {
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
  if (status === 401 || status === 404 || normalized.includes("not found")) {
    return "invalid_token";
  }
  return "request_failed";
}

function toApiError(response: Response, body: unknown): ResultShareApiError {
  const detail =
    body && typeof body === "object" && "detail" in body && typeof body.detail === "string"
      ? body.detail
      : `result share request failed with status ${response.status}`;
  return new ResultShareApiError({
    status: response.status,
    detail,
    body,
    kind: inferErrorKind(response.status, detail),
  });
}

export function createResultShareApiClient(config: ResultShareApiClientConfig) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>(shareToken: string, suffix: "/bootstrap" | "/content"): Promise<T> {
    const url = buildEndpointUrl(
      config.apiBaseUrl,
      `/result-shares/${encodeURIComponent(shareToken)}/${suffix.slice(1)}`,
    );

    try {
      const response = await fetchImpl(url);
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
      request<ShareGrantBootstrapRead>(shareToken, "/bootstrap"),
    getShareContent: (shareToken: string) =>
      request<SharedResultContentRead>(shareToken, "/content"),
  };
}
