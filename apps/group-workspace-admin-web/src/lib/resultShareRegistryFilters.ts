import type {
  ResultShareAliasStatus,
  ResultShareGrantStatus,
  ResultShareKind,
  ResultShareRegistryFilterChipViewModel,
  ResultShareRegistryFilterInput,
  ResultShareRegistryFilterSummaryViewModel,
  ResultShareRegistrySectionSortInput,
  ResultShareRegistrySortDirection,
  ResultShareRegistrySortField,
  ResultShareRegistrySortInput,
} from "./types";

type FilterOption<T extends string> = {
  value: T;
  label: string;
};

type RegistrySortOption = {
  key: string;
  label: string;
  field: ResultShareRegistrySortField;
  direction: ResultShareRegistrySortDirection;
};

const shareKindLabels: Record<ResultShareKind, string> = {
  workspace_board: "Workspace board",
  digest_issue: "Digest issue",
  paper_snapshot: "Paper snapshot",
};

const grantStatusLabels: Record<ResultShareGrantStatus, string> = {
  active: "Active grants",
  revoked: "Revoked grants",
  expired: "Expired grants",
};

const aliasStatusLabels: Record<ResultShareAliasStatus, string> = {
  active: "Active aliases",
  revoked: "Revoked aliases",
  expired: "Expired aliases",
};

export const DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT: ResultShareRegistryFilterInput = {
  shareKind: null,
  grantStatus: null,
  aliasStatus: null,
  workspaceId: null,
  resultShareGrantId: null,
};

export const DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT: ResultShareRegistrySortInput = {
  grants: {
    field: "lastUsedAt",
    direction: "desc",
  },
  aliases: {
    field: "lastUsedAt",
    direction: "desc",
  },
};

export const RESULT_SHARE_REGISTRY_SHARE_KIND_OPTIONS: FilterOption<ResultShareKind>[] = [
  { value: "workspace_board", label: shareKindLabels.workspace_board },
  { value: "digest_issue", label: shareKindLabels.digest_issue },
  { value: "paper_snapshot", label: shareKindLabels.paper_snapshot },
];

export const RESULT_SHARE_REGISTRY_GRANT_STATUS_OPTIONS: FilterOption<ResultShareGrantStatus>[] = [
  { value: "active", label: grantStatusLabels.active },
  { value: "revoked", label: grantStatusLabels.revoked },
  { value: "expired", label: grantStatusLabels.expired },
];

export const RESULT_SHARE_REGISTRY_ALIAS_STATUS_OPTIONS: FilterOption<ResultShareAliasStatus>[] = [
  { value: "active", label: aliasStatusLabels.active },
  { value: "revoked", label: aliasStatusLabels.revoked },
  { value: "expired", label: aliasStatusLabels.expired },
];

export const RESULT_SHARE_REGISTRY_SORT_OPTIONS: RegistrySortOption[] = [
  { key: "lastUsedAt_desc", label: "Last used, newest first", field: "lastUsedAt", direction: "desc" },
  { key: "lastUsedAt_asc", label: "Last used, oldest first", field: "lastUsedAt", direction: "asc" },
  { key: "createdAt_desc", label: "Created, newest first", field: "createdAt", direction: "desc" },
  { key: "createdAt_asc", label: "Created, oldest first", field: "createdAt", direction: "asc" },
  { key: "expiresAt_desc", label: "Expires, latest first", field: "expiresAt", direction: "desc" },
  { key: "expiresAt_asc", label: "Expires, soonest first", field: "expiresAt", direction: "asc" },
  { key: "shareKind_asc", label: "Share kind, A-Z", field: "shareKind", direction: "asc" },
  { key: "shareKind_desc", label: "Share kind, Z-A", field: "shareKind", direction: "desc" },
  { key: "status_asc", label: "Status, A-Z", field: "status", direction: "asc" },
  { key: "status_desc", label: "Status, Z-A", field: "status", direction: "desc" },
];

function normalizeNullableString(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed.length > 0 ? trimmed : null;
}

export function normalizeResultShareRegistryFilterInput(
  input: Partial<ResultShareRegistryFilterInput> | ResultShareRegistryFilterInput,
): ResultShareRegistryFilterInput {
  return {
    shareKind: input.shareKind ?? null,
    grantStatus: input.grantStatus ?? null,
    aliasStatus: input.aliasStatus ?? null,
    workspaceId: normalizeNullableString(input.workspaceId),
    resultShareGrantId: normalizeNullableString(input.resultShareGrantId),
  };
}

function normalizeSortField(value: ResultShareRegistrySortField | null | undefined): ResultShareRegistrySortField {
  return value ?? "lastUsedAt";
}

function normalizeSortDirection(
  value: ResultShareRegistrySortDirection | null | undefined,
): ResultShareRegistrySortDirection {
  return value ?? "desc";
}

export function normalizeResultShareRegistrySectionSortInput(
  input: Partial<ResultShareRegistrySectionSortInput> | ResultShareRegistrySectionSortInput,
): ResultShareRegistrySectionSortInput {
  return {
    field: normalizeSortField(input.field),
    direction: normalizeSortDirection(input.direction),
  };
}

export function normalizeResultShareRegistrySortInput(
  input: Partial<ResultShareRegistrySortInput> | ResultShareRegistrySortInput,
): ResultShareRegistrySortInput {
  return {
    grants: normalizeResultShareRegistrySectionSortInput(input.grants ?? DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.grants),
    aliases: normalizeResultShareRegistrySectionSortInput(input.aliases ?? DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.aliases),
  };
}

export function serializeResultShareRegistrySectionSortInput(
  input: Partial<ResultShareRegistrySectionSortInput> | ResultShareRegistrySectionSortInput,
): string {
  const normalized = normalizeResultShareRegistrySectionSortInput(input);
  return `${normalized.field}_${normalized.direction}`;
}

export function parseResultShareRegistrySectionSortInput(
  value: string,
): ResultShareRegistrySectionSortInput {
  const matched = RESULT_SHARE_REGISTRY_SORT_OPTIONS.find((option) => option.key === value);
  if (!matched) {
    return DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.grants;
  }
  return {
    field: matched.field,
    direction: matched.direction,
  };
}

export function formatResultShareRegistrySectionSortLabel(
  input: Partial<ResultShareRegistrySectionSortInput> | ResultShareRegistrySectionSortInput,
): string {
  const key = serializeResultShareRegistrySectionSortInput(input);
  return RESULT_SHARE_REGISTRY_SORT_OPTIONS.find((option) => option.key === key)?.label ?? key;
}

function hasGrantFilters(filters: ResultShareRegistryFilterInput): boolean {
  return Boolean(filters.shareKind || filters.grantStatus || filters.workspaceId);
}

function hasAliasFilters(filters: ResultShareRegistryFilterInput): boolean {
  return Boolean(filters.shareKind || filters.aliasStatus || filters.resultShareGrantId);
}

function buildFilterChip(
  key: string,
  label: string,
  value: string | null,
): ResultShareRegistryFilterChipViewModel | null {
  if (!value) {
    return null;
  }
  return {
    key,
    label,
    value,
  };
}

export function buildResultShareRegistryFilterSummaryViewModel(
  input: Partial<ResultShareRegistryFilterInput> | ResultShareRegistryFilterInput,
  sortInput: Partial<ResultShareRegistrySortInput> | ResultShareRegistrySortInput,
): ResultShareRegistryFilterSummaryViewModel {
  const filters = normalizeResultShareRegistryFilterInput(input);
  const sorts = normalizeResultShareRegistrySortInput(sortInput);
  const chips = [
    buildFilterChip(
      "shareKind",
      "Share kind",
      filters.shareKind ? shareKindLabels[filters.shareKind] : null,
    ),
    buildFilterChip(
      "grantStatus",
      "Grant status",
      filters.grantStatus ? grantStatusLabels[filters.grantStatus] : null,
    ),
    buildFilterChip(
      "aliasStatus",
      "Alias status",
      filters.aliasStatus ? aliasStatusLabels[filters.aliasStatus] : null,
    ),
    buildFilterChip("workspaceId", "Grant workspace", filters.workspaceId),
    buildFilterChip("resultShareGrantId", "Alias grant", filters.resultShareGrantId),
    buildFilterChip(
      "grantSort",
      "Grant sort",
      formatResultShareRegistrySectionSortLabel(sorts.grants),
    ),
    buildFilterChip(
      "aliasSort",
      "Alias sort",
      formatResultShareRegistrySectionSortLabel(sorts.aliases),
    ),
  ].filter((chip): chip is ResultShareRegistryFilterChipViewModel => chip !== null);

  return {
    chips,
    hasActiveFilters: hasGrantFilters(filters) || hasAliasFilters(filters),
    scopeNotes: [
      "Workspace ID narrows the share-grant registry only.",
      "Grant ID narrows the alias registry only.",
      "Share kind applies to both registry sections.",
      "Sorting is stable: null last-used and expiry timestamps stay last, with ID as the tie-breaker.",
      "Quick open reuses the existing read-only per-share drilldown panel.",
    ],
  };
}
