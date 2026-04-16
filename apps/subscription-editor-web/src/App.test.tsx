import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type {
  SubscriptionEditorBootstrapRead,
  SubscriptionSelfServiceEditorContractRead,
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
} from "@research-pulse/subscription-editor-core";

import { SubscriptionEditorShell } from "./App";

function bootstrapFixture(): SubscriptionEditorBootstrapRead {
  return {
    contract_version: "v1",
    handoff_grant: {
      id: "handoff-1",
      user_id: "user-1",
      channel: "official_account",
      binding_id: "binding-1",
      mini_grant_id: "mini-1",
      self_service_grant_id: "self-service-1",
      status: "active",
      display_label: "Mini editor handoff",
      issued_by: "mini_handoff",
      expires_at: "2026-04-16T05:15:00Z",
      last_used_at: null,
      created_at: "2026-04-16T05:00:00Z",
      updated_at: "2026-04-16T05:00:00Z",
    },
    linked_self_service_grant: {
      id: "self-service-1",
      channel: "official_account",
      binding_id: "binding-1",
      status: "active",
      display_label: "Self-service grant",
      expires_at: null,
      last_used_at: null,
      created_at: "2026-04-16T04:00:00Z",
    },
    user: {
      id: "user-1",
      name: "Mini User",
      email: "mini@example.com",
      field: "Materials",
    },
    official_account_binding_summary: {
      id: "binding-1",
      channel_type: "official_account",
      app_id: "wx-official-app",
      display_label: "OA Binding",
      bind_state: "active",
      subscribed: true,
      digest_enabled: true,
      subscribed_at: null,
      unsubscribed_at: null,
      last_seen_at: null,
    },
    current_settings_draft: {
      subscription_policy_id: "policy-1",
      user_id: "user-1",
      channel: "official_account",
      enabled: true,
      quiet_hours: null,
      timezone: "UTC",
      allowed_weekdays: [0, 1, 2],
      muted_until: null,
      minimum_selected_cards: 1,
      skip_if_no_today_focus: false,
      updated_at: "2026-04-16T04:20:00Z",
      self_service_grant_status: "active",
    },
    latest_digest_summary: {
      id: "digest-1",
      issue_date: "2026-04-16",
      status: "ready",
      title: "Daily digest",
      summary: "1 today focus from 2 selected pulse cards.",
      selected_card_count: 2,
      deep_link_path: "/mini/pulse-digests/user-1/2026-04-16",
    },
    authoritative_preview_supported: true,
    supported_editor_endpoints: [
      "/subscription-editor/bootstrap",
      "/subscription-editor/contract",
      "/subscription-editor/settings/preview",
      "/subscription-editor/settings",
    ],
    notes: [],
  };
}

function contractFixture(): SubscriptionSelfServiceEditorContractRead {
  return {
    contract_version: "v1",
    channel: "official_account",
    editable_section_ids: [
      "delivery_controls",
      "schedule_controls",
      "content_thresholds",
    ],
    weekday_numbering_note: "Weekdays use 0 = Monday and 6 = Sunday.",
    sections: [
      {
        section_id: "delivery_controls",
        title: "Delivery Controls",
        description: "Core on/off state and binding-aware context.",
        editable: true,
        field_ids: [
          "channel",
          "enabled",
          "official_account_binding_summary",
          "self_service_grant_status",
        ],
      },
      {
        section_id: "schedule_controls",
        title: "Schedule Controls",
        description: "Quiet hours, timezone, weekdays, and temporary mute.",
        editable: true,
        field_ids: [
          "quiet_hours",
          "timezone",
          "allowed_weekdays",
          "muted_until",
        ],
      },
      {
        section_id: "content_thresholds",
        title: "Content Thresholds",
        description: "Minimum digest thresholds before delivery is eligible.",
        editable: true,
        field_ids: ["minimum_selected_cards", "skip_if_no_today_focus"],
      },
      {
        section_id: "preview_context",
        title: "Preview Context",
        description: "Read-only fields that help explain preview outcomes.",
        editable: false,
        field_ids: ["latest_digest_summary", "authoritative_preview_supported"],
      },
    ],
    fields: [
      {
        field_id: "enabled",
        label: "Enabled",
        value_type: "boolean",
        editable: true,
        required: true,
        nullable: false,
        description: "Enable or pause official-account digest delivery.",
        validation_hints: {},
      },
      {
        field_id: "timezone",
        label: "Timezone",
        value_type: "string",
        editable: true,
        required: true,
        nullable: false,
        description: "Effective timezone for preview.",
        validation_hints: {},
      },
      {
        field_id: "allowed_weekdays",
        label: "Allowed Weekdays",
        value_type: "integer_list",
        editable: true,
        required: false,
        nullable: false,
        description: "Explicit allowed weekdays.",
        validation_hints: {},
      },
      {
        field_id: "quiet_hours",
        label: "Quiet Hours",
        value_type: "json",
        editable: true,
        required: false,
        nullable: true,
        description: "Quiet-hour windows.",
        validation_hints: {},
      },
      {
        field_id: "muted_until",
        label: "Muted Until",
        value_type: "datetime",
        editable: true,
        required: false,
        nullable: true,
        description: "Pause delivery until the given datetime.",
        validation_hints: {},
      },
      {
        field_id: "minimum_selected_cards",
        label: "Minimum Selected Cards",
        value_type: "integer",
        editable: true,
        required: false,
        nullable: true,
        description: "Minimum digest threshold.",
        validation_hints: {},
      },
      {
        field_id: "skip_if_no_today_focus",
        label: "Skip If No Today Focus",
        value_type: "boolean",
        editable: true,
        required: true,
        nullable: false,
        description: "Skip delivery when there is no today focus.",
        validation_hints: {},
      },
      {
        field_id: "channel",
        label: "Channel",
        value_type: "enum",
        editable: false,
        required: true,
        nullable: false,
        description: "Controlled channel.",
        validation_hints: {},
      },
      {
        field_id: "official_account_binding_summary",
        label: "Official Account Binding Summary",
        value_type: "object",
        editable: false,
        required: false,
        nullable: true,
        description: "Safe binding summary.",
        validation_hints: {},
      },
      {
        field_id: "self_service_grant_status",
        label: "Self-Service Grant Status",
        value_type: "enum",
        editable: false,
        required: true,
        nullable: false,
        description: "Current self-service grant status.",
        validation_hints: {},
      },
      {
        field_id: "latest_digest_summary",
        label: "Latest Digest Summary",
        value_type: "object",
        editable: false,
        required: false,
        nullable: true,
        description: "Digest context.",
        validation_hints: {},
      },
      {
        field_id: "authoritative_preview_supported",
        label: "Authoritative Preview Supported",
        value_type: "boolean",
        editable: false,
        required: true,
        nullable: false,
        description: "Backend preview support.",
        validation_hints: {},
      },
    ],
  };
}

function previewFixture(): SubscriptionSettingsPreviewRead {
  return {
    contract_version: "v1",
    normalized_draft: {
      ...bootstrapFixture().current_settings_draft,
      timezone: "Asia/Shanghai",
      allowed_weekdays: [0, 2, 4],
      minimum_selected_cards: 2,
      skip_if_no_today_focus: true,
    },
    changed_fields: [
      "timezone",
      "allowed_weekdays",
      "minimum_selected_cards",
      "skip_if_no_today_focus",
    ],
    validation_errors: [],
    validation_warnings: [],
    authoritative_preview: {
      state: "ready",
      decision: "eligible",
      reason_codes: [],
      normalized_control_policy: {
        channel: "official_account",
        enabled: true,
        effective_timezone: "Asia/Shanghai",
      },
      current_local_time: "2026-04-16T13:00:00+08:00",
      local_weekday: 3,
      next_allowed_at: null,
      latest_digest_issue: bootstrapFixture().latest_digest_summary,
    },
  };
}

function saveFixture(): SubscriptionSettingsSaveResultRead {
  return {
    contract_version: "v1",
    saved_settings: {
      subscription_policy_id: "policy-1",
      user_id: "user-1",
      channel: "official_account",
      enabled: true,
      quiet_hours: null,
      timezone: "Asia/Shanghai",
      allowed_weekdays: [0, 2, 4],
      muted_until: null,
      minimum_selected_cards: 2,
      skip_if_no_today_focus: true,
      updated_at: "2026-04-16T05:05:00Z",
    },
    changed_fields: ["timezone", "allowed_weekdays"],
    authoritative_preview: previewFixture().authoritative_preview,
  };
}

function createMockApiClient() {
  return {
    getBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
    getContract: vi.fn().mockResolvedValue(contractFixture()),
    previewSettings: vi.fn().mockResolvedValue(previewFixture()),
    saveSettings: vi.fn().mockResolvedValue(saveFixture()),
  };
}

describe("subscription editor shell", () => {
  it("renders token entry state before any handoff token is connected", () => {
    render(<SubscriptionEditorShell initialApiBaseUrl="http://127.0.0.1:8000" />);

    expect(screen.getByText("Subscription editor web shell")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect handoff token" })).toBeInTheDocument();
  });

  it("renders the editor state after bootstrap using the existing editor contract", async () => {
    const apiClient = createMockApiClient();
    const apiClientFactory = vi.fn().mockReturnValue(apiClient);
    const user = userEvent.setup();

    render(
      <SubscriptionEditorShell
        initialApiBaseUrl="http://127.0.0.1:8000"
        apiClientFactory={apiClientFactory}
      />,
    );

    await user.type(
      screen.getByRole("textbox", { name: "Handoff token" }),
      "handoff-token",
    );
    await user.click(screen.getByRole("button", { name: "Connect handoff token" }));

    expect(await screen.findByRole("heading", { name: "Subscription editor" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Delivery Controls" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("UTC")).toBeInTheDocument();
    expect(screen.getByText("Daily digest")).toBeInTheDocument();
  });

  it("renders preview and save result feedback through the authoritative editor endpoints", async () => {
    const apiClient = createMockApiClient();
    const apiClientFactory = vi.fn().mockReturnValue(apiClient);
    const user = userEvent.setup();

    render(
      <SubscriptionEditorShell
        initialApiBaseUrl="http://127.0.0.1:8000"
        apiClientFactory={apiClientFactory}
      />,
    );

    await user.type(
      screen.getByRole("textbox", { name: "Handoff token" }),
      "handoff-token",
    );
    await user.click(screen.getByRole("button", { name: "Connect handoff token" }));
    await screen.findByRole("heading", { name: "Subscription editor" });

    const timezoneInput = screen.getByRole("textbox", { name: "Timezone" });
    await user.clear(timezoneInput);
    await user.type(timezoneInput, "Asia/Shanghai");

    await user.click(screen.getByRole("button", { name: "Preview changes" }));
    expect(await screen.findByText("eligible")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(
        screen.getByText(
          "Saved 2 field(s) to the authoritative subscription policy.",
        ),
      ).toBeInTheDocument(),
    );
  });
});
