import type { DeliveryControlSettingsRead, PaperListItemRead } from "./types";
import {
  buildQuietHoursPatch,
  buildSubscriptionPolicyDraft,
  buildSubscriptionPolicyPatchInput,
  buildTodayEmptyState,
  deliveryControlWeekdays,
  deriveProgressPercentage,
  extractQuietHoursDraft,
  serializeAllowedWeekdays,
  sortDeliveryControlSettings,
  sortPapers,
  summarizeDeliveryControlHint,
  toDatetimeLocalValue,
} from "./readModels";

describe("desktop read model helpers", () => {
  it("uses the fixed derived progress percentage mapping", () => {
    expect(deriveProgressPercentage("published")).toBe(100);
    expect(deriveProgressPercentage("revision")).toBe(80);
    expect(deriveProgressPercentage("under_review")).toBe(65);
    expect(deriveProgressPercentage("in_prep")).toBe(35);
    expect(deriveProgressPercentage("paused")).toBe(0);
  });

  it("builds a stable today empty state", () => {
    expect(buildTodayEmptyState("No digest yet.")).toEqual({
      state: "empty",
      issueId: null,
      issueDate: null,
      status: null,
      title: null,
      summary: null,
      highlightCount: 0,
      selectedCardCount: 0,
      deepLinkPath: null,
      highlights: [],
      message: "No digest yet.",
      updatedAt: null,
    });
  });

  it("sorts paper list items by stable desktop ordering", () => {
    const papers: PaperListItemRead[] = [
      {
        id: "paper-b",
        userId: "user-1",
        title: "Beta Paper",
        paperType: "published",
        stage: "published",
        venue: null,
        priority: 4,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-14T00:00:00Z",
        progressPercentage: 100,
        updatedAt: "2026-04-14T00:00:00Z",
        pendingMutationCount: 0,
        lastMutationError: null,
        attachmentCount: 0,
        workspaceReady: false,
      },
      {
        id: "paper-a",
        userId: "user-1",
        title: "Alpha Paper",
        paperType: "revision",
        stage: "revision",
        venue: null,
        priority: 5,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-15T00:00:00Z",
        progressPercentage: 80,
        updatedAt: "2026-04-15T00:00:00Z",
        pendingMutationCount: 0,
        lastMutationError: null,
        attachmentCount: 2,
        workspaceReady: true,
      },
      {
        id: "paper-c",
        userId: "user-1",
        title: "Gamma Paper",
        paperType: "revision",
        stage: "revision",
        venue: null,
        priority: 5,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-14T00:00:00Z",
        progressPercentage: 80,
        updatedAt: "2026-04-13T00:00:00Z",
        pendingMutationCount: 0,
        lastMutationError: null,
        attachmentCount: 1,
        workspaceReady: true,
      },
    ];

    expect(sortPapers(papers).map((paper) => paper.id)).toEqual([
      "paper-a",
      "paper-c",
      "paper-b",
    ]);
  });

  it("maps delivery-control drafts from normalized settings", () => {
    const settings: DeliveryControlSettingsRead = {
      id: "policy-1",
      userId: "user-1",
      channel: "official_account",
      enabled: true,
      frequency: "daily",
      quietHours: [{ start: "22:00", end: "07:00", timezone: "Asia/Shanghai" }],
      rawQuietHours: {
        timezone: "Asia/Shanghai",
        windows: [{ start: "22:00", end: "07:00", timezone: "Asia/Shanghai" }],
      },
      timezone: "Asia/Shanghai",
      allowedWeekdays: [0, 2, 4],
      mutedUntil: "2026-04-15T14:30:00Z",
      minimumSelectedCards: 2,
      skipIfNoTodayFocus: true,
      frequencyCap: 3,
      updatedAt: "2026-04-15T00:00:00Z",
      pendingMutationCount: 1,
      lastMutationError: null,
      rawPolicy: { timezone: "Asia/Shanghai", stale_days: 10 },
      localSettingsError: null,
    };

    expect(extractQuietHoursDraft(settings.quietHours)).toEqual({
      start: "22:00",
      end: "07:00",
    });

    expect(buildSubscriptionPolicyDraft(settings)).toMatchObject({
      enabled: true,
      frequencyCap: "3",
      timezone: "Asia/Shanghai",
      quietStart: "22:00",
      quietEnd: "07:00",
      allowedWeekdays: [0, 2, 4],
      minimumSelectedCards: "2",
      skipIfNoTodayFocus: true,
    });
  });

  it("serializes weekdays and policy patch payloads stably from settings drafts", () => {
    const settings: DeliveryControlSettingsRead = {
      id: "policy-1",
      userId: "user-1",
      channel: "official_account",
      enabled: true,
      frequency: "daily",
      quietHours: [{ start: "22:00", end: "07:00", timezone: "UTC" }],
      rawQuietHours: null,
      timezone: "UTC",
      allowedWeekdays: [0, 1, 2],
      mutedUntil: null,
      minimumSelectedCards: null,
      skipIfNoTodayFocus: false,
      frequencyCap: 2,
      updatedAt: "2026-04-15T00:00:00Z",
      pendingMutationCount: 0,
      lastMutationError: null,
      rawPolicy: { timezone: "UTC", stale_days: 10 },
      localSettingsError: null,
    };

    expect(serializeAllowedWeekdays([3, 3, 1, 6, 2])).toEqual([1, 2, 3, 6]);

    const payload = buildSubscriptionPolicyPatchInput(settings, {
      enabled: false,
      frequencyCap: "5",
      timezone: "Asia/Shanghai",
      quietStart: "23:00",
      quietEnd: "08:00",
      allowedWeekdays: [0, 2, 4],
      mutedUntil: "2026-04-16T09:30",
      minimumSelectedCards: "4",
      skipIfNoTodayFocus: true,
    });

    expect(payload).toMatchObject({
      subscriptionPolicyId: "policy-1",
      enabled: false,
      frequencyCap: 5,
      quietHours: {
        timezone: "Asia/Shanghai",
        windows: [{ start: "23:00", end: "08:00", timezone: "Asia/Shanghai" }],
      },
    });
    expect(payload.policy).toMatchObject({
      timezone: "Asia/Shanghai",
      allowed_weekdays: [0, 2, 4],
      minimum_selected_cards: 4,
      skip_if_no_today_focus: true,
      stale_days: 10,
    });
    expect(typeof payload.policy?.muted_until).toBe("string");
  });

  it("sorts official-account settings first and shapes local hint summaries", () => {
    const settings: DeliveryControlSettingsRead[] = [
      {
        id: "policy-in-app",
        userId: "user-1",
        channel: "in_app",
        enabled: true,
        frequency: "daily",
        quietHours: [],
        rawQuietHours: null,
        timezone: "UTC",
        allowedWeekdays: [],
        mutedUntil: null,
        minimumSelectedCards: null,
        skipIfNoTodayFocus: false,
        frequencyCap: 1,
        updatedAt: "2026-04-14T00:00:00Z",
        pendingMutationCount: 0,
        lastMutationError: null,
        rawPolicy: {},
        localSettingsError: null,
      },
      {
        id: "policy-official",
        userId: "user-1",
        channel: "official_account",
        enabled: true,
        frequency: "daily",
        quietHours: [],
        rawQuietHours: null,
        timezone: "UTC",
        allowedWeekdays: [],
        mutedUntil: null,
        minimumSelectedCards: null,
        skipIfNoTodayFocus: false,
        frequencyCap: 1,
        updatedAt: "2026-04-15T00:00:00Z",
        pendingMutationCount: 0,
        lastMutationError: null,
        rawPolicy: {},
        localSettingsError: null,
      },
    ];

    expect(sortDeliveryControlSettings(settings).map((entry) => entry.id)).toEqual([
      "policy-official",
      "policy-in-app",
    ]);

    expect(
      summarizeDeliveryControlHint({
        subscriptionPolicyId: "policy-official",
        channel: "official_account",
        effectiveTimezone: "UTC",
        currentLocalTime: "2026-04-15T09:30:00Z",
        localWeekday: 2,
        quietHoursActive: false,
        mutedUntilActive: true,
        weekdayBlocked: false,
        nextAllowedAtApprox: "2026-04-15T11:00:00Z",
        notes: ["Muted-until is active in the synced policy."],
        localSettingsError: null,
      }),
    ).toContain("Muted-until");
  });

  it("keeps weekday numbering and datetime-local shaping stable", () => {
    expect(deliveryControlWeekdays.map((entry) => entry.value)).toEqual([0, 1, 2, 3, 4, 5, 6]);
    expect(typeof toDatetimeLocalValue("2026-04-15T09:30:00Z")).toBe("string");
    expect(buildQuietHoursPatch("22:00", "07:00", "UTC")).toEqual({
      timezone: "UTC",
      windows: [{ start: "22:00", end: "07:00", timezone: "UTC" }],
    });
  });
});
