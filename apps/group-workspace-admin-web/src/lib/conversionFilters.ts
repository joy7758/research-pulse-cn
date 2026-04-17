import type {
  ConversionFilterInput,
  ConversionFilterSummaryViewModel,
  ConversionFilterSupportViewModel,
  ResultShareKind,
  ResultShareViewAccessMode,
  ResultShareViewEventType,
  ResultShareViewOutcome,
} from "./types";

type FilterOption<T extends string | number> = {
  value: T;
  label: string;
};

type ConversionFilterQuerySupport = {
  includeDimensions: boolean;
  includeOutcome: boolean;
  includeLimit: boolean;
};

const datePattern = /^\d{4}-\d{2}-\d{2}$/;

const shareKindLabels: Record<ResultShareKind, string> = {
  workspace_board: "Workspace board",
  digest_issue: "Digest issue",
  paper_snapshot: "Paper snapshot",
};

const accessModeLabels: Record<ResultShareViewAccessMode, string> = {
  share_token: "Raw share token",
  alias: "Alias",
  alias_redirect: "Alias redirect",
};

const eventTypeLabels: Record<ResultShareViewEventType, string> = {
  bootstrap_view: "Bootstrap view",
  content_view: "Content view",
  redirect: "Redirect",
  invite_handoff_redirect: "Invite handoff redirect",
  collect_handoff_redirect: "Collect handoff redirect",
};

const outcomeLabels: Record<ResultShareViewOutcome, string> = {
  resolved: "Resolved",
  rejected: "Rejected",
};

export const DEFAULT_CONVERSION_FILTER_LIMIT = 20;

export const DEFAULT_CONVERSION_FILTER_INPUT: ConversionFilterInput = {
  dateFrom: null,
  dateTo: null,
  shareKind: null,
  accessMode: null,
  eventType: null,
  outcome: null,
  limit: DEFAULT_CONVERSION_FILTER_LIMIT,
};

export const GLOBAL_CONVERSION_FILTER_SUPPORT: ConversionFilterSupportViewModel = {
  overviewSupportsDimensions: true,
  overviewSupportsOutcome: true,
  drilldownSupportsDimensions: true,
  drilldownSupportsOutcome: true,
  drilldownSupportsLimit: true,
};

export const WORKSPACE_CONVERSION_FILTER_SUPPORT: ConversionFilterSupportViewModel = {
  overviewSupportsDimensions: true,
  overviewSupportsOutcome: true,
  drilldownSupportsDimensions: true,
  drilldownSupportsOutcome: true,
  drilldownSupportsLimit: true,
};

export const SHARE_KIND_FILTER_OPTIONS: FilterOption<ResultShareKind>[] = [
  { value: "workspace_board", label: shareKindLabels.workspace_board },
  { value: "digest_issue", label: shareKindLabels.digest_issue },
  { value: "paper_snapshot", label: shareKindLabels.paper_snapshot },
];

export const ACCESS_MODE_FILTER_OPTIONS: FilterOption<ResultShareViewAccessMode>[] = [
  { value: "share_token", label: accessModeLabels.share_token },
  { value: "alias", label: accessModeLabels.alias },
  { value: "alias_redirect", label: accessModeLabels.alias_redirect },
];

export const EVENT_TYPE_FILTER_OPTIONS: FilterOption<ResultShareViewEventType>[] = [
  { value: "bootstrap_view", label: eventTypeLabels.bootstrap_view },
  { value: "content_view", label: eventTypeLabels.content_view },
  { value: "redirect", label: eventTypeLabels.redirect },
  { value: "invite_handoff_redirect", label: eventTypeLabels.invite_handoff_redirect },
  { value: "collect_handoff_redirect", label: eventTypeLabels.collect_handoff_redirect },
];

export const OUTCOME_FILTER_OPTIONS: FilterOption<ResultShareViewOutcome>[] = [
  { value: "resolved", label: outcomeLabels.resolved },
  { value: "rejected", label: outcomeLabels.rejected },
];

export const LIMIT_FILTER_OPTIONS: FilterOption<number>[] = [
  { value: 10, label: "10" },
  { value: 20, label: "20" },
  { value: 50, label: "50" },
  { value: 100, label: "100" },
];

function normalizeDateInput(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  return datePattern.test(trimmed) ? trimmed : null;
}

function normalizeNullableString<T extends string>(value: T | "" | null | undefined): T | null {
  return value ? value : null;
}

function normalizeLimitInput(value: number | null | undefined): number {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return DEFAULT_CONVERSION_FILTER_LIMIT;
  }
  return Math.max(1, Math.min(100, Math.trunc(value)));
}

function toUtcBoundary(dateValue: string, boundary: "start" | "end"): string {
  const suffix =
    boundary === "start" ? "T00:00:00.000Z" : "T23:59:59.999Z";
  return new Date(`${dateValue}${suffix}`).toISOString();
}

export function formatConversionFilterWindow(dateFrom: string | null, dateTo: string | null): string {
  if (!dateFrom && !dateTo) {
    return "Default analytics window";
  }
  if (dateFrom && dateTo) {
    return `${dateFrom} → ${dateTo}`;
  }
  if (dateFrom) {
    return `${dateFrom} → now`;
  }
  return `Until ${dateTo}`;
}

export function normalizeConversionFilterInput(
  input: Partial<ConversionFilterInput> | ConversionFilterInput,
): ConversionFilterInput {
  const normalizedDateFrom = normalizeDateInput(input.dateFrom);
  const normalizedDateTo = normalizeDateInput(input.dateTo);
  let dateFrom = normalizedDateFrom;
  let dateTo = normalizedDateTo;

  if (dateFrom && dateTo && dateFrom > dateTo) {
    dateFrom = normalizedDateTo;
    dateTo = normalizedDateFrom;
  }

  return {
    dateFrom,
    dateTo,
    shareKind: normalizeNullableString(input.shareKind),
    accessMode: normalizeNullableString(input.accessMode),
    eventType: normalizeNullableString(input.eventType),
    outcome: normalizeNullableString(input.outcome),
    limit: normalizeLimitInput(input.limit),
  };
}

export function buildConversionFilterQuery(
  input: Partial<ConversionFilterInput> | ConversionFilterInput,
  support: ConversionFilterQuerySupport,
): URLSearchParams {
  const filters = normalizeConversionFilterInput(input);
  const query = new URLSearchParams();

  if (filters.dateFrom) {
    query.set("date_from", toUtcBoundary(filters.dateFrom, "start"));
  }
  if (filters.dateTo) {
    query.set("date_to", toUtcBoundary(filters.dateTo, "end"));
  }
  if (support.includeDimensions) {
    if (filters.shareKind) {
      query.set("share_kind", filters.shareKind);
    }
    if (filters.accessMode) {
      query.set("access_mode", filters.accessMode);
    }
    if (filters.eventType) {
      query.set("event_type", filters.eventType);
    }
  }
  if (support.includeOutcome && filters.outcome) {
    query.set("outcome", filters.outcome);
  }
  if (support.includeLimit) {
    query.set("limit", String(filters.limit ?? DEFAULT_CONVERSION_FILTER_LIMIT));
  }
  return query;
}

export function buildConversionFilterSummaryViewModel(
  input: Partial<ConversionFilterInput> | ConversionFilterInput,
  support: ConversionFilterSupportViewModel,
): ConversionFilterSummaryViewModel {
  const filters = normalizeConversionFilterInput(input);
  const chips = [];

  if (filters.dateFrom) {
    chips.push({ key: "dateFrom", label: "Date from", value: filters.dateFrom });
  }
  if (filters.dateTo) {
    chips.push({ key: "dateTo", label: "Date to", value: filters.dateTo });
  }
  if (filters.shareKind) {
    chips.push({
      key: "shareKind",
      label: "Share kind",
      value: shareKindLabels[filters.shareKind],
    });
  }
  if (filters.accessMode) {
    chips.push({
      key: "accessMode",
      label: "Access mode",
      value: accessModeLabels[filters.accessMode],
    });
  }
  if (filters.eventType) {
    chips.push({
      key: "eventType",
      label: "Event type",
      value: eventTypeLabels[filters.eventType],
    });
  }
  if (filters.outcome) {
    chips.push({
      key: "outcome",
      label: "Outcome",
      value: outcomeLabels[filters.outcome],
    });
  }
  if (
    support.drilldownSupportsLimit &&
    filters.limit !== null &&
    filters.limit !== DEFAULT_CONVERSION_FILTER_LIMIT
  ) {
    chips.push({
      key: "limit",
      label: "Recent rows",
      value: String(filters.limit),
    });
  }

  const scopeNotes = ["Date window applies to overview and drilldown."];
  if (support.overviewSupportsDimensions && support.drilldownSupportsDimensions) {
    scopeNotes.push("Share kind, access mode, and event type apply to overview and drilldown.");
  } else if (support.drilldownSupportsDimensions) {
    scopeNotes.push("Share kind, access mode, and event type apply to drilldown.");
  }
  if (support.overviewSupportsOutcome && support.drilldownSupportsOutcome) {
    scopeNotes.push("Outcome applies to overview and drilldown.");
  } else if (support.drilldownSupportsOutcome) {
    scopeNotes.push("Outcome applies to drilldown.");
  }
  if (support.drilldownSupportsLimit) {
    scopeNotes.push("Recent rows limit applies to drilldown recent and top sections.");
  }

  return {
    windowLabel: formatConversionFilterWindow(filters.dateFrom, filters.dateTo),
    chips,
    scopeNotes,
    hasActiveFilters: chips.length > 0,
  };
}
