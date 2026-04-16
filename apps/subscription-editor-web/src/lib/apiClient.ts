import type {
  ApiValidationErrorRead,
  SubscriptionEditorApiErrorShape,
  SubscriptionEditorBootstrapRead,
  SubscriptionEditorSettingsPatchInput,
  SubscriptionSelfServiceEditorContractRead,
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
} from "./types";

export type SubscriptionEditorApiClientConfig = {
  apiBaseUrl: string;
  handoffToken: string;
  fetchImpl?: typeof fetch;
};

export class SubscriptionEditorApiError extends Error {
  readonly status: number | null;
  readonly fieldErrors;
  readonly body: unknown;

  constructor({ status, detail, fieldErrors, body }: SubscriptionEditorApiErrorShape) {
    super(detail);
    this.name = "SubscriptionEditorApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.body = body;
  }
}

export type SubscriptionEditorApiClient = ReturnType<
  typeof createSubscriptionEditorApiClient
>;

function normalizeApiBaseUrl(rawApiBaseUrl: string): string {
  const trimmed = rawApiBaseUrl.trim();
  if (!trimmed) {
    return window.location.origin;
  }
  return trimmed.replace(/\/+$/, "");
}

function buildEndpointUrl(apiBaseUrl: string, path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizeApiBaseUrl(apiBaseUrl)}${normalizedPath}`;
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  return text ? { detail: text } : null;
}

function toApiError(response: Response, body: unknown): SubscriptionEditorApiError {
  const maybeError = body as ApiValidationErrorRead | null;
  return new SubscriptionEditorApiError({
    status: response.status,
    detail:
      (maybeError && typeof maybeError.detail === "string" && maybeError.detail) ||
      `subscription editor request failed with status ${response.status}`,
    fieldErrors: Array.isArray(maybeError?.errors) ? maybeError.errors : [],
    body,
  });
}

export function createSubscriptionEditorApiClient(
  config: SubscriptionEditorApiClientConfig,
) {
  const fetchImpl = config.fetchImpl ?? fetch;

  async function request<T>(
    path: string,
    init?: RequestInit & { query?: Record<string, string> },
  ): Promise<T> {
    const url = new URL(buildEndpointUrl(config.apiBaseUrl, path));
    for (const [key, value] of Object.entries(init?.query ?? {})) {
      url.searchParams.set(key, value);
    }

    const response = await fetchImpl(url.toString(), {
      ...init,
      headers: {
        Authorization: `Bearer ${config.handoffToken}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });
    const body = await parseResponseBody(response);
    if (!response.ok) {
      throw toApiError(response, body);
    }
    return body as T;
  }

  return {
    getBootstrap: () =>
      request<SubscriptionEditorBootstrapRead>("/subscription-editor/bootstrap"),
    getContract: () =>
      request<SubscriptionSelfServiceEditorContractRead>("/subscription-editor/contract"),
    previewSettings: (payload: SubscriptionEditorSettingsPatchInput) =>
      request<SubscriptionSettingsPreviewRead>("/subscription-editor/settings/preview", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    saveSettings: (
      payload: SubscriptionEditorSettingsPatchInput,
      options: { includePreview: boolean },
    ) =>
      request<SubscriptionSettingsSaveResultRead>("/subscription-editor/settings", {
        method: "PATCH",
        query: options.includePreview ? { include_preview: "true" } : {},
        body: JSON.stringify(payload),
      }),
  };
}
