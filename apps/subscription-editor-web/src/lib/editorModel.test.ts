import type {
  SubscriptionEditorBootstrapRead,
  SubscriptionSelfServiceEditorContractRead,
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
} from "./types";
import {
  buildContractFieldMap,
  buildFormStateFromBootstrap,
  buildPreviewDisplayModel,
  buildSaveDisplayModel,
  buildSettingsPatchPayload,
  normalizeWeekdaySelection,
} from "./editorModel";

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
      quiet_hours: {
        timezone: "Asia/Shanghai",
        windows: [
          {
            start: "22:00",
            end: "07:00",
            timezone: "Asia/Shanghai",
          },
        ],
      },
      timezone: "Asia/Shanghai",
      allowed_weekdays: [0, 2, 2, 4],
      muted_until: "2026-04-16T12:00:00Z",
      minimum_selected_cards: 2,
      skip_if_no_today_focus: true,
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

describe("subscription editor model helpers", () => {
  it("shapes bootstrap data into deterministic local form state", () => {
    expect(buildFormStateFromBootstrap(bootstrapFixture())).toEqual({
      enabled: true,
      timezone: "Asia/Shanghai",
      quietHoursWindows: [
        {
          id: "quiet-window-0",
          start: "22:00",
          end: "07:00",
        },
      ],
      allowedWeekdays: [0, 2, 4],
      mutedUntil: "2026-04-16T20:00",
      minimumSelectedCards: "2",
      skipIfNoTodayFocus: true,
    });
  });

  it("maps contract fields and preserves weekday serialization stability", () => {
    const contract: SubscriptionSelfServiceEditorContractRead = {
      contract_version: "v1",
      channel: "official_account",
      editable_section_ids: ["schedule_controls"],
      weekday_numbering_note: "Weekdays use 0 = Monday and 6 = Sunday.",
      sections: [
        {
          section_id: "schedule_controls",
          title: "Schedule Controls",
          description: "Quiet hours, timezone, weekdays, and temporary mute.",
          editable: true,
          field_ids: ["allowed_weekdays", "timezone"],
        },
      ],
      fields: [
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
      ],
    };

    expect(buildContractFieldMap(contract).get("allowed_weekdays")?.label).toBe(
      "Allowed Weekdays",
    );
    expect(normalizeWeekdaySelection([4, 2, 2, 0])).toEqual([0, 2, 4]);
    expect(
      buildSettingsPatchPayload({
        enabled: true,
        timezone: "Asia/Shanghai",
        quietHoursWindows: [],
        allowedWeekdays: [4, 2, 2, 0],
        mutedUntil: "",
        minimumSelectedCards: "3",
        skipIfNoTodayFocus: false,
      }),
    ).toMatchObject({
      timezone: "Asia/Shanghai",
      allowed_weekdays: [0, 2, 4],
      minimum_selected_cards: 3,
    });
  });

  it("shapes preview and save responses for deterministic rendering", () => {
    const preview: SubscriptionSettingsPreviewRead = {
      contract_version: "v1",
      normalized_draft: bootstrapFixture().current_settings_draft,
      changed_fields: ["timezone"],
      validation_errors: [],
      validation_warnings: [],
      authoritative_preview: {
        state: "ready",
        decision: "eligible",
        reason_codes: [],
        normalized_control_policy: { timezone: "Asia/Shanghai" },
        current_local_time: "2026-04-16T13:00:00+08:00",
        local_weekday: 3,
        next_allowed_at: null,
        latest_digest_issue: bootstrapFixture().latest_digest_summary,
      },
    };
    const saveResult: SubscriptionSettingsSaveResultRead = {
      contract_version: "v1",
      saved_settings: {
        ...bootstrapFixture().current_settings_draft,
      },
      changed_fields: ["timezone"],
      authoritative_preview: preview.authoritative_preview,
    };

    expect(buildPreviewDisplayModel(preview.authoritative_preview)).toMatchObject({
      state: "ready",
      decisionLabel: "eligible",
      currentLocalTimeLabel: "2026-04-16T13:00:00+08:00",
    });
    expect(buildSaveDisplayModel(saveResult)).toMatchObject({
      summary: "Saved 1 field(s) to the authoritative subscription policy.",
      changedFields: ["timezone"],
    });
  });
});
