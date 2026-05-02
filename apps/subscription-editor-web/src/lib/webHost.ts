import {
  buildRuntimeMetadataFromLaunchInput,
  type SubscriptionEditorHostAdapter,
} from "@research-pulse/subscription-editor-core";

import {
  clearHandoffTokenFromVisibleUrl,
  extractHandoffTokenFromFragment,
} from "./token";

export const DEFAULT_SUBSCRIPTION_EDITOR_API_BASE_URL =
  import.meta.env.VITE_SUBSCRIPTION_EDITOR_API_BASE_URL?.trim() ||
  "http://127.0.0.1:8000";

export type WebShellHostAdapterOptions = {
  initialApiBaseUrl?: string;
  initialHash?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  defaultApiBaseUrl?: string;
};

export function createWebShellHostAdapter(
  options: WebShellHostAdapterOptions,
): SubscriptionEditorHostAdapter {
  const defaultApiBaseUrl =
    options.defaultApiBaseUrl ?? DEFAULT_SUBSCRIPTION_EDITOR_API_BASE_URL;
  const resolvedLocation =
    options.locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    options.historyLike ?? (typeof window === "undefined" ? undefined : window.history);

  const currentFragment = options.initialHash ?? resolvedLocation?.hash ?? "";
  const extracted = extractHandoffTokenFromFragment(currentFragment);
  const apiBaseUrl = options.initialApiBaseUrl?.trim() || defaultApiBaseUrl;

  return {
    runtimeKind: "web_shell",
    getInitialTokenInput: () => extracted.handoffToken,
    clearVisibleTokenHint: () => {
      if (!resolvedLocation || !resolvedHistory || options.initialHash) {
        return;
      }
      clearHandoffTokenFromVisibleUrl(resolvedLocation, resolvedHistory);
    },
    getApiBaseUrl: () => apiBaseUrl,
    getRuntimeMetadata: () =>
      buildRuntimeMetadataFromLaunchInput(
        {
          runtime_kind: "web_shell",
          api_base_url: apiBaseUrl,
          handoff_token: null,
          token_delivery_kind: extracted.handoffToken ? "url_fragment" : "manual_entry",
        },
        {
          notes: [
            "Web shell is the reference host for the shared subscription editor core.",
          ],
        },
      ),
  };
}
