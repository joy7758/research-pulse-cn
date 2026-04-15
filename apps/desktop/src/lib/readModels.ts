import type {
  DeliveryControlLocalHintRead,
  DeliveryControlSettingsRead,
  PaperListItemRead,
  QueueSubscriptionPolicyPatchInput,
  QuietHoursWindowRead,
  TodayOverviewRead,
} from "./types";

export const progressPercentageByPaperType = {
  published: 100,
  revision: 80,
  under_review: 65,
  in_prep: 35,
  paused: 0,
} as const;

export const deliveryControlWeekdays = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
] as const;

export type KnownPaperType = keyof typeof progressPercentageByPaperType;

export type SubscriptionPolicyDraft = {
  enabled: boolean;
  frequencyCap: string;
  timezone: string;
  quietStart: string;
  quietEnd: string;
  allowedWeekdays: number[];
  mutedUntil: string;
  minimumSelectedCards: string;
  skipIfNoTodayFocus: boolean;
};

export function deriveProgressPercentage(paperType: string): number {
  return progressPercentageByPaperType[paperType as KnownPaperType] ?? 0;
}

export function buildTodayEmptyState(message?: string): TodayOverviewRead {
  return {
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
    message: message ?? "No digest issue is cached yet.",
    updatedAt: null,
  };
}

export function sortPapers(papers: PaperListItemRead[]): PaperListItemRead[] {
  return [...papers].sort((left, right) => {
    if (left.priority !== right.priority) {
      return right.priority - left.priority;
    }
    if ((left.lastTouchAt ?? "") !== (right.lastTouchAt ?? "")) {
      return (right.lastTouchAt ?? "").localeCompare(left.lastTouchAt ?? "");
    }
    if ((left.updatedAt ?? "") !== (right.updatedAt ?? "")) {
      return (right.updatedAt ?? "").localeCompare(left.updatedAt ?? "");
    }
    const titleOrder = left.title.localeCompare(right.title);
    if (titleOrder !== 0) {
      return titleOrder;
    }
    return left.id.localeCompare(right.id);
  });
}

export function sortDeliveryControlSettings(
  settings: DeliveryControlSettingsRead[],
): DeliveryControlSettingsRead[] {
  return [...settings].sort((left, right) => {
    const leftPriority = left.channel === "official_account" ? 0 : 1;
    const rightPriority = right.channel === "official_account" ? 0 : 1;
    if (leftPriority !== rightPriority) {
      return leftPriority - rightPriority;
    }
    if ((left.updatedAt ?? "") !== (right.updatedAt ?? "")) {
      return (right.updatedAt ?? "").localeCompare(left.updatedAt ?? "");
    }
    const channelOrder = left.channel.localeCompare(right.channel);
    if (channelOrder !== 0) {
      return channelOrder;
    }
    return left.id.localeCompare(right.id);
  });
}

export function extractQuietHoursDraft(
  quietHours: QuietHoursWindowRead[],
): { start: string; end: string } {
  const primary = quietHours[0];
  return {
    start: primary?.start ?? "",
    end: primary?.end ?? "",
  };
}

export function buildSubscriptionPolicyDraft(
  settings: DeliveryControlSettingsRead,
): SubscriptionPolicyDraft {
  const quietHours = extractQuietHoursDraft(settings.quietHours);
  return {
    enabled: settings.enabled,
    frequencyCap: String(settings.frequencyCap),
    timezone: settings.timezone,
    quietStart: quietHours.start,
    quietEnd: quietHours.end,
    allowedWeekdays: [...settings.allowedWeekdays],
    mutedUntil: toDatetimeLocalValue(settings.mutedUntil),
    minimumSelectedCards:
      settings.minimumSelectedCards === null ? "" : String(settings.minimumSelectedCards),
    skipIfNoTodayFocus: settings.skipIfNoTodayFocus,
  };
}

export function buildSubscriptionPolicyPatchInput(
  settings: DeliveryControlSettingsRead,
  draft: SubscriptionPolicyDraft,
): QueueSubscriptionPolicyPatchInput {
  const timezone = draft.timezone.trim();
  if (!timezone) {
    throw new Error("Timezone is required for desktop delivery-control edits.");
  }

  const frequencyCap = Number(draft.frequencyCap);
  if (!Number.isInteger(frequencyCap) || frequencyCap < 1) {
    throw new Error("Frequency cap must be an integer greater than or equal to 1.");
  }

  const minimumSelectedCards = parseOptionalNonNegativeInteger(
    draft.minimumSelectedCards,
    "Minimum selected cards",
  );
  const quietHours = buildQuietHoursPatch(
    draft.quietStart,
    draft.quietEnd,
    timezone,
  );
  const rawPolicy = { ...settings.rawPolicy };
  const policy = {
    ...rawPolicy,
    timezone,
    allowed_weekdays: serializeAllowedWeekdays(draft.allowedWeekdays),
    muted_until: serializeMutedUntilInput(draft.mutedUntil),
    minimum_selected_cards: minimumSelectedCards,
    skip_if_no_today_focus: draft.skipIfNoTodayFocus,
  };

  return {
    subscriptionPolicyId: settings.id,
    enabled: draft.enabled,
    frequencyCap,
    quietHours,
    policy,
  };
}

export function summarizeDeliveryControlHint(
  hint: DeliveryControlLocalHintRead,
): string {
  if (hint.quietHoursActive) {
    return "Quiet hours are active in the synced policy.";
  }
  if (hint.mutedUntilActive) {
    return "Muted-until is active in the synced policy.";
  }
  if (hint.weekdayBlocked) {
    return "Today is blocked by the synced allowed weekdays rule.";
  }
  return "Current synced policy is not blocked by time, mute, or weekday rules.";
}

export function serializeAllowedWeekdays(allowedWeekdays: number[]): number[] {
  return [...new Set(allowedWeekdays)]
    .filter((value) => Number.isInteger(value) && value >= 0 && value <= 6)
    .sort((left, right) => left - right);
}

export function buildQuietHoursPatch(
  start: string,
  end: string,
  timezone: string,
): Record<string, unknown> | null {
  const nextStart = start.trim();
  const nextEnd = end.trim();
  if (!nextStart && !nextEnd) {
    return null;
  }
  if (!nextStart || !nextEnd) {
    throw new Error("Quiet hours requires both start and end times.");
  }
  if (!isValidTimeString(nextStart) || !isValidTimeString(nextEnd)) {
    throw new Error("Quiet hours times must use HH:MM format.");
  }
  return {
    timezone,
    windows: [
      {
        start: nextStart,
        end: nextEnd,
        timezone,
      },
    ],
  };
}

export function toDatetimeLocalValue(value: string | null): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  const hours = String(parsed.getHours()).padStart(2, "0");
  const minutes = String(parsed.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function serializeMutedUntilInput(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error("Muted until must be a valid local date and time.");
  }
  return parsed.toISOString();
}

function parseOptionalNonNegativeInteger(
  value: string,
  label: string,
): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error(`${label} must be a non-negative integer.`);
  }
  return parsed;
}

function isValidTimeString(value: string): boolean {
  return /^\d{2}:\d{2}$/.test(value);
}
