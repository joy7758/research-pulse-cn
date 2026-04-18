import type {
  ResultShareAliasStatus,
  ResultShareGrantStatus,
  ResultShareKind,
  ResultShareRegistryFilterChipViewModel,
  ResultShareRegistryFilterInput,
  ResultShareRegistryFilterSummaryViewModel,
} from "./types";

type FilterOption<T extends string> = {
  value: T;
  label: string;
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
): ResultShareRegistryFilterSummaryViewModel {
  const filters = normalizeResultShareRegistryFilterInput(input);
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
    buildFilterChip("workspaceId", "Workspace", filters.workspaceId),
    buildFilterChip("resultShareGrantId", "Grant", filters.resultShareGrantId),
  ].filter((chip): chip is ResultShareRegistryFilterChipViewModel => chip !== null);

  return {
    chips,
    hasActiveFilters: chips.length > 0,
    scopeNotes: [
      "Workspace ID narrows the share-grant registry only.",
      "Grant ID narrows the alias registry only.",
      "Quick open reuses the existing read-only per-share drilldown panel.",
    ],
  };
}
