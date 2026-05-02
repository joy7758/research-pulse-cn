import type {
  EditorHostRuntimeMetadataRead,
  MiniEditorLaunchInputRead,
  SubscriptionEditorSupportedRuntimeRead,
} from "./types";

export function buildRuntimeMetadataFromLaunchInput(
  launchInput: MiniEditorLaunchInputRead,
  options?: { notes?: string[] },
): EditorHostRuntimeMetadataRead {
  return {
    runtime_kind: launchInput.runtime_kind,
    api_base_url: launchInput.api_base_url,
    token_delivery_kind: launchInput.token_delivery_kind,
    editor_entry_mode: "handoff_token",
    notes: options?.notes ?? [],
  };
}

export function buildSupportedRuntimeRead(
  options?: Partial<SubscriptionEditorSupportedRuntimeRead>,
): SubscriptionEditorSupportedRuntimeRead {
  return {
    default_runtime: options?.default_runtime ?? "web_shell",
    supported_runtimes:
      options?.supported_runtimes ?? ["web_shell", "mini_webview_reserve"],
    token_delivery_kinds:
      options?.token_delivery_kinds ?? [
        "manual_entry",
        "url_fragment",
        "host_injected",
      ],
    notes: options?.notes ?? [],
  };
}
