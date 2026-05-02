import type {
  EditorFormState,
  PreviewDisplayModel,
  QuietHoursWindowDraft,
  SaveDisplayModel,
  SubscriptionEditorBootstrapRead,
  SubscriptionEditorSettingsPatchInput,
  SubscriptionSelfServiceEditorContractRead,
  SubscriptionSettingsPreviewRead,
  SubscriptionSettingsSaveResultRead,
  SubscriptionSettingsValidationIssueRead,
} from "./types";

export const weekdayOptions = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
] as const;

export function createQuietHoursWindowDraft(
  index: number,
  window?: { start: string; end: string },
): QuietHoursWindowDraft {
  return {
    id: `quiet-window-${index}`,
    start: window?.start ?? "",
    end: window?.end ?? "",
  };
}

export function normalizeWeekdaySelection(days: number[]): number[] {
  return [...new Set(days)]
    .filter((day) => Number.isInteger(day) && day >= 0 && day <= 6)
    .sort((left, right) => left - right);
}

function formatDateTimeInTimeZone(value: Date, timeZone: string): string | null {
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(value);
    const partMap = new Map(parts.map((part) => [part.type, part.value]));
    const year = partMap.get("year");
    const month = partMap.get("month");
    const day = partMap.get("day");
    const hour = partMap.get("hour");
    const minute = partMap.get("minute");
    if (!year || !month || !day || !hour || !minute) {
      return null;
    }
    return `${year}-${month}-${day}T${hour}:${minute}`;
  } catch {
    return null;
  }
}

function getTimeZoneOffsetMs(value: Date, timeZone: string): number | null {
  const localValue = formatDateTimeInTimeZone(value, timeZone);
  if (!localValue) {
    return null;
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(localValue);
  if (!match) {
    return null;
  }
  const [, year, month, day, hour, minute] = match;
  const localAsUtc = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
  );
  return localAsUtc - value.getTime();
}

export function toDatetimeLocalValue(value: string | null, timeZone?: string): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  if (timeZone) {
    const zonedValue = formatDateTimeInTimeZone(parsed, timeZone);
    if (zonedValue) {
      return zonedValue;
    }
  }
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  const hours = String(parsed.getHours()).padStart(2, "0");
  const minutes = String(parsed.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function fromDatetimeLocalValue(value: string, timeZone?: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const localMatch =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(trimmed);
  if (localMatch && timeZone) {
    const [, year, month, day, hour, minute, second] = localMatch;
    const utcGuess = new Date(
      Date.UTC(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hour),
        Number(minute),
        Number(second ?? "0"),
      ),
    );
    const offset = getTimeZoneOffsetMs(utcGuess, timeZone);
    if (offset !== null) {
      const firstPass = new Date(utcGuess.getTime() - offset);
      const correctedOffset = getTimeZoneOffsetMs(firstPass, timeZone);
      return new Date(
        utcGuess.getTime() - (correctedOffset ?? offset),
      ).toISOString();
    }
  }
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) {
    return trimmed;
  }
  return parsed.toISOString();
}

export function buildFormStateFromBootstrap(
  bootstrap: SubscriptionEditorBootstrapRead,
): EditorFormState {
  const quietHoursWindows =
    bootstrap.current_settings_draft.quiet_hours?.windows?.map((window, index) =>
      createQuietHoursWindowDraft(index, window),
    ) ?? [];
  return {
    enabled: bootstrap.current_settings_draft.enabled,
    timezone: bootstrap.current_settings_draft.timezone,
    quietHoursWindows,
    allowedWeekdays: normalizeWeekdaySelection(
      bootstrap.current_settings_draft.allowed_weekdays,
    ),
    mutedUntil: toDatetimeLocalValue(
      bootstrap.current_settings_draft.muted_until,
      bootstrap.current_settings_draft.timezone,
    ),
    minimumSelectedCards:
      bootstrap.current_settings_draft.minimum_selected_cards === null
        ? ""
        : String(bootstrap.current_settings_draft.minimum_selected_cards),
    skipIfNoTodayFocus: bootstrap.current_settings_draft.skip_if_no_today_focus,
  };
}

export function buildSettingsPatchPayload(
  form: EditorFormState,
): SubscriptionEditorSettingsPatchInput {
  const trimmedTimezone = form.timezone.trim();
  const trimmedMinimumSelectedCards = form.minimumSelectedCards.trim();
  const quietHoursWindows = form.quietHoursWindows.map((window) => ({
    start: window.start.trim(),
    end: window.end.trim(),
    timezone: trimmedTimezone,
  }));
  return {
    enabled: form.enabled,
    quiet_hours:
      quietHoursWindows.length === 0
        ? null
        : {
            timezone: trimmedTimezone,
            windows: quietHoursWindows,
          },
    timezone: trimmedTimezone,
    allowed_weekdays: normalizeWeekdaySelection(form.allowedWeekdays),
    muted_until: fromDatetimeLocalValue(form.mutedUntil, trimmedTimezone),
    minimum_selected_cards:
      trimmedMinimumSelectedCards === ""
        ? null
        : /^-?\d+$/.test(trimmedMinimumSelectedCards)
          ? Number(trimmedMinimumSelectedCards)
          : trimmedMinimumSelectedCards,
    skip_if_no_today_focus: form.skipIfNoTodayFocus,
  };
}

export function buildDraftFingerprint(form: EditorFormState): string {
  return JSON.stringify(buildSettingsPatchPayload(form));
}

export function buildContractFieldMap(
  contract: SubscriptionSelfServiceEditorContractRead,
): Map<string, SubscriptionSelfServiceEditorContractRead["fields"][number]> {
  return new Map(contract.fields.map((field) => [field.field_id, field]));
}

export function groupValidationIssuesByField(
  issues: SubscriptionSettingsValidationIssueRead[],
): Record<string, SubscriptionSettingsValidationIssueRead[]> {
  return issues.reduce<Record<string, SubscriptionSettingsValidationIssueRead[]>>(
    (grouped, issue) => {
      grouped[issue.field_id] ??= [];
      grouped[issue.field_id].push(issue);
      return grouped;
    },
    {},
  );
}

export function buildPreviewDisplayModel(
  preview: SubscriptionSettingsPreviewRead["authoritative_preview"],
): PreviewDisplayModel {
  return {
    state: preview.state,
    decisionLabel: preview.decision ?? "Unavailable",
    reasonCodes: preview.reason_codes,
    normalizedControlPolicyText: JSON.stringify(
      preview.normalized_control_policy ?? {},
      null,
      2,
    ),
    currentLocalTimeLabel: preview.current_local_time ?? "Unavailable",
    localWeekdayLabel:
      preview.local_weekday === null ? "Unavailable" : String(preview.local_weekday),
    nextAllowedAtLabel: preview.next_allowed_at ?? "Unavailable",
    latestDigestLabel: preview.latest_digest_issue
      ? `${preview.latest_digest_issue.title} (${preview.latest_digest_issue.issue_date})`
      : "Unavailable",
  };
}

export function buildSaveDisplayModel(
  saveResult: SubscriptionSettingsSaveResultRead,
): SaveDisplayModel {
  return {
    summary: `Saved ${saveResult.changed_fields.length} field(s) to the authoritative subscription policy.`,
    changedFields: saveResult.changed_fields,
    savedSettings: saveResult.saved_settings,
    authoritativePreview: saveResult.authoritative_preview,
  };
}
