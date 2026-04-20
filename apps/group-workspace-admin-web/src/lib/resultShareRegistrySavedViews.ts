import {
  buildConversionFilterSummaryViewModel,
  DEFAULT_CONVERSION_FILTER_INPUT,
  normalizeConversionFilterInput,
  PER_SHARE_DRILLDOWN_FILTER_SUPPORT,
} from "./conversionFilters";
import {
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
  formatResultShareRegistrySectionSortLabel,
  normalizeResultShareRegistryFilterInput,
  normalizeResultShareRegistrySectionSortInput,
  normalizeResultShareRegistrySortInput,
} from "./resultShareRegistryFilters";
import type {
  ConversionFilterInput,
  ResultShareRegistryFilterInput,
  ResultShareRegistryPresetBackupSnapshot,
  ResultShareRegistryPresetExportPayload,
  ResultShareRegistryPresetIntegrityIssue,
  ResultShareRegistryPresetIntegrityIssueCode,
  ResultShareRegistryPresetIntegrityReport,
  ResultShareRegistryPresetImportApplyResult,
  ResultShareRegistryPresetImportMode,
  ResultShareRegistryPresetImportPreview,
  ResultShareRegistryPresetLocalAuditActionType,
  ResultShareRegistryPresetLocalAuditEvent,
  ResultShareRegistryPresetLocalAuditLoadResult,
  ResultShareRegistryPresetLocalAuditStatus,
  ResultShareRegistryPresetLocalAuditSummary,
  ResultShareRegistryPresetRecoveryAction,
  ResultShareRegistrySavedViewApplyMode,
  ResultShareRegistrySavedView,
  ResultShareRegistrySavedViewDrilldownContext,
  ResultShareRegistrySavedViewDraft,
  ResultShareRegistrySavedViewScope,
  ResultShareRegistrySavedViewStoreState,
  ResultShareRegistrySavedViewSummary,
  ResultShareRegistryPresetStorageDiagnostics,
  ResultShareRegistryPresetWorkspaceLoadResult,
  ResultShareRegistryPresetWorkspaceBackupSnapshot,
  ResultShareRegistryPresetWorkspaceExportPayload,
  ResultShareRegistryPresetWorkspaceHealthFinding,
  ResultShareRegistryPresetWorkspaceHealthClipboardFormat,
  ResultShareRegistryPresetWorkspaceHealthClipboardSummary,
  ResultShareRegistryPresetWorkspaceHealthClipboardValidationResult,
  ResultShareRegistryPresetWorkspaceHealthReport,
  ResultShareRegistryPresetWorkspaceHealthReportMetadata,
  ResultShareRegistryPresetWorkspaceHealthReportPreview,
  ResultShareRegistryPresetWorkspaceHealthReportValidationResult,
  ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey,
  ResultShareRegistryPresetWorkspaceHealthThresholdDraft,
  ResultShareRegistryPresetWorkspaceHealthThresholdLoadResult,
  ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
  ResultShareRegistryPresetWorkspaceHealthThresholdPreview,
  ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult,
  ResultShareRegistryPresetWorkspaceHealthRecommendation,
  ResultShareRegistryPresetWorkspaceHealthScore,
  ResultShareRegistryPresetWorkspaceHealthStatus,
  ResultShareRegistryPresetWorkspaceImportApplyResult,
  ResultShareRegistryPresetWorkspaceImportPreview,
  ResultShareRegistryPresetWorkspaceState,
  ResultShareRegistryPresetWorkspaceViewModel,
  ResultShareRegistrySortInput,
} from "./types";

export const RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY = "resultShareRegistryGrantPresets";
export const RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY = "resultShareRegistryAliasPresets";
export const RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY =
  "resultShareRegistryDefaultPresetId";
export const RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY =
  "resultShareRegistryPresetLastGoodBackup";
export const RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY =
  "resultShareRegistryPresetLocalAuditEvents";
export const RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY =
  "resultShareRegistryPresetWorkspaceState";
export const RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY =
  "resultShareRegistryPresetWorkspaceLastGoodBackup";
export const RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY =
  "resultShareRegistryPresetWorkspaceHealthThresholdPreferences";
export const RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION =
  "result-share-registry-presets.v1";
export const RESULT_SHARE_REGISTRY_PRESET_BACKUP_SCHEMA_VERSION =
  "result-share-registry-presets-backup.v1";
export const RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION =
  "result-share-registry-preset-workspace.v1";
export const RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION =
  "result-share-registry-preset-workspace-backup.v1";
export const RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION =
  "result-share-registry-preset-workspace-health-report.v1";
const RESULT_SHARE_REGISTRY_LOCAL_AUDIT_MAX_EVENTS = 100;
const RESULT_SHARE_REGISTRY_LOCAL_AUDIT_RECENT_LIMIT = 12;

const presetTopLevelAllowedKeys = new Set([
  "schemaVersion",
  "exportedAt",
  "app",
  "source",
  "presets",
  "defaultPresetId",
]);
const presetEnvelopeAllowedKeys = new Set(["grantRegistry", "aliasRegistry", "defaultPresetId"]);
const presetAllowedKeys = new Set([
  "id",
  "name",
  "scope",
  "filters",
  "sort",
  "drilldownContext",
  "createdAt",
  "updatedAt",
]);
const presetFilterAllowedKeys = new Set([
  "shareKind",
  "grantStatus",
  "aliasStatus",
  "workspaceId",
  "resultShareGrantId",
]);
const presetSortAllowedKeys = new Set(["field", "direction"]);
const presetDrilldownAllowedKeys = new Set([
  "dateFrom",
  "dateTo",
  "accessMode",
  "eventType",
  "outcome",
  "limit",
]);
const workspaceExportAllowedKeys = new Set([
  "schemaVersion",
  "exportedAt",
  "app",
  "source",
  "workspaceState",
]);
const workspaceStateAllowedKeys = new Set([
  "pinnedGrantPresetIds",
  "pinnedAliasPresetIds",
  "lastActivePresetScope",
  "lastActivePresetId",
  "collapsedSections",
  "updatedAt",
]);
const workspaceCollapsedSectionAllowedKeys = new Set([
  "pinnedGrantPresets",
  "pinnedAliasPresets",
  "recentGrantPresets",
  "recentAliasPresets",
  "recentActivity",
  "storageHealth",
]);
const workspaceHealthThresholdPreferencesAllowedKeys = new Set([
  "statusThresholds",
  "findingPenaltyOverrides",
  "recommendationVisibility",
  "updatedAt",
]);
const workspaceHealthThresholdStatusAllowedKeys = new Set([
  "healthyMin",
  "attentionMin",
  "riskMin",
  "criticalMin",
]);
const workspaceHealthThresholdVisibilityAllowedKeys = new Set([
  "showInfo",
  "showWarnings",
  "showErrors",
  "showCritical",
]);
const unsafeFieldPattern =
  /(^|_)(token|secret|password|hash|rawalias|rawsharetoken|localpath|absolutepath|sourcefile|responsepayload)(_|$)|rawAlias|rawShareToken|localPath|absolutePath|sourceFile|responsePayload|alias_hash|token_hash/i;

const presetLocalAuditActionTypes: ResultShareRegistryPresetLocalAuditActionType[] = [
  "preset_saved",
  "preset_applied",
  "preset_overwritten",
  "preset_deleted",
  "preset_pinned",
  "preset_unpinned",
  "preset_workspace_health_checked",
  "preset_workspace_health_report_exported_json",
  "preset_workspace_health_report_exported_markdown",
  "preset_workspace_health_report_validation_failed",
  "preset_workspace_health_report_copied_summary",
  "preset_workspace_health_report_copied_findings",
  "preset_workspace_health_report_copied_recommendations",
  "preset_workspace_health_report_copied_markdown",
  "preset_workspace_health_report_copied_json",
  "preset_workspace_health_report_copy_validation_failed",
  "preset_workspace_health_report_copy_failed",
  "preset_workspace_health_thresholds_updated",
  "preset_workspace_health_thresholds_reset",
  "preset_workspace_health_threshold_validation_failed",
  "preset_workspace_export_created",
  "preset_workspace_import_dry_run",
  "preset_workspace_import_merge",
  "preset_workspace_import_replace",
  "preset_workspace_backup_created",
  "preset_workspace_backup_restored",
  "preset_workspace_import_validation_failed",
  "default_set",
  "default_cleared",
  "import_dry_run",
  "import_merge",
  "import_replace",
  "export_created",
  "integrity_checked",
  "invalid_presets_discarded",
  "scope_reset",
  "all_presets_reset",
  "dangling_default_cleared",
  "backup_created",
  "backup_restored",
  "recovery_failed",
  "validation_failed",
  "preset_workspace_reset",
  "stale_pins_cleaned",
];

type StorageInspectionScopeResult = {
  keyPresent: boolean;
  rawCount: number;
  validPresets: ResultShareRegistrySavedView[];
};

export type ResultShareRegistryPresetStorageInspection = {
  store: ResultShareRegistrySavedViewStoreState;
  report: ResultShareRegistryPresetIntegrityReport;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
  lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null;
};

function createAuditEventId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `registry-preset-audit-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function buildIssue(
  issue: ResultShareRegistryPresetIntegrityIssue,
): ResultShareRegistryPresetIntegrityIssue {
  return issue;
}

function pushIssue(
  issues: ResultShareRegistryPresetIntegrityIssue[],
  issue: ResultShareRegistryPresetIntegrityIssue,
): void {
  issues.push(buildIssue(issue));
}

function createSavedViewId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `registry-preset-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeScope(
  value: ResultShareRegistrySavedViewScope | string | null | undefined,
): ResultShareRegistrySavedViewScope | null {
  return value === "grant_registry" || value === "alias_registry" ? value : null;
}

function normalizeFiltersForScope(
  scope: ResultShareRegistrySavedViewScope,
  filters: Partial<ResultShareRegistryFilterInput> | ResultShareRegistryFilterInput,
): ResultShareRegistryFilterInput {
  const normalized = normalizeResultShareRegistryFilterInput(filters);
  if (scope === "grant_registry") {
    return {
      ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
      shareKind: normalized.shareKind,
      grantStatus: normalized.grantStatus,
      workspaceId: normalized.workspaceId,
    };
  }
  return {
    ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
    shareKind: normalized.shareKind,
    aliasStatus: normalized.aliasStatus,
    resultShareGrantId: normalized.resultShareGrantId,
  };
}

function normalizeDrilldownContext(
  value:
    | Partial<ResultShareRegistrySavedViewDrilldownContext>
    | ConversionFilterInput
    | ResultShareRegistrySavedViewDrilldownContext
    | null
    | undefined,
): ResultShareRegistrySavedViewDrilldownContext | null {
  if (!value) {
    return null;
  }
  const normalized = normalizeConversionFilterInput({
    ...DEFAULT_CONVERSION_FILTER_INPUT,
    ...value,
    shareKind: null,
  });
  return {
    dateFrom: normalized.dateFrom,
    dateTo: normalized.dateTo,
    accessMode: normalized.accessMode,
    eventType: normalized.eventType,
    outcome: normalized.outcome,
    limit: normalized.limit,
  };
}

export function buildResultShareRegistrySavedViewDraft(
  scope: ResultShareRegistrySavedViewScope,
  name: string,
  filters: ResultShareRegistryFilterInput,
  sorts: ResultShareRegistrySortInput,
  options?: {
    includeDrilldownContext?: boolean;
    drilldownFilters?: ConversionFilterInput;
  },
): ResultShareRegistrySavedViewDraft | null {
  const trimmedName = name.trim();
  if (!trimmedName) {
    return null;
  }
  const normalizedSorts = normalizeResultShareRegistrySortInput(sorts);
  return {
    name: trimmedName,
    scope,
    filters: normalizeFiltersForScope(scope, filters),
    sort: normalizeResultShareRegistrySectionSortInput(
      scope === "grant_registry" ? normalizedSorts.grants : normalizedSorts.aliases,
    ),
    drilldownContext: options?.includeDrilldownContext
      ? normalizeDrilldownContext(options.drilldownFilters ?? DEFAULT_CONVERSION_FILTER_INPUT)
      : null,
  };
}

export function createResultShareRegistrySavedView(
  draft: ResultShareRegistrySavedViewDraft,
  options?: {
    id?: string;
    now?: string;
  },
): ResultShareRegistrySavedView {
  const timestamp = options?.now ?? new Date().toISOString();
  return {
    id: options?.id ?? createSavedViewId(),
    name: draft.name.trim(),
    scope: draft.scope,
    filters: normalizeFiltersForScope(draft.scope, draft.filters),
    sort: normalizeResultShareRegistrySectionSortInput(draft.sort),
    drilldownContext: normalizeDrilldownContext(draft.drilldownContext),
    createdAt: timestamp,
    updatedAt: timestamp,
  };
}

function normalizeSavedView(
  value: unknown,
  scope: ResultShareRegistrySavedViewScope,
): ResultShareRegistrySavedView | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const candidate = value as Partial<ResultShareRegistrySavedView>;
  const normalizedScope = normalizeScope(candidate.scope ?? scope);
  if (normalizedScope !== scope) {
    return null;
  }
  const name = candidate.name?.trim() ?? "";
  const id = candidate.id?.trim() ?? "";
  const createdAt = candidate.createdAt?.trim() ?? "";
  const updatedAt = candidate.updatedAt?.trim() ?? "";
  if (!name || !id || !createdAt || !updatedAt) {
    return null;
  }
  return {
    id,
    name,
    scope,
    filters: normalizeFiltersForScope(scope, candidate.filters ?? DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT),
    sort: normalizeResultShareRegistrySectionSortInput(
      candidate.sort ??
        (scope === "grant_registry"
          ? DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.grants
          : DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.aliases),
    ),
    drilldownContext: normalizeDrilldownContext(candidate.drilldownContext),
    createdAt,
    updatedAt,
  };
}

export function sanitizeImportedSavedView(
  value: unknown,
  scope: ResultShareRegistrySavedViewScope,
  warnings: string[],
  errors: string[],
  path: string,
): ResultShareRegistrySavedView | null {
  if (!isRecord(value)) {
    errors.push(`${path} is not a valid preset object.`);
    return null;
  }

  const hasUnsafePresetKeys = collectUnexpectedKeys(value, presetAllowedKeys, path, warnings, errors);
  if (hasUnsafePresetKeys) {
    return null;
  }

  if (value.scope !== scope) {
    errors.push(`${path} has invalid scope "${String(value.scope ?? "")}".`);
    return null;
  }

  if ("filters" in value && isRecord(value.filters)) {
    if (
      collectUnexpectedKeys(
        value.filters,
        presetFilterAllowedKeys,
        `${path}.filters`,
        warnings,
        errors,
      )
    ) {
      return null;
    }
  } else if ("filters" in value && value.filters !== null && value.filters !== undefined) {
    errors.push(`${path}.filters must be an object.`);
    return null;
  }

  if ("sort" in value && isRecord(value.sort)) {
    if (
      collectUnexpectedKeys(value.sort, presetSortAllowedKeys, `${path}.sort`, warnings, errors)
    ) {
      return null;
    }
  } else if ("sort" in value && value.sort !== null && value.sort !== undefined) {
    errors.push(`${path}.sort must be an object.`);
    return null;
  }

  if ("drilldownContext" in value && value.drilldownContext !== null && value.drilldownContext !== undefined) {
    if (!isRecord(value.drilldownContext)) {
      errors.push(`${path}.drilldownContext must be an object or null.`);
      return null;
    }
    if (
      collectUnexpectedKeys(
        value.drilldownContext,
        presetDrilldownAllowedKeys,
        `${path}.drilldownContext`,
        warnings,
        errors,
      )
    ) {
      return null;
    }
  }

  const normalized = normalizeSavedView(value, scope);
  if (!normalized) {
    errors.push(`${path} does not match the expected preset shape.`);
    return null;
  }
  return normalized;
}

export function buildResultShareRegistryPresetExport(
  store: ResultShareRegistrySavedViewStoreState,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetExportPayload {
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
    exportedAt: options?.now ?? new Date().toISOString(),
    app: "research-pulse-cn",
    source: "group-workspace-admin-web",
    presets: {
      grantRegistry: store.grantPresets,
      aliasRegistry: store.aliasPresets,
    },
  };
}

export function parseResultShareRegistryPresetImport(
  raw: string,
): ResultShareRegistryPresetImportPreview {
  const warnings: string[] = [];
  const errors: string[] = [];
  let parsed: unknown;

  try {
    parsed = JSON.parse(raw);
  } catch {
    return {
      schemaVersion: null,
      validPresetCount: 0,
      invalidPresetCount: 0,
      grantPresetCount: 0,
      aliasPresetCount: 0,
      warnings: [],
      errors: ["Import file is not valid JSON."],
      canApply: false,
      importedScopes: {
        grantRegistry: false,
        aliasRegistry: false,
      },
      presets: {
        grantRegistry: [],
        aliasRegistry: [],
      },
    };
  }

  if (!isRecord(parsed)) {
    return {
      schemaVersion: null,
      validPresetCount: 0,
      invalidPresetCount: 0,
      grantPresetCount: 0,
      aliasPresetCount: 0,
      warnings: [],
      errors: ["Import file must contain a JSON object."],
      canApply: false,
      importedScopes: {
        grantRegistry: false,
        aliasRegistry: false,
      },
      presets: {
        grantRegistry: [],
        aliasRegistry: [],
      },
    };
  }

  collectUnexpectedKeys(parsed, presetTopLevelAllowedKeys, "Import payload", warnings, errors);

  const schemaVersion =
    typeof parsed.schemaVersion === "string" ? parsed.schemaVersion : null;
  if (schemaVersion !== RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION) {
    errors.push(
      `Import schemaVersion must be "${RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION}".`,
    );
  }

  if (
    typeof parsed.app === "string" &&
    parsed.app !== "research-pulse-cn"
  ) {
    warnings.push(`Import app is "${parsed.app}" instead of "research-pulse-cn".`);
  }
  if (
    typeof parsed.source === "string" &&
    parsed.source !== "group-workspace-admin-web"
  ) {
    warnings.push(`Import source is "${parsed.source}" instead of "group-workspace-admin-web".`);
  }
  if ("defaultPresetId" in parsed) {
    warnings.push("Imported default preset markers are ignored in v1.");
  }

  const presetEnvelope = parsed.presets;
  if (!isRecord(presetEnvelope)) {
    errors.push('Import payload must contain a "presets" object.');
    return {
      schemaVersion,
      validPresetCount: 0,
      invalidPresetCount: 0,
      grantPresetCount: 0,
      aliasPresetCount: 0,
      warnings,
      errors,
      canApply: false,
      importedScopes: {
        grantRegistry: false,
        aliasRegistry: false,
      },
      presets: {
        grantRegistry: [],
        aliasRegistry: [],
      },
    };
  }

  collectUnexpectedKeys(presetEnvelope, presetEnvelopeAllowedKeys, "Import payload.presets", warnings, errors);
  if ("defaultPresetId" in presetEnvelope) {
    warnings.push("Imported nested default preset markers are ignored in v1.");
  }

  const grantScopePresent = Object.prototype.hasOwnProperty.call(presetEnvelope, "grantRegistry");
  const aliasScopePresent = Object.prototype.hasOwnProperty.call(presetEnvelope, "aliasRegistry");

  const sanitizedGrantPresets: ResultShareRegistrySavedView[] = [];
  const sanitizedAliasPresets: ResultShareRegistrySavedView[] = [];
  let invalidPresetCount = 0;

  const parseScope = (
    scope: ResultShareRegistrySavedViewScope,
    envelopeKey: "grantRegistry" | "aliasRegistry",
    target: ResultShareRegistrySavedView[],
  ) => {
    if (!Object.prototype.hasOwnProperty.call(presetEnvelope, envelopeKey)) {
      return;
    }
    const value = presetEnvelope[envelopeKey];
    if (!Array.isArray(value)) {
      errors.push(`Import payload.presets.${envelopeKey} must be an array.`);
      return;
    }
    value.forEach((item, index) => {
      const normalized = sanitizeImportedSavedView(
        item,
        scope,
        warnings,
        errors,
        `Import payload.presets.${envelopeKey}[${index}]`,
      );
      if (!normalized) {
        invalidPresetCount += 1;
        return;
      }
      target.push(normalized);
    });
  };

  parseScope("grant_registry", "grantRegistry", sanitizedGrantPresets);
  parseScope("alias_registry", "aliasRegistry", sanitizedAliasPresets);

  const validPresetCount = sanitizedGrantPresets.length + sanitizedAliasPresets.length;
  const fatalErrors = errors.some((message) =>
    message.includes("must") || message.includes("unsafe") || message.includes("not valid"),
  );

  return {
    schemaVersion,
    validPresetCount,
    invalidPresetCount,
    grantPresetCount: sanitizedGrantPresets.length,
    aliasPresetCount: sanitizedAliasPresets.length,
    warnings,
    errors,
    canApply: !fatalErrors && validPresetCount > 0,
    importedScopes: {
      grantRegistry: grantScopePresent,
      aliasRegistry: aliasScopePresent,
    },
    presets: {
      grantRegistry: sanitizedGrantPresets,
      aliasRegistry: sanitizedAliasPresets,
    },
  };
}

function prepareImportedPresetsForMerge(
  existingPresets: ResultShareRegistrySavedView[],
  importedPresets: ResultShareRegistrySavedView[],
): ResultShareRegistrySavedView[] {
  const existingIds = new Set(existingPresets.map((preset) => preset.id));
  const existingNames = new Set(existingPresets.map((preset) => preset.name));
  const merged = [...existingPresets];

  for (const preset of importedPresets) {
    let nextPreset = preset;
    if (existingIds.has(preset.id)) {
      nextPreset = {
        ...preset,
        id: generateImportedPresetId(existingIds, preset.id),
        name: generateImportedPresetName(existingNames, preset.name),
      };
    } else {
      existingIds.add(preset.id);
      existingNames.add(preset.name);
    }
    merged.push(nextPreset);
  }

  return merged;
}

function prepareImportedPresetsForReplace(
  importedPresets: ResultShareRegistrySavedView[],
): ResultShareRegistrySavedView[] {
  const existingIds = new Set<string>();
  const existingNames = new Set<string>();
  return importedPresets.map((preset) => {
    let nextPreset = preset;
    if (existingIds.has(preset.id)) {
      nextPreset = {
        ...preset,
        id: generateImportedPresetId(existingIds, preset.id),
        name: generateImportedPresetName(existingNames, preset.name),
      };
    } else {
      existingIds.add(preset.id);
      existingNames.add(preset.name);
    }
    return nextPreset;
  });
}

export function applyResultShareRegistryPresetImport(
  store: ResultShareRegistrySavedViewStoreState,
  preview: ResultShareRegistryPresetImportPreview,
  mode: ResultShareRegistryPresetImportMode,
): ResultShareRegistryPresetImportApplyResult {
  const nextGrantPresets =
    mode === "replace"
      ? preview.importedScopes.grantRegistry
        ? prepareImportedPresetsForReplace(preview.presets.grantRegistry)
        : store.grantPresets
      : prepareImportedPresetsForMerge(store.grantPresets, preview.presets.grantRegistry);
  const nextAliasPresets =
    mode === "replace"
      ? preview.importedScopes.aliasRegistry
        ? prepareImportedPresetsForReplace(preview.presets.aliasRegistry)
        : store.aliasPresets
      : prepareImportedPresetsForMerge(store.aliasPresets, preview.presets.aliasRegistry);

  const provisionalStore: ResultShareRegistrySavedViewStoreState = {
    grantPresets: nextGrantPresets,
    aliasPresets: nextAliasPresets,
    defaultPresetId: store.defaultPresetId,
  };
  const defaultPresetStillExists = Boolean(
    provisionalStore.defaultPresetId && findSavedViewById(provisionalStore, provisionalStore.defaultPresetId),
  );

  return {
    store: {
      ...provisionalStore,
      defaultPresetId: defaultPresetStillExists ? provisionalStore.defaultPresetId : null,
    },
    importedGrantCount: preview.presets.grantRegistry.length,
    importedAliasCount: preview.presets.aliasRegistry.length,
    defaultPresetCleared: Boolean(provisionalStore.defaultPresetId) && !defaultPresetStillExists,
  };
}

function findSavedViewById(
  store: ResultShareRegistrySavedViewStoreState,
  presetId: string | null,
): ResultShareRegistrySavedView | null {
  if (!presetId) {
    return null;
  }
  return (
    store.grantPresets.find((preset) => preset.id === presetId) ??
    store.aliasPresets.find((preset) => preset.id === presetId) ??
    null
  );
}

function replaceSavedView(
  presets: ResultShareRegistrySavedView[],
  nextPreset: ResultShareRegistrySavedView,
): ResultShareRegistrySavedView[] {
  return presets.map((preset) => (preset.id === nextPreset.id ? nextPreset : preset));
}

function looksUnsafeFieldName(key: string): boolean {
  return unsafeFieldPattern.test(key);
}

export function hasUnsafePresetFieldName(key: string): boolean {
  return looksUnsafeFieldName(key);
}

export function redactUnsafeImportIssueDetails(detail: string | null | undefined): string | null {
  if (!detail) {
    return null;
  }
  return looksUnsafeFieldName(detail) ? "[redacted]" : detail;
}

export function sanitizePresetAuditDetails(detail: string | null | undefined): string | null {
  if (!detail) {
    return null;
  }
  return redactUnsafeImportIssueDetails(detail);
}

function isAuditActionType(
  value: unknown,
): value is ResultShareRegistryPresetLocalAuditActionType {
  return (
    typeof value === "string" &&
    presetLocalAuditActionTypes.includes(
      value as ResultShareRegistryPresetLocalAuditActionType,
    )
  );
}

function isAuditStatus(
  value: unknown,
): value is ResultShareRegistryPresetLocalAuditStatus {
  return value === "success" || value === "warning" || value === "failed";
}

function normalizeLocalAuditEvent(
  value: unknown,
): ResultShareRegistryPresetLocalAuditEvent | null {
  if (!isRecord(value)) {
    return null;
  }
  const id = typeof value.id === "string" ? value.id.trim() : "";
  const occurredAt = typeof value.occurredAt === "string" ? value.occurredAt.trim() : "";
  const summary = typeof value.summary === "string" ? value.summary.trim() : "";
  if (!id || !occurredAt || !summary) {
    return null;
  }
  if (!isAuditActionType(value.actionType) || !isAuditStatus(value.status)) {
    return null;
  }
  const scope =
    value.scope === null || value.scope === undefined
      ? null
      : value.scope === "storage" ||
          (typeof value.scope === "string" && normalizeScope(value.scope))
        ? (value.scope as ResultShareRegistrySavedViewScope | "storage")
        : null;
  const presetId = typeof value.presetId === "string" ? value.presetId.trim() : null;
  const presetName = typeof value.presetName === "string" ? value.presetName.trim() : null;
  return {
    id,
    occurredAt,
    actionType: value.actionType,
    scope,
    presetId: presetId || null,
    presetName: presetName || null,
    status: value.status,
    summary,
    safeDetails: sanitizePresetAuditDetails(
      typeof value.safeDetails === "string" ? value.safeDetails : null,
    ),
  };
}

export function createPresetAuditEvent(
  actionType: ResultShareRegistryPresetLocalAuditActionType,
  status: ResultShareRegistryPresetLocalAuditStatus,
  summary: string,
  options?: {
    scope?: ResultShareRegistrySavedViewScope | "storage" | null;
    presetId?: string | null;
    presetName?: string | null;
    safeDetails?: string | null;
    occurredAt?: string;
    id?: string;
  },
): ResultShareRegistryPresetLocalAuditEvent {
  return {
    id: options?.id ?? createAuditEventId(),
    occurredAt: options?.occurredAt ?? new Date().toISOString(),
    actionType,
    scope: options?.scope ?? null,
    presetId: options?.presetId?.trim() || null,
    presetName: options?.presetName?.trim() || null,
    status,
    summary: summary.trim(),
    safeDetails: sanitizePresetAuditDetails(options?.safeDetails ?? null),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function loadResultShareRegistryPresetAuditEvents(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetLocalAuditLoadResult {
  if (!storage) {
    return {
      events: [],
      storageWarning: null,
    };
  }
  let raw: string | null = null;
  try {
    raw = storage.getItem(RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY);
  } catch {
    return {
      events: [],
      storageWarning: "Local preset audit storage could not be read.",
    };
  }
  if (!raw) {
    return {
      events: [],
      storageWarning: null,
    };
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return {
        events: [],
        storageWarning: "Local preset audit storage must contain an array.",
      };
    }
    const events = parsed
      .map((item) => normalizeLocalAuditEvent(item))
      .filter((item): item is ResultShareRegistryPresetLocalAuditEvent => item !== null)
      .slice(0, RESULT_SHARE_REGISTRY_LOCAL_AUDIT_MAX_EVENTS);
    return {
      events,
      storageWarning:
        events.length !== parsed.length
          ? "Some local audit entries were invalid and were ignored."
          : null,
    };
  } catch {
    return {
      events: [],
      storageWarning: "Local preset audit storage is not valid JSON.",
    };
  }
}

export function saveResultShareRegistryPresetAuditEvents(
  storage: Storage | null | undefined,
  events: ResultShareRegistryPresetLocalAuditEvent[],
): ResultShareRegistryPresetLocalAuditEvent[] {
  const normalizedEvents = events
    .map((event) => normalizeLocalAuditEvent(event))
    .filter((event): event is ResultShareRegistryPresetLocalAuditEvent => event !== null)
    .slice(0, RESULT_SHARE_REGISTRY_LOCAL_AUDIT_MAX_EVENTS);
  if (!storage) {
    return normalizedEvents;
  }
  storage.setItem(
    RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY,
    JSON.stringify(normalizedEvents),
  );
  return normalizedEvents;
}

export function appendResultShareRegistryPresetAuditEvent(
  storage: Storage | null | undefined,
  event: ResultShareRegistryPresetLocalAuditEvent,
): ResultShareRegistryPresetLocalAuditLoadResult {
  const current = loadResultShareRegistryPresetAuditEvents(storage);
  const nextEvents = [event, ...current.events].slice(
    0,
    RESULT_SHARE_REGISTRY_LOCAL_AUDIT_MAX_EVENTS,
  );
  return {
    events: saveResultShareRegistryPresetAuditEvents(storage, nextEvents),
    storageWarning: null,
  };
}

export function clearResultShareRegistryPresetAuditEvents(
  storage: Storage | null | undefined,
): void {
  if (!storage) {
    return;
  }
  storage.removeItem(RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY);
}

function createEmptyAuditActionCount(): Record<ResultShareRegistryPresetLocalAuditActionType, number> {
  return presetLocalAuditActionTypes.reduce(
    (counts, actionType) => ({
      ...counts,
      [actionType]: 0,
    }),
    {} as Record<ResultShareRegistryPresetLocalAuditActionType, number>,
  );
}

export function buildResultShareRegistryPresetAuditSummary(
  events: ResultShareRegistryPresetLocalAuditEvent[],
  options?: {
    storageWarning?: string | null;
  },
): ResultShareRegistryPresetLocalAuditSummary {
  const byActionType = createEmptyAuditActionCount();
  const byScope = {
    grant_registry: 0,
    alias_registry: 0,
    storage: 0,
    unscoped: 0,
  };
  let successCount = 0;
  let warningCount = 0;
  let failedCount = 0;

  for (const event of events) {
    byActionType[event.actionType] += 1;
    if (event.scope === "grant_registry") {
      byScope.grant_registry += 1;
    } else if (event.scope === "alias_registry") {
      byScope.alias_registry += 1;
    } else if (event.scope === "storage") {
      byScope.storage += 1;
    } else {
      byScope.unscoped += 1;
    }
    if (event.status === "success") {
      successCount += 1;
    } else if (event.status === "warning") {
      warningCount += 1;
    } else {
      failedCount += 1;
    }
  }

  const backupRelatedCount =
    byActionType.backup_created +
    byActionType.backup_restored +
    byActionType.preset_workspace_backup_created +
    byActionType.preset_workspace_backup_restored;
  const recoveryRelatedCount =
    byActionType.invalid_presets_discarded +
    byActionType.scope_reset +
    byActionType.all_presets_reset +
    byActionType.dangling_default_cleared +
    byActionType.backup_restored +
    byActionType.recovery_failed +
    byActionType.preset_workspace_backup_restored;
  const importRelatedCount =
    byActionType.import_dry_run +
    byActionType.import_merge +
    byActionType.import_replace +
    byActionType.validation_failed +
    byActionType.preset_workspace_import_dry_run +
    byActionType.preset_workspace_import_merge +
    byActionType.preset_workspace_import_replace +
    byActionType.preset_workspace_import_validation_failed;
  const exportRelatedCount =
    byActionType.export_created +
    byActionType.preset_workspace_export_created +
    byActionType.preset_workspace_health_report_exported_json +
    byActionType.preset_workspace_health_report_exported_markdown;

  return {
    totalEvents: events.length,
    successCount,
    warningCount,
    failedCount,
    lastEventAt: events[0]?.occurredAt ?? null,
    byActionType,
    byScope,
    recentEvents: events.slice(0, RESULT_SHARE_REGISTRY_LOCAL_AUDIT_RECENT_LIMIT),
    backupRelatedCount,
    recoveryRelatedCount,
    importRelatedCount,
    exportRelatedCount,
    storageWarning: options?.storageWarning ?? null,
  };
}

function createDefaultResultShareRegistryPresetWorkspaceState(
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  return {
    pinnedGrantPresetIds: [],
    pinnedAliasPresetIds: [],
    lastActivePresetScope: null,
    lastActivePresetId: null,
    collapsedSections: null,
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

function normalizeWorkspacePresetIds(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const seen = new Set<string>();
  const result: string[] = [];
  value.forEach((item) => {
    if (typeof item !== "string") {
      return;
    }
    const trimmed = item.trim();
    if (!trimmed || seen.has(trimmed)) {
      return;
    }
    seen.add(trimmed);
    result.push(trimmed);
  });
  return result;
}

function normalizeCollapsedSections(
  value: unknown,
): ResultShareRegistryPresetWorkspaceState["collapsedSections"] {
  if (!isRecord(value)) {
    return null;
  }
  return {
    pinnedGrantPresets: value.pinnedGrantPresets === true,
    pinnedAliasPresets: value.pinnedAliasPresets === true,
    recentGrantPresets: value.recentGrantPresets === true,
    recentAliasPresets: value.recentAliasPresets === true,
    recentActivity: value.recentActivity === true,
    storageHealth: value.storageHealth === true,
  };
}

function normalizeResultShareRegistryPresetWorkspaceState(
  value: unknown,
  options?: {
    allowMissingUpdatedAt?: boolean;
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState | null {
  if (!isRecord(value)) {
    return null;
  }
  const updatedAt = typeof value.updatedAt === "string" ? value.updatedAt.trim() : "";
  if (!updatedAt && !options?.allowMissingUpdatedAt) {
    return null;
  }
  return {
    pinnedGrantPresetIds: normalizeWorkspacePresetIds(value.pinnedGrantPresetIds),
    pinnedAliasPresetIds: normalizeWorkspacePresetIds(value.pinnedAliasPresetIds),
    lastActivePresetScope: normalizeScope(
      typeof value.lastActivePresetScope === "string" ||
        value.lastActivePresetScope === null ||
        value.lastActivePresetScope === undefined
        ? value.lastActivePresetScope
        : null,
    ),
    lastActivePresetId:
      typeof value.lastActivePresetId === "string" && value.lastActivePresetId.trim()
        ? value.lastActivePresetId.trim()
        : null,
    collapsedSections: normalizeCollapsedSections(value.collapsedSections),
    updatedAt: updatedAt || options?.now || new Date().toISOString(),
  };
}

export function loadResultShareRegistryPresetWorkspaceState(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetWorkspaceLoadResult {
  if (!storage) {
    return {
      state: createDefaultResultShareRegistryPresetWorkspaceState(),
      storageWarning: null,
      keyPresent: false,
    };
  }
  let raw: string | null = null;
  try {
    raw = storage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY);
  } catch {
    return {
      state: createDefaultResultShareRegistryPresetWorkspaceState(),
      storageWarning: "Local preset workspace state could not be read.",
      keyPresent: false,
    };
  }
  if (!raw) {
    return {
      state: createDefaultResultShareRegistryPresetWorkspaceState(),
      storageWarning: null,
      keyPresent: false,
    };
  }
  try {
    const parsed = JSON.parse(raw);
    const normalized = normalizeResultShareRegistryPresetWorkspaceState(parsed);
    if (!normalized) {
      return {
        state: createDefaultResultShareRegistryPresetWorkspaceState(),
        storageWarning: "Local preset workspace state is invalid and fell back to defaults.",
        keyPresent: true,
      };
    }
    return {
      state: normalized,
      storageWarning: null,
      keyPresent: true,
    };
  } catch {
    return {
      state: createDefaultResultShareRegistryPresetWorkspaceState(),
      storageWarning: "Local preset workspace state is not valid JSON and fell back to defaults.",
      keyPresent: true,
    };
  }
}

export function persistResultShareRegistryPresetWorkspaceState(
  storage: Storage | null | undefined,
  state: ResultShareRegistryPresetWorkspaceState,
): ResultShareRegistryPresetWorkspaceState {
  const normalized =
    normalizeResultShareRegistryPresetWorkspaceState(state) ??
    createDefaultResultShareRegistryPresetWorkspaceState();
  if (!storage) {
    return normalized;
  }
  storage.setItem(
    RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY,
    JSON.stringify(normalized),
  );
  return normalized;
}

function classifyWorkspaceStateAgainstStore(
  workspaceState: ResultShareRegistryPresetWorkspaceState,
  store: ResultShareRegistrySavedViewStoreState,
): {
  stalePinnedGrantPresetIds: string[];
  stalePinnedAliasPresetIds: string[];
  lastActivePresetExists: boolean;
} {
  const grantPresetIds = new Set(store.grantPresets.map((preset) => preset.id));
  const aliasPresetIds = new Set(store.aliasPresets.map((preset) => preset.id));
  const lastActivePresetExists =
    workspaceState.lastActivePresetScope === "grant_registry"
      ? workspaceState.lastActivePresetId !== null &&
        grantPresetIds.has(workspaceState.lastActivePresetId)
      : workspaceState.lastActivePresetScope === "alias_registry"
        ? workspaceState.lastActivePresetId !== null &&
          aliasPresetIds.has(workspaceState.lastActivePresetId)
        : true;
  return {
    stalePinnedGrantPresetIds: workspaceState.pinnedGrantPresetIds.filter(
      (presetId) => !grantPresetIds.has(presetId),
    ),
    stalePinnedAliasPresetIds: workspaceState.pinnedAliasPresetIds.filter(
      (presetId) => !aliasPresetIds.has(presetId),
    ),
    lastActivePresetExists,
  };
}

function sanitizeImportedPresetWorkspaceState(
  value: unknown,
  warnings: string[],
  errors: string[],
  path: string,
): ResultShareRegistryPresetWorkspaceState | null {
  if (!isRecord(value)) {
    errors.push(`${path} must be an object.`);
    return null;
  }
  if (collectUnexpectedKeys(value, workspaceStateAllowedKeys, path, warnings, errors)) {
    return null;
  }
  if ("pinnedGrantPresetIds" in value && !Array.isArray(value.pinnedGrantPresetIds)) {
    errors.push(`${path}.pinnedGrantPresetIds must be an array of preset ids.`);
    return null;
  }
  if ("pinnedAliasPresetIds" in value && !Array.isArray(value.pinnedAliasPresetIds)) {
    errors.push(`${path}.pinnedAliasPresetIds must be an array of preset ids.`);
    return null;
  }
  if (
    "lastActivePresetScope" in value &&
    value.lastActivePresetScope !== null &&
    value.lastActivePresetScope !== undefined &&
    value.lastActivePresetScope !== "grant_registry" &&
    value.lastActivePresetScope !== "alias_registry"
  ) {
    errors.push(`${path}.lastActivePresetScope must be grant_registry, alias_registry, or null.`);
    return null;
  }
  if (
    "lastActivePresetId" in value &&
    value.lastActivePresetId !== null &&
    value.lastActivePresetId !== undefined &&
    typeof value.lastActivePresetId !== "string"
  ) {
    errors.push(`${path}.lastActivePresetId must be a string or null.`);
    return null;
  }
  if (
    "collapsedSections" in value &&
    value.collapsedSections !== null &&
    value.collapsedSections !== undefined
  ) {
    if (!isRecord(value.collapsedSections)) {
      errors.push(`${path}.collapsedSections must be an object or null.`);
      return null;
    }
    if (
      collectUnexpectedKeys(
        value.collapsedSections,
        workspaceCollapsedSectionAllowedKeys,
        `${path}.collapsedSections`,
        warnings,
        errors,
      )
    ) {
      return null;
    }
  }

  const normalized = normalizeResultShareRegistryPresetWorkspaceState(value, {
    allowMissingUpdatedAt: true,
  });
  if (!normalized) {
    errors.push(`${path} does not match the expected preset workspace shape.`);
    return null;
  }
  return normalized;
}

export function buildResultShareRegistryPresetWorkspaceExport(
  workspaceState: ResultShareRegistryPresetWorkspaceState,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceExportPayload {
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
    exportedAt: options?.now ?? new Date().toISOString(),
    app: "research-pulse-cn",
    source: "group-workspace-admin-web",
    workspaceState:
      normalizeResultShareRegistryPresetWorkspaceState(workspaceState, {
        allowMissingUpdatedAt: true,
        now: options?.now,
      }) ?? createDefaultResultShareRegistryPresetWorkspaceState(options),
  };
}

function buildPresetWorkspaceImportPreview(
  workspaceState: ResultShareRegistryPresetWorkspaceState | null,
  store: ResultShareRegistrySavedViewStoreState,
  warnings: string[],
  errors: string[],
  schemaVersion: string | null,
): ResultShareRegistryPresetWorkspaceImportPreview {
  const classification = workspaceState
    ? classifyWorkspaceStateAgainstStore(workspaceState, store)
    : {
        stalePinnedGrantPresetIds: [],
        stalePinnedAliasPresetIds: [],
        lastActivePresetExists: false,
      };
  const previewWarnings = [...warnings];
  if (classification.stalePinnedGrantPresetIds.length > 0) {
    previewWarnings.push(
      `Imported workspace state contains ${classification.stalePinnedGrantPresetIds.length} stale grant pin(s). Existing stale-pin cleanup can remove them after import.`,
    );
  }
  if (classification.stalePinnedAliasPresetIds.length > 0) {
    previewWarnings.push(
      `Imported workspace state contains ${classification.stalePinnedAliasPresetIds.length} stale alias pin(s). Existing stale-pin cleanup can remove them after import.`,
    );
  }
  if (workspaceState && !classification.lastActivePresetExists) {
    previewWarnings.push(
      "Imported workspace last-active preset does not exist locally and will be cleared on apply.",
    );
  }
  return {
    schemaVersion,
    valid: errors.length === 0,
    canApply: errors.length === 0,
    warnings: previewWarnings,
    errors,
    pinnedGrantPresetCount: workspaceState?.pinnedGrantPresetIds.length ?? 0,
    pinnedAliasPresetCount: workspaceState?.pinnedAliasPresetIds.length ?? 0,
    stalePinnedGrantPresetIds: classification.stalePinnedGrantPresetIds,
    stalePinnedAliasPresetIds: classification.stalePinnedAliasPresetIds,
    lastActivePresetExists: classification.lastActivePresetExists,
    workspaceState,
  };
}

export function parseResultShareRegistryPresetWorkspaceImport(
  raw: string,
  store: ResultShareRegistrySavedViewStoreState,
): ResultShareRegistryPresetWorkspaceImportPreview {
  const warnings: string[] = [];
  const errors: string[] = [];
  let parsed: unknown;

  try {
    parsed = JSON.parse(raw);
  } catch {
    return {
      schemaVersion: null,
      valid: false,
      canApply: false,
      warnings: [],
      errors: ["Import file is not valid JSON."],
      pinnedGrantPresetCount: 0,
      pinnedAliasPresetCount: 0,
      stalePinnedGrantPresetIds: [],
      stalePinnedAliasPresetIds: [],
      lastActivePresetExists: false,
      workspaceState: null,
    };
  }

  if (!isRecord(parsed)) {
    return {
      schemaVersion: null,
      valid: false,
      canApply: false,
      warnings: [],
      errors: ["Import file must contain a JSON object."],
      pinnedGrantPresetCount: 0,
      pinnedAliasPresetCount: 0,
      stalePinnedGrantPresetIds: [],
      stalePinnedAliasPresetIds: [],
      lastActivePresetExists: false,
      workspaceState: null,
    };
  }

  const schemaVersion =
    typeof parsed.schemaVersion === "string" ? parsed.schemaVersion : null;
  if (collectUnexpectedKeys(parsed, workspaceExportAllowedKeys, "payload", warnings, errors)) {
    return buildPresetWorkspaceImportPreview(null, store, warnings, errors, schemaVersion);
  }
  if (schemaVersion !== RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION) {
    errors.push(
      `Import schemaVersion must be ${RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION}.`,
    );
    return buildPresetWorkspaceImportPreview(null, store, warnings, errors, schemaVersion);
  }
  const workspaceState = sanitizeImportedPresetWorkspaceState(
    parsed.workspaceState,
    warnings,
    errors,
    "payload.workspaceState",
  );
  return buildPresetWorkspaceImportPreview(workspaceState, store, warnings, errors, schemaVersion);
}

function mergeWorkspaceCollapsedSections(
  current: ResultShareRegistryPresetWorkspaceState["collapsedSections"],
  incoming: ResultShareRegistryPresetWorkspaceState["collapsedSections"],
): ResultShareRegistryPresetWorkspaceState["collapsedSections"] {
  if (!current && !incoming) {
    return null;
  }
  return {
    pinnedGrantPresets: incoming?.pinnedGrantPresets ?? current?.pinnedGrantPresets ?? false,
    pinnedAliasPresets: incoming?.pinnedAliasPresets ?? current?.pinnedAliasPresets ?? false,
    recentGrantPresets: incoming?.recentGrantPresets ?? current?.recentGrantPresets ?? false,
    recentAliasPresets: incoming?.recentAliasPresets ?? current?.recentAliasPresets ?? false,
    recentActivity: incoming?.recentActivity ?? current?.recentActivity ?? false,
    storageHealth: incoming?.storageHealth ?? current?.storageHealth ?? false,
  };
}

export function applyResultShareRegistryPresetWorkspaceImport(
  currentState: ResultShareRegistryPresetWorkspaceState,
  preview: ResultShareRegistryPresetWorkspaceImportPreview,
  mode: ResultShareRegistryPresetImportMode,
  store: ResultShareRegistrySavedViewStoreState,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceImportApplyResult {
  const timestamp = options?.now ?? new Date().toISOString();
  const importedWorkspaceState = preview.workspaceState
    ? normalizeResultShareRegistryPresetWorkspaceState(preview.workspaceState, {
        allowMissingUpdatedAt: true,
        now: timestamp,
      })
    : null;
  if (!preview.canApply || !importedWorkspaceState) {
    return {
      workspaceState: currentState,
      stalePinnedGrantPresetIds: [],
      stalePinnedAliasPresetIds: [],
      lastActivePresetCleared: false,
    };
  }

  const nextWorkspaceState =
    mode === "merge"
      ? {
          pinnedGrantPresetIds: [
            ...currentState.pinnedGrantPresetIds,
            ...importedWorkspaceState.pinnedGrantPresetIds.filter(
              (presetId) => !currentState.pinnedGrantPresetIds.includes(presetId),
            ),
          ],
          pinnedAliasPresetIds: [
            ...currentState.pinnedAliasPresetIds,
            ...importedWorkspaceState.pinnedAliasPresetIds.filter(
              (presetId) => !currentState.pinnedAliasPresetIds.includes(presetId),
            ),
          ],
          lastActivePresetScope:
            classifyWorkspaceStateAgainstStore(importedWorkspaceState, store).lastActivePresetExists &&
            importedWorkspaceState.lastActivePresetId
              ? importedWorkspaceState.lastActivePresetScope
              : currentState.lastActivePresetScope,
          lastActivePresetId:
            classifyWorkspaceStateAgainstStore(importedWorkspaceState, store).lastActivePresetExists &&
            importedWorkspaceState.lastActivePresetId
              ? importedWorkspaceState.lastActivePresetId
              : currentState.lastActivePresetId,
          collapsedSections: mergeWorkspaceCollapsedSections(
            currentState.collapsedSections,
            importedWorkspaceState.collapsedSections,
          ),
          updatedAt: timestamp,
        }
      : {
          ...importedWorkspaceState,
          updatedAt: timestamp,
        };

  const classification = classifyWorkspaceStateAgainstStore(nextWorkspaceState, store);
  const resultWorkspaceState =
    classification.lastActivePresetExists
      ? nextWorkspaceState
      : {
          ...nextWorkspaceState,
          lastActivePresetScope: null,
          lastActivePresetId: null,
          updatedAt: timestamp,
        };

  return {
    workspaceState: resultWorkspaceState,
    stalePinnedGrantPresetIds: classification.stalePinnedGrantPresetIds,
    stalePinnedAliasPresetIds: classification.stalePinnedAliasPresetIds,
    lastActivePresetCleared:
      nextWorkspaceState.lastActivePresetId !== null && !classification.lastActivePresetExists,
  };
}

function normalizeResultShareRegistryPresetWorkspaceBackupSnapshot(
  value: unknown,
): ResultShareRegistryPresetWorkspaceBackupSnapshot | null {
  if (!isRecord(value)) {
    return null;
  }
  const schemaVersion =
    typeof value.schemaVersion === "string" ? value.schemaVersion.trim() : "";
  const createdAt = typeof value.createdAt === "string" ? value.createdAt.trim() : "";
  const reason = typeof value.reason === "string" ? value.reason.trim() : "";
  if (
    schemaVersion !== RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION ||
    !createdAt ||
    !reason
  ) {
    return null;
  }
  const workspaceState = normalizeResultShareRegistryPresetWorkspaceState(value.workspaceState, {
    allowMissingUpdatedAt: true,
    now: createdAt,
  });
  if (!workspaceState) {
    return null;
  }
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION,
    createdAt,
    reason,
    workspaceState,
  };
}

export function createResultShareRegistryPresetWorkspaceBackup(
  workspaceState: ResultShareRegistryPresetWorkspaceState,
  reason: string,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceBackupSnapshot {
  const createdAt = options?.now ?? new Date().toISOString();
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION,
    createdAt,
    reason,
    workspaceState:
      normalizeResultShareRegistryPresetWorkspaceState(workspaceState, {
        allowMissingUpdatedAt: true,
        now: createdAt,
      }) ?? createDefaultResultShareRegistryPresetWorkspaceState({ now: createdAt }),
  };
}

export function persistResultShareRegistryPresetWorkspaceBackup(
  storage: Storage | null | undefined,
  backup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null,
): ResultShareRegistryPresetWorkspaceBackupSnapshot | null {
  if (!storage) {
    return backup;
  }
  if (!backup) {
    storage.removeItem(RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY);
    return null;
  }
  const normalized = normalizeResultShareRegistryPresetWorkspaceBackupSnapshot(backup);
  if (!normalized) {
    storage.removeItem(RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY);
    return null;
  }
  storage.setItem(
    RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY,
    JSON.stringify(normalized),
  );
  return normalized;
}

export function loadResultShareRegistryPresetWorkspaceBackup(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetWorkspaceBackupSnapshot | null {
  if (!storage) {
    return null;
  }
  let raw: string | null = null;
  try {
    raw = storage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY);
  } catch {
    return null;
  }
  if (!raw) {
    return null;
  }
  try {
    return normalizeResultShareRegistryPresetWorkspaceBackupSnapshot(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function restoreResultShareRegistryPresetWorkspaceBackup(
  backup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null,
): ResultShareRegistryPresetWorkspaceState | null {
  if (!backup) {
    return null;
  }
  const normalized = normalizeResultShareRegistryPresetWorkspaceBackupSnapshot(backup);
  return normalized?.workspaceState ?? null;
}

export function resetResultShareRegistryPresetWorkspaceState(
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  return createDefaultResultShareRegistryPresetWorkspaceState(options);
}

export function pinResultShareRegistryPresetWorkspacePreset(
  state: ResultShareRegistryPresetWorkspaceState,
  scope: ResultShareRegistrySavedViewScope,
  presetId: string,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  const trimmedId = presetId.trim();
  if (!trimmedId) {
    return state;
  }
  const key =
    scope === "grant_registry" ? "pinnedGrantPresetIds" : "pinnedAliasPresetIds";
  const nextIds = state[key].includes(trimmedId) ? state[key] : [...state[key], trimmedId];
  return {
    ...state,
    [key]: nextIds,
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function unpinResultShareRegistryPresetWorkspacePreset(
  state: ResultShareRegistryPresetWorkspaceState,
  scope: ResultShareRegistrySavedViewScope,
  presetId: string,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  const key =
    scope === "grant_registry" ? "pinnedGrantPresetIds" : "pinnedAliasPresetIds";
  return {
    ...state,
    [key]: state[key].filter((item) => item !== presetId),
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function movePinnedResultShareRegistryPresetWorkspacePreset(
  state: ResultShareRegistryPresetWorkspaceState,
  scope: ResultShareRegistrySavedViewScope,
  presetId: string,
  direction: "up" | "down",
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  const key =
    scope === "grant_registry" ? "pinnedGrantPresetIds" : "pinnedAliasPresetIds";
  const nextIds = [...state[key]];
  const index = nextIds.indexOf(presetId);
  if (index < 0) {
    return state;
  }
  const swapIndex = direction === "up" ? index - 1 : index + 1;
  if (swapIndex < 0 || swapIndex >= nextIds.length) {
    return state;
  }
  [nextIds[index], nextIds[swapIndex]] = [nextIds[swapIndex], nextIds[index]];
  return {
    ...state,
    [key]: nextIds,
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function clearAllResultShareRegistryPresetWorkspacePins(
  state: ResultShareRegistryPresetWorkspaceState,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  return {
    ...state,
    pinnedGrantPresetIds: [],
    pinnedAliasPresetIds: [],
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function setResultShareRegistryPresetWorkspaceLastActive(
  state: ResultShareRegistryPresetWorkspaceState,
  scope: ResultShareRegistrySavedViewScope | null,
  presetId: string | null,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  return {
    ...state,
    lastActivePresetScope: scope,
    lastActivePresetId: presetId?.trim() || null,
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function syncResultShareRegistryPresetWorkspaceStateWithStore(
  state: ResultShareRegistryPresetWorkspaceState,
  store: ResultShareRegistrySavedViewStoreState,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceState {
  const existingGrantIds = new Set(store.grantPresets.map((preset) => preset.id));
  const existingAliasIds = new Set(store.aliasPresets.map((preset) => preset.id));
  const lastActiveStillExists =
    state.lastActivePresetScope === "grant_registry"
      ? state.lastActivePresetId !== null && existingGrantIds.has(state.lastActivePresetId)
      : state.lastActivePresetScope === "alias_registry"
        ? state.lastActivePresetId !== null && existingAliasIds.has(state.lastActivePresetId)
        : false;

  return {
    ...state,
    lastActivePresetScope: lastActiveStillExists ? state.lastActivePresetScope : null,
    lastActivePresetId: lastActiveStillExists ? state.lastActivePresetId : null,
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function cleanStaleResultShareRegistryPresetWorkspacePins(
  state: ResultShareRegistryPresetWorkspaceState,
  store: ResultShareRegistrySavedViewStoreState,
  options?: {
    now?: string;
  },
): {
  state: ResultShareRegistryPresetWorkspaceState;
  removedGrantPinIds: string[];
  removedAliasPinIds: string[];
} {
  const existingGrantIds = new Set(store.grantPresets.map((preset) => preset.id));
  const existingAliasIds = new Set(store.aliasPresets.map((preset) => preset.id));
  const removedGrantPinIds = state.pinnedGrantPresetIds.filter((id) => !existingGrantIds.has(id));
  const removedAliasPinIds = state.pinnedAliasPresetIds.filter((id) => !existingAliasIds.has(id));
  return {
    state: {
      ...state,
      pinnedGrantPresetIds: state.pinnedGrantPresetIds.filter((id) => existingGrantIds.has(id)),
      pinnedAliasPresetIds: state.pinnedAliasPresetIds.filter((id) => existingAliasIds.has(id)),
      updatedAt: options?.now ?? new Date().toISOString(),
    },
    removedGrantPinIds,
    removedAliasPinIds,
  };
}

function sortSavedViewSummariesByUpdatedAt(
  presets: ResultShareRegistrySavedViewSummary[],
): ResultShareRegistrySavedViewSummary[] {
  return [...presets].sort((left, right) => {
    const timestampCompare = right.updatedAt.localeCompare(left.updatedAt);
    if (timestampCompare !== 0) {
      return timestampCompare;
    }
    return left.id.localeCompare(right.id);
  });
}

export function buildResultShareRegistryPresetWorkspaceViewModel(
  summaries: {
    grantPresets: ResultShareRegistrySavedViewSummary[];
    aliasPresets: ResultShareRegistrySavedViewSummary[];
    defaultPreset: ResultShareRegistrySavedViewSummary | null;
  },
  workspaceState: ResultShareRegistryPresetWorkspaceState,
  auditSummary: ResultShareRegistryPresetLocalAuditSummary,
  diagnostics: ResultShareRegistryPresetStorageDiagnostics,
  lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null,
  workspaceBackup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null,
): ResultShareRegistryPresetWorkspaceViewModel {
  const grantById = new Map(summaries.grantPresets.map((preset) => [preset.id, preset]));
  const aliasById = new Map(summaries.aliasPresets.map((preset) => [preset.id, preset]));
  const pinnedGrantPresets = workspaceState.pinnedGrantPresetIds
    .map((presetId) => grantById.get(presetId) ?? null)
    .filter((preset): preset is ResultShareRegistrySavedViewSummary => preset !== null);
  const pinnedAliasPresets = workspaceState.pinnedAliasPresetIds
    .map((presetId) => aliasById.get(presetId) ?? null)
    .filter((preset): preset is ResultShareRegistrySavedViewSummary => preset !== null);
  const staleGrantPinIds = workspaceState.pinnedGrantPresetIds.filter((presetId) => !grantById.has(presetId));
  const staleAliasPinIds = workspaceState.pinnedAliasPresetIds.filter((presetId) => !aliasById.has(presetId));
  const recentGrantPresets = sortSavedViewSummariesByUpdatedAt(summaries.grantPresets).slice(0, 3);
  const recentAliasPresets = sortSavedViewSummariesByUpdatedAt(summaries.aliasPresets).slice(0, 3);
  const lastActivePreset =
    workspaceState.lastActivePresetScope === "grant_registry"
      ? grantById.get(workspaceState.lastActivePresetId ?? "") ?? null
      : workspaceState.lastActivePresetScope === "alias_registry"
        ? aliasById.get(workspaceState.lastActivePresetId ?? "") ?? null
        : null;

  return {
    overviewSummary: [
      { label: "Grant presets", value: summaries.grantPresets.length, hint: null },
      { label: "Alias presets", value: summaries.aliasPresets.length, hint: null },
      { label: "Pinned grants", value: pinnedGrantPresets.length, hint: null },
      { label: "Pinned aliases", value: pinnedAliasPresets.length, hint: null },
      { label: "Local audit events", value: auditSummary.totalEvents, hint: null },
      {
        label: "Storage health",
        value: diagnostics.errorCount + diagnostics.warningCount,
        hint:
          diagnostics.errorCount + diagnostics.warningCount > 0
            ? "Warnings and errors in local preset storage"
            : "No current storage issues",
      },
    ],
    lastActivePresetLabel: lastActivePreset
      ? `${lastActivePreset.scope === "grant_registry" ? "Grant" : "Alias"} preset · ${lastActivePreset.name}`
      : null,
    pinnedGrantPresets,
    pinnedAliasPresets,
    recentGrantPresets,
    recentAliasPresets,
    staleGrantPinIds,
    staleAliasPinIds,
    recentActivity: auditSummary.recentEvents.slice(0, 5),
    storageHealth: {
      issueCount: diagnostics.warningCount + diagnostics.errorCount,
      lastBackupLabel: lastGoodBackup
        ? `${lastGoodBackup.createdAt} · ${lastGoodBackup.reason}`
        : "No local backup stored",
      workspaceBackupLabel: workspaceBackup
        ? `${workspaceBackup.createdAt} · ${workspaceBackup.reason}`
        : "No workspace backup stored",
      auditWarning: auditSummary.storageWarning,
      workspaceWarning: diagnostics.workspaceStateWarning,
      latestValidationAt: diagnostics.latestValidationAt,
    },
  };
}

const DEFAULT_PRESET_WORKSPACE_HEALTH_STATUS_THRESHOLDS = {
  healthyMin: 90,
  attentionMin: 70,
  riskMin: 40,
  criticalMin: 0,
} as const;

const DEFAULT_PRESET_WORKSPACE_HEALTH_RECOMMENDATION_VISIBILITY = {
  showInfo: true,
  showWarnings: true,
  showErrors: true,
  showCritical: true,
} as const;

const DEFAULT_PRESET_WORKSPACE_HEALTH_PENALTY_OVERRIDES: Record<
  ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey,
  number
> = {
  storageInvalidJson: 40,
  workspaceStateWarning: 15,
  unsafeFieldDetected: 40,
  invalidSchemaVersion: 25,
  danglingDefaultPreset: 10,
  stalePinnedPreset: 5,
  allPinnedPresetsStale: 15,
  missingPresetBackup: 5,
  missingWorkspaceBackup: 5,
  corruptedAuditHistory: 10,
  recentFailedImport: 5,
  recentFailedRecovery: 5,
  noSavedPresets: 5,
  invalidDrilldownContext: 10,
  importPreviewHasErrors: 15,
};

function isIntegerString(value: string): boolean {
  return /^-?\d+$/.test(value.trim());
}

function parseDraftInteger(
  value: string,
  path: string,
  errors: string[],
): number | null {
  const trimmed = value.trim();
  if (!isIntegerString(trimmed)) {
    errors.push(`${path} must be an integer.`);
    return null;
  }
  return Number.parseInt(trimmed, 10);
}

export function getDefaultPresetWorkspaceHealthThresholdPreferences(
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceHealthThresholdPreferences {
  return {
    statusThresholds: {
      ...DEFAULT_PRESET_WORKSPACE_HEALTH_STATUS_THRESHOLDS,
    },
    findingPenaltyOverrides: {},
    recommendationVisibility: {
      ...DEFAULT_PRESET_WORKSPACE_HEALTH_RECOMMENDATION_VISIBILITY,
    },
    updatedAt: options?.now ?? new Date().toISOString(),
  };
}

export function createPresetWorkspaceHealthThresholdDraft(
  preferences?: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
): ResultShareRegistryPresetWorkspaceHealthThresholdDraft {
  const source = preferences ?? getDefaultPresetWorkspaceHealthThresholdPreferences();
  return {
    statusThresholds: {
      healthyMin: String(source.statusThresholds.healthyMin),
      attentionMin: String(source.statusThresholds.attentionMin),
      riskMin: String(source.statusThresholds.riskMin),
      criticalMin: String(source.statusThresholds.criticalMin),
    },
    findingPenaltyOverrides: Object.fromEntries(
      Object.entries(source.findingPenaltyOverrides).map(([key, value]) => [key, String(value)]),
    ) as ResultShareRegistryPresetWorkspaceHealthThresholdDraft["findingPenaltyOverrides"],
    recommendationVisibility: {
      ...source.recommendationVisibility,
    },
  };
}

function normalizeThresholdVisibility(
  value: unknown,
): ResultShareRegistryPresetWorkspaceHealthThresholdPreferences["recommendationVisibility"] {
  if (!isRecord(value)) {
    return {
      ...DEFAULT_PRESET_WORKSPACE_HEALTH_RECOMMENDATION_VISIBILITY,
    };
  }
  return {
    showInfo: value.showInfo !== false,
    showWarnings: value.showWarnings !== false,
    showErrors: value.showErrors !== false,
    showCritical: value.showCritical !== false,
  };
}

function sanitizePenaltyOverridesRecord(
  value: unknown,
  warnings: string[],
  errors: string[],
  path: string,
): Partial<Record<ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey, number>> {
  if (value == null) {
    return {};
  }
  if (!isRecord(value)) {
    errors.push(`${path} must be an object when provided.`);
    return {};
  }
  const result: Partial<
    Record<ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey, number>
  > = {};
  for (const [rawKey, rawValue] of Object.entries(value)) {
    if (!(rawKey in DEFAULT_PRESET_WORKSPACE_HEALTH_PENALTY_OVERRIDES)) {
      warnings.push(`${path}.${rawKey} is not a supported penalty override and was ignored.`);
      continue;
    }
    if (typeof rawValue !== "number" || !Number.isInteger(rawValue)) {
      errors.push(`${path}.${rawKey} must be an integer.`);
      continue;
    }
    if (rawValue < 0 || rawValue > 100) {
      errors.push(`${path}.${rawKey} must be between 0 and 100.`);
      continue;
    }
    result[rawKey as ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey] = rawValue;
  }
  return result;
}

function normalizePresetWorkspaceHealthThresholdPreferences(
  value: unknown,
  options?: {
    allowMissingUpdatedAt?: boolean;
    now?: string;
  },
): {
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences | null;
  warnings: string[];
  errors: string[];
} {
  const warnings: string[] = [];
  const errors: string[] = [];
  if (!isRecord(value)) {
    return {
      preferences: null,
      warnings,
      errors: ["Threshold preferences must be an object."],
    };
  }
  if (
    collectUnexpectedKeys(
      value,
      workspaceHealthThresholdPreferencesAllowedKeys,
      "thresholdPreferences",
      warnings,
      errors,
    )
  ) {
    return { preferences: null, warnings, errors };
  }
  if (!isRecord(value.statusThresholds)) {
    errors.push("thresholdPreferences.statusThresholds must be an object.");
    return { preferences: null, warnings, errors };
  }
  if (
    collectUnexpectedKeys(
      value.statusThresholds,
      workspaceHealthThresholdStatusAllowedKeys,
      "thresholdPreferences.statusThresholds",
      warnings,
      errors,
    )
  ) {
    return { preferences: null, warnings, errors };
  }
  if (
    value.recommendationVisibility !== undefined &&
    value.recommendationVisibility !== null &&
    !isRecord(value.recommendationVisibility)
  ) {
    errors.push("thresholdPreferences.recommendationVisibility must be an object.");
    return { preferences: null, warnings, errors };
  }
  if (
    isRecord(value.recommendationVisibility) &&
    collectUnexpectedKeys(
      value.recommendationVisibility,
      workspaceHealthThresholdVisibilityAllowedKeys,
      "thresholdPreferences.recommendationVisibility",
      warnings,
      errors,
    )
  ) {
    return { preferences: null, warnings, errors };
  }
  const statusThresholds = value.statusThresholds as Record<string, unknown>;
  const healthyMin = statusThresholds.healthyMin;
  const attentionMin = statusThresholds.attentionMin;
  const riskMin = statusThresholds.riskMin;
  const criticalMin = statusThresholds.criticalMin;
  if (
    ![healthyMin, attentionMin, riskMin, criticalMin].every(
      (item) => typeof item === "number" && Number.isInteger(item),
    )
  ) {
    errors.push("All threshold values must be integers.");
    return { preferences: null, warnings, errors };
  }
  const normalizedHealthyMin = healthyMin as number;
  const normalizedAttentionMin = attentionMin as number;
  const normalizedRiskMin = riskMin as number;
  const normalizedCriticalMin = criticalMin as number;
  const thresholdValues = [
    normalizedHealthyMin,
    normalizedAttentionMin,
    normalizedRiskMin,
    normalizedCriticalMin,
  ];
  if (thresholdValues.some((item) => item < 0 || item > 100)) {
    errors.push("All threshold values must be within 0..100.");
  }
  if (normalizedCriticalMin !== 0) {
    errors.push("criticalMin must stay at 0 in v1.");
  }
  if (
    !(
      normalizedHealthyMin > normalizedAttentionMin &&
      normalizedAttentionMin > normalizedRiskMin &&
      normalizedRiskMin > normalizedCriticalMin
    )
  ) {
    errors.push("Thresholds must satisfy healthyMin > attentionMin > riskMin > criticalMin.");
  }
  const updatedAt = typeof value.updatedAt === "string" ? value.updatedAt.trim() : "";
  if (!updatedAt && !options?.allowMissingUpdatedAt) {
    errors.push("thresholdPreferences.updatedAt is required.");
  }
  const penaltyOverrides = sanitizePenaltyOverridesRecord(
    value.findingPenaltyOverrides,
    warnings,
    errors,
    "thresholdPreferences.findingPenaltyOverrides",
  );
  if (errors.length > 0) {
    return { preferences: null, warnings, errors };
  }
  return {
    preferences: {
      statusThresholds: {
        healthyMin: normalizedHealthyMin,
        attentionMin: normalizedAttentionMin,
        riskMin: normalizedRiskMin,
        criticalMin: normalizedCriticalMin,
      },
      findingPenaltyOverrides: penaltyOverrides,
      recommendationVisibility: normalizeThresholdVisibility(value.recommendationVisibility),
      updatedAt: updatedAt || options?.now || new Date().toISOString(),
    },
    warnings,
    errors,
  };
}

export function validatePresetWorkspaceHealthThresholdPreferences(
  draft: ResultShareRegistryPresetWorkspaceHealthThresholdDraft,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult {
  const warnings: string[] = [];
  const errors: string[] = [];
  const healthyMin = parseDraftInteger(
    draft.statusThresholds.healthyMin,
    "statusThresholds.healthyMin",
    errors,
  );
  const attentionMin = parseDraftInteger(
    draft.statusThresholds.attentionMin,
    "statusThresholds.attentionMin",
    errors,
  );
  const riskMin = parseDraftInteger(draft.statusThresholds.riskMin, "statusThresholds.riskMin", errors);
  const criticalMin = parseDraftInteger(
    draft.statusThresholds.criticalMin,
    "statusThresholds.criticalMin",
    errors,
  );
  const parsedThresholds = [healthyMin, attentionMin, riskMin, criticalMin];
  if (parsedThresholds.every((item) => item !== null)) {
    const values = parsedThresholds as number[];
    if (values.some((item) => item < 0 || item > 100)) {
      errors.push("Threshold values must be within 0..100.");
    }
    if (criticalMin !== 0) {
      errors.push("Critical minimum stays fixed at 0 in v1.");
    }
    if (!(healthyMin! > attentionMin! && attentionMin! > riskMin! && riskMin! > criticalMin!)) {
      errors.push("Thresholds must satisfy healthyMin > attentionMin > riskMin > criticalMin.");
    }
  }

  const normalizedPenaltyOverrides: Partial<
    Record<ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey, number>
  > = {};
  for (const [rawKey, rawValue] of Object.entries(draft.findingPenaltyOverrides)) {
    const trimmed = rawValue.trim();
    if (!trimmed) {
      continue;
    }
    if (!(rawKey in DEFAULT_PRESET_WORKSPACE_HEALTH_PENALTY_OVERRIDES)) {
      warnings.push(`findingPenaltyOverrides.${rawKey} is not supported and was ignored.`);
      continue;
    }
    const parsed = parseDraftInteger(trimmed, `findingPenaltyOverrides.${rawKey}`, errors);
    if (parsed === null) {
      continue;
    }
    if (parsed < 0 || parsed > 100) {
      errors.push(`findingPenaltyOverrides.${rawKey} must be within 0..100.`);
      continue;
    }
    normalizedPenaltyOverrides[rawKey as ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey] =
      parsed;
  }

  if (errors.length > 0 || parsedThresholds.some((item) => item === null)) {
    return {
      valid: false,
      warnings,
      errors,
      normalizedPreferences: null,
      previewStatusImpact: null,
    };
  }

  return {
    valid: true,
    warnings,
    errors,
    normalizedPreferences: {
      statusThresholds: {
        healthyMin: healthyMin!,
        attentionMin: attentionMin!,
        riskMin: riskMin!,
        criticalMin: criticalMin!,
      },
      findingPenaltyOverrides: normalizedPenaltyOverrides,
      recommendationVisibility: {
        ...draft.recommendationVisibility,
      },
      updatedAt: options?.now ?? new Date().toISOString(),
    },
    previewStatusImpact: null,
  };
}

export function loadPresetWorkspaceHealthThresholdPreferences(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetWorkspaceHealthThresholdLoadResult {
  if (!storage) {
    return {
      preferences: getDefaultPresetWorkspaceHealthThresholdPreferences(),
      storageWarning: null,
      keyPresent: false,
      source: "default",
    };
  }
  let raw: string | null = null;
  try {
    raw = storage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY);
  } catch {
    return {
      preferences: getDefaultPresetWorkspaceHealthThresholdPreferences(),
      storageWarning: "Local health threshold preferences could not be read.",
      keyPresent: false,
      source: "default",
    };
  }
  if (!raw) {
    return {
      preferences: getDefaultPresetWorkspaceHealthThresholdPreferences(),
      storageWarning: null,
      keyPresent: false,
      source: "default",
    };
  }
  try {
    const parsed = JSON.parse(raw);
    const normalized = normalizePresetWorkspaceHealthThresholdPreferences(parsed, {
      allowMissingUpdatedAt: true,
    });
    if (!normalized.preferences || normalized.errors.length > 0) {
      return {
        preferences: getDefaultPresetWorkspaceHealthThresholdPreferences(),
        storageWarning: "Local health threshold preferences are invalid and fell back to defaults.",
        keyPresent: true,
        source: "default",
      };
    }
    return {
      preferences: normalized.preferences,
      storageWarning:
        normalized.warnings.length > 0
          ? "Local health threshold preferences were normalized with warnings."
          : null,
      keyPresent: true,
      source: "local",
    };
  } catch {
    return {
      preferences: getDefaultPresetWorkspaceHealthThresholdPreferences(),
      storageWarning: "Local health threshold preferences are not valid JSON and fell back to defaults.",
      keyPresent: true,
      source: "default",
    };
  }
}

export function persistPresetWorkspaceHealthThresholdPreferences(
  storage: Storage | null | undefined,
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
): ResultShareRegistryPresetWorkspaceHealthThresholdPreferences {
  const normalized =
    normalizePresetWorkspaceHealthThresholdPreferences(preferences, {
      allowMissingUpdatedAt: true,
    }).preferences ?? getDefaultPresetWorkspaceHealthThresholdPreferences();
  if (!storage) {
    return normalized;
  }
  storage.setItem(
    RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY,
    JSON.stringify(normalized),
  );
  return normalized;
}

export function resetPresetWorkspaceHealthThresholdPreferences(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetWorkspaceHealthThresholdPreferences {
  if (storage) {
    storage.removeItem(RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY);
  }
  return getDefaultPresetWorkspaceHealthThresholdPreferences();
}

function buildPresetWorkspaceHealthThresholdSummary(
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
): string[] {
  const thresholds = preferences.statusThresholds;
  const penaltyKeys = Object.keys(preferences.findingPenaltyOverrides);
  return [
    `Healthy ${thresholds.healthyMin}-100`,
    `Attention ${thresholds.attentionMin}-${thresholds.healthyMin - 1}`,
    `Risk ${thresholds.riskMin}-${thresholds.attentionMin - 1}`,
    `Critical ${thresholds.criticalMin}-${thresholds.riskMin - 1}`,
    penaltyKeys.length > 0
      ? `Penalty overrides: ${penaltyKeys.length} local override(s)`
      : "Penalty overrides: default weights",
  ];
}

function classifyPresetWorkspaceHealthStatus(
  score: number,
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
): ResultShareRegistryPresetWorkspaceHealthStatus {
  if (score >= preferences.statusThresholds.healthyMin) {
    return "healthy";
  }
  if (score >= preferences.statusThresholds.attentionMin) {
    return "attention";
  }
  if (score >= preferences.statusThresholds.riskMin) {
    return "risk";
  }
  return "critical";
}

function getPresetWorkspaceHealthPenalty(
  preferences: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
  key: ResultShareRegistryPresetWorkspaceHealthPenaltyOverrideKey,
): number {
  return preferences.findingPenaltyOverrides[key] ?? DEFAULT_PRESET_WORKSPACE_HEALTH_PENALTY_OVERRIDES[key];
}

export function buildPresetWorkspaceHealthThresholdPreview(input: {
  currentScore: ResultShareRegistryPresetWorkspaceHealthScore;
  draftScore?: ResultShareRegistryPresetWorkspaceHealthScore | null;
}): ResultShareRegistryPresetWorkspaceHealthThresholdPreview {
  const previewScore = input.draftScore ?? input.currentScore;
  const scoreChanged = previewScore.score !== input.currentScore.score;
  const statusChanged = previewScore.status !== input.currentScore.status;
  return {
    currentScore: input.currentScore.score,
    currentStatus: input.currentScore.status,
    draftScore: previewScore.score,
    draftStatus: previewScore.status,
    scoreChanged,
    statusChanged,
    summary:
      statusChanged || scoreChanged
        ? `Preview would change health from ${input.currentScore.status} (${input.currentScore.score}) to ${previewScore.status} (${previewScore.score}).`
        : `Preview keeps health at ${input.currentScore.status} (${input.currentScore.score}).`,
  };
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function hasIntegrityIssue(
  report: ResultShareRegistryPresetIntegrityReport,
  code: ResultShareRegistryPresetIntegrityIssueCode,
): boolean {
  return report.issues.some((issue) => issue.code === code);
}

function countRecentFailedAuditEvents(
  summary: ResultShareRegistryPresetLocalAuditSummary,
  actionTypes: ResultShareRegistryPresetLocalAuditActionType[],
): number {
  const actionTypeSet = new Set(actionTypes);
  return summary.recentEvents.filter(
    (event) => event.status === "failed" && actionTypeSet.has(event.actionType),
  ).length;
}

export function formatPresetWorkspaceHealthStatus(
  status: ResultShareRegistryPresetWorkspaceHealthStatus,
): string {
  if (status === "healthy") {
    return "Healthy";
  }
  if (status === "attention") {
    return "Attention";
  }
  if (status === "risk") {
    return "Risk";
  }
  return "Critical";
}

export function buildResultShareRegistryPresetWorkspaceHealthScore(input: {
  store: ResultShareRegistrySavedViewStoreState;
  integrityReport: ResultShareRegistryPresetIntegrityReport;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
  lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null;
  workspaceBackup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null;
  workspaceState: ResultShareRegistryPresetWorkspaceState;
  auditSummary: ResultShareRegistryPresetLocalAuditSummary;
  workspaceImportPreview: ResultShareRegistryPresetWorkspaceImportPreview | null;
  thresholdPreferences?: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences;
  thresholdPreferenceSource?: "default" | "local";
  thresholdStorageWarning?: string | null;
  checkedAt?: string;
}): ResultShareRegistryPresetWorkspaceHealthScore {
  const checkedAt = input.checkedAt ?? new Date().toISOString();
  const thresholdPreferences =
    input.thresholdPreferences ?? getDefaultPresetWorkspaceHealthThresholdPreferences({ now: checkedAt });
  const thresholdPreferenceSource = input.thresholdPreferenceSource ?? "default";
  const thresholdWarnings = input.thresholdStorageWarning ? [input.thresholdStorageWarning] : [];
  const classification = classifyWorkspaceStateAgainstStore(input.workspaceState, input.store);
  const totalPresetCount =
    input.store.grantPresets.length + input.store.aliasPresets.length;
  const totalPinnedCount =
    input.workspaceState.pinnedGrantPresetIds.length +
    input.workspaceState.pinnedAliasPresetIds.length;
  const stalePinnedCount =
    classification.stalePinnedGrantPresetIds.length +
    classification.stalePinnedAliasPresetIds.length;
  const validPinnedCount = totalPinnedCount - stalePinnedCount;
  const importFailureCount = countRecentFailedAuditEvents(input.auditSummary, [
    "validation_failed",
    "import_dry_run",
    "import_merge",
    "import_replace",
    "preset_workspace_import_validation_failed",
    "preset_workspace_import_dry_run",
    "preset_workspace_import_merge",
    "preset_workspace_import_replace",
  ]);
  const recoveryFailureCount = countRecentFailedAuditEvents(input.auditSummary, [
    "recovery_failed",
    "backup_restored",
    "preset_workspace_backup_restored",
  ]);
  const breakdown = {
    storageIntegrity: 100,
    presetValidity: 100,
    pinnedPresetHygiene: 100,
    backupReadiness: 100,
    auditReliability: 100,
    importExportSafety: 100,
    drilldownContextCompleteness: 100,
  };
  let score = 100;
  const findings: ResultShareRegistryPresetWorkspaceHealthFinding[] = [];
  const recommendations = new Map<
    ResultShareRegistryPresetWorkspaceHealthRecommendation["kind"],
    ResultShareRegistryPresetWorkspaceHealthRecommendation
  >();

  const applyPenalty = (
    key: keyof typeof breakdown,
    amount: number,
  ): void => {
    score -= amount;
    breakdown[key] = clampScore(breakdown[key] - amount);
  };

  const addFinding = (
    finding: ResultShareRegistryPresetWorkspaceHealthFinding,
  ): void => {
    if (
      findings.some(
        (existing) =>
          existing.code === finding.code &&
          existing.summary === finding.summary &&
          existing.detail === finding.detail,
      )
    ) {
      return;
    }
    findings.push(finding);
  };

  const addRecommendation = (
    recommendation: ResultShareRegistryPresetWorkspaceHealthRecommendation,
  ): void => {
    recommendations.set(recommendation.kind, recommendation);
  };

  const storageInvalid =
    hasIntegrityIssue(input.integrityReport, "invalid_json") ||
    Boolean(input.diagnostics.workspaceStateWarning);
  if (storageInvalid) {
    applyPenalty(
      "storageIntegrity",
      hasIntegrityIssue(input.integrityReport, "invalid_json")
        ? getPresetWorkspaceHealthPenalty(thresholdPreferences, "storageInvalidJson")
        : getPresetWorkspaceHealthPenalty(thresholdPreferences, "workspaceStateWarning"),
    );
    addFinding({
      severity: hasIntegrityIssue(input.integrityReport, "invalid_json") ? "critical" : "warning",
      code: "storage_invalid_json",
      summary: "Local preset storage integrity needs attention.",
      detail: hasIntegrityIssue(input.integrityReport, "invalid_json")
        ? "At least one preset storage key contains invalid JSON."
        : "Local preset workspace organization state fell back after a storage warning.",
    });
    addRecommendation({
      kind: "run_integrity_check",
      label: "Run integrity check",
      detail: "Re-run the local preset integrity scan before applying more changes.",
    });
    if (input.diagnostics.workspaceStateWarning) {
      addRecommendation({
        kind: "reset_workspace_state",
        label: "Reset workspace state",
        detail: "Use the existing workspace reset control if local browser organization state continues to fall back after validation.",
      });
    }
  }

  if (hasIntegrityIssue(input.integrityReport, "unsafe_field_detected")) {
    applyPenalty(
      "storageIntegrity",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "unsafeFieldDetected"),
    );
    addFinding({
      severity: "critical",
      code: "unsafe_field_detected",
      summary: "Unsafe fields were detected in local preset storage.",
      detail: "Unsafe preset keys were quarantined and should be discarded through the existing recovery flow.",
    });
    addRecommendation({
      kind: "discard_invalid_presets",
      label: "Discard invalid presets",
      detail: "Use the existing recovery controls to remove unsafe or invalid preset entries.",
    });
  }

  if (hasIntegrityIssue(input.integrityReport, "invalid_schema_version")) {
    applyPenalty(
      "storageIntegrity",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "invalidSchemaVersion"),
    );
    addFinding({
      severity: "error",
      code: "invalid_schema_version",
      summary: "Local preset storage includes an unsupported schema shape.",
      detail: "At least one locally stored preset object does not match the expected schema version or normalized shape.",
    });
    addRecommendation({
      kind: "run_integrity_check",
      label: "Run integrity check",
      detail: "Review the integrity diagnostics before importing or restoring more preset state.",
    });
  }

  if (hasIntegrityIssue(input.integrityReport, "dangling_default_preset")) {
    applyPenalty(
      "presetValidity",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "danglingDefaultPreset"),
    );
    addFinding({
      severity: "warning",
      code: "dangling_default_preset",
      summary: "The local default preset marker is dangling.",
      detail: "The default preset id no longer points to an existing saved preset.",
    });
  }

  if (totalPresetCount === 0) {
    applyPenalty(
      "presetValidity",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "noSavedPresets"),
    );
    addFinding({
      severity: "warning",
      code: "no_saved_presets",
      summary: "No local saved presets are available.",
      detail: "The preset workspace can still function, but saved registry/drilldown reuse is not available until you save or import presets.",
    });
  }

  if (stalePinnedCount > 0) {
    applyPenalty(
      "pinnedPresetHygiene",
      Math.min(
        20,
        stalePinnedCount *
          getPresetWorkspaceHealthPenalty(thresholdPreferences, "stalePinnedPreset"),
      ),
    );
    addFinding({
      severity: stalePinnedCount >= 3 ? "error" : "warning",
      code: "stale_pinned_presets",
      summary: "One or more pinned presets no longer exist locally.",
      detail: `Detected ${stalePinnedCount} stale pinned preset id(s) across the grant and alias workspace sections.`,
    });
    addRecommendation({
      kind: "clean_stale_pins",
      label: "Clean stale pins",
      detail: "Use the existing stale-pin cleanup action to remove workspace pins that no longer match saved presets.",
    });
  }

  if (totalPinnedCount > 0 && validPinnedCount === 0) {
    applyPenalty(
      "pinnedPresetHygiene",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "allPinnedPresetsStale"),
    );
    addFinding({
      severity: "error",
      code: "stale_pinned_presets",
      summary: "All current pinned presets are stale.",
      detail: "Every pinned preset id points to a missing saved preset, so quick-apply workspace shortcuts are no longer useful.",
    });
  } else if (totalPinnedCount === 0 && totalPresetCount > 0) {
    addFinding({
      severity: "info",
      code: "no_pinned_presets",
      summary: "No presets are pinned in the local workspace.",
      detail: "Pinning is optional, but adding a few high-signal presets improves quick-apply workflows.",
    });
    addRecommendation({
      kind: "add_pinned_presets",
      label: "Add pinned presets",
      detail: "Pin a few frequently used grant or alias presets for faster workspace navigation.",
    });
  }

  const missingBackupPenalty =
    (input.lastGoodBackup
      ? 0
      : getPresetWorkspaceHealthPenalty(thresholdPreferences, "missingPresetBackup")) +
    (input.workspaceBackup
      ? 0
      : getPresetWorkspaceHealthPenalty(thresholdPreferences, "missingWorkspaceBackup"));
  if (missingBackupPenalty > 0) {
    applyPenalty("backupReadiness", missingBackupPenalty);
    addFinding({
      severity: missingBackupPenalty === 10 ? "warning" : "info",
      code: "missing_last_good_backup",
      summary: "One or more local backup snapshots are missing.",
      detail:
        missingBackupPenalty === 10
          ? "Neither the saved preset store nor the preset workspace currently has a last-good backup snapshot."
          : "One of the local preset backup layers is missing its last-good snapshot.",
    });
    addRecommendation({
      kind: "create_backup",
      label: "Create a backup before risky changes",
      detail: "Run an import/export or another backup-creating workflow before larger local cleanup or replacement steps.",
    });
  }

  if (input.auditSummary.storageWarning) {
    applyPenalty(
      "auditReliability",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "corruptedAuditHistory"),
    );
    addFinding({
      severity: "warning",
      code: "corrupted_audit_history",
      summary: "Local preset audit history is partially unavailable.",
      detail: "The current audit history key had to fall back safely, so recent local activity summaries may be incomplete.",
    });
    addRecommendation({
      kind: "review_recent_audit_failures",
      label: "Review recent audit failures",
      detail: "Check the local audit panel and diagnostics before relying on recent import or recovery summaries.",
    });
  }

  if (importFailureCount > 0) {
    applyPenalty(
      "importExportSafety",
      Math.min(
        20,
        importFailureCount *
          getPresetWorkspaceHealthPenalty(thresholdPreferences, "recentFailedImport"),
      ),
    );
    addFinding({
      severity: importFailureCount >= 2 ? "error" : "warning",
      code: "recent_failed_import",
      summary: "Recent local preset import activity includes failures.",
      detail: `Detected ${importFailureCount} failed import or validation event(s) in recent local preset activity.`,
    });
    addRecommendation({
      kind: "validate_import_before_apply",
      label: "Validate import before apply",
      detail: "Use the existing dry-run preview and validation flow before applying more preset or workspace imports.",
    });
    addRecommendation({
      kind: "review_recent_audit_failures",
      label: "Review recent audit failures",
      detail: "Inspect recent local audit entries to understand which import step failed.",
    });
  }

  if (recoveryFailureCount > 0) {
    applyPenalty(
      "auditReliability",
      Math.min(
        20,
        recoveryFailureCount *
          getPresetWorkspaceHealthPenalty(thresholdPreferences, "recentFailedRecovery"),
      ),
    );
    addFinding({
      severity: recoveryFailureCount >= 2 ? "error" : "warning",
      code: "recent_failed_recovery",
      summary: "Recent local recovery activity includes failures.",
      detail: `Detected ${recoveryFailureCount} failed recovery or restore event(s) in recent local preset activity.`,
    });
    addRecommendation({
      kind: "review_recent_audit_failures",
      label: "Review recent audit failures",
      detail: "Inspect recent local audit entries before relying on additional restore or recovery operations.",
    });
    if (input.lastGoodBackup || input.workspaceBackup) {
      addRecommendation({
        kind: "restore_last_good_backup",
        label: "Restore a last-good backup",
        detail: "Use one of the existing backup restore controls if local state still looks inconsistent after recovery failures.",
      });
    }
  }

  if (hasIntegrityIssue(input.integrityReport, "invalid_drilldown_context")) {
    applyPenalty(
      "drilldownContextCompleteness",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "invalidDrilldownContext"),
    );
    addFinding({
      severity: "warning",
      code: "invalid_drilldown_context",
      summary: "Some saved drilldown-linked preset context is invalid.",
      detail: "At least one saved preset has a drilldown context shape that did not normalize cleanly.",
    });
    addRecommendation({
      kind: "discard_invalid_presets",
      label: "Discard invalid presets",
      detail: "Remove invalid saved presets before relying on drilldown-linked quick apply behavior.",
    });
  }

  if (
    input.workspaceImportPreview &&
    !input.workspaceImportPreview.canApply &&
    input.workspaceImportPreview.errors.length > 0
  ) {
    applyPenalty(
      "importExportSafety",
      getPresetWorkspaceHealthPenalty(thresholdPreferences, "importPreviewHasErrors"),
    );
    addFinding({
      severity: "warning",
      code: "import_preview_has_errors",
      summary: "The current workspace import preview has blocking errors.",
      detail: "Imported workspace organization state cannot be applied until the current preview errors are resolved.",
    });
    addRecommendation({
      kind: "validate_import_before_apply",
      label: "Validate import before apply",
      detail: "Resolve the current workspace import preview errors before applying merge or replace.",
    });
  }

  score = clampScore(score);
  const status = classifyPresetWorkspaceHealthStatus(score, thresholdPreferences);

  const summary =
    status === "healthy"
      ? "Local preset workspace hygiene looks healthy."
      : status === "attention"
        ? "Local preset workspace hygiene needs minor attention."
        : status === "risk"
          ? "Local preset workspace hygiene has several risks that should be reviewed."
          : "Local preset workspace hygiene is in a critical state and needs recovery attention.";

  return {
    score,
    status,
    checkedAt,
    summary,
    thresholdPreferenceSource,
    thresholdSummary: buildPresetWorkspaceHealthThresholdSummary(thresholdPreferences),
    thresholdWarnings,
    breakdown,
    findings,
    recommendations: [...recommendations.values()],
    notes: [
      "This is a local operator hygiene score, not a security, compliance, or backend health score.",
      "It derives only from browser-local preset storage, workspace state, audit history, backup presence, and current import preview state.",
      thresholdPreferenceSource === "local"
        ? "Local threshold preferences are active for status classification, and local penalty override preferences may also change raw score when configured."
        : "Default threshold preferences are active for status classification.",
      "Score calculation never performs automatic repair; it only points to existing local tools.",
    ],
  };
}

function buildPresetWorkspaceIntegrityStatusLabel(
  diagnostics: ResultShareRegistryPresetStorageDiagnostics,
): string {
  if (diagnostics.errorCount > 0) {
    return "errors_detected";
  }
  if (diagnostics.warningCount > 0 || diagnostics.workspaceStateWarning) {
    return "warnings_detected";
  }
  return "clean";
}

export function buildHealthReportSafeExclusions(): string[] {
  return [
    "Admin bearer tokens are excluded.",
    "Raw share tokens, raw aliases, token hashes, and alias hashes are excluded.",
    "Saved preset definitions and raw workspace state objects are excluded.",
    "Raw import/export payloads, response payloads, local file paths, and source-file data are excluded.",
  ];
}

export function sanitizeHealthReportFinding(
  finding: ResultShareRegistryPresetWorkspaceHealthFinding,
): ResultShareRegistryPresetWorkspaceHealthFinding {
  return {
    severity: finding.severity,
    code: finding.code,
    summary: finding.summary.trim(),
    detail: finding.detail.trim(),
  };
}

export function sanitizeHealthReportRecommendation(
  recommendation: ResultShareRegistryPresetWorkspaceHealthRecommendation,
): ResultShareRegistryPresetWorkspaceHealthRecommendation {
  return {
    kind: recommendation.kind,
    label: recommendation.label.trim(),
    detail: recommendation.detail.trim(),
  };
}

function buildResultShareRegistryPresetWorkspaceHealthReportMetadata(input: {
  healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
  generatedAt: string;
}): ResultShareRegistryPresetWorkspaceHealthReportMetadata {
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION,
    generatedAt: input.generatedAt,
    app: "research-pulse-cn",
    source: "group-workspace-admin-web",
    reportKind: "preset_workspace_health",
    thresholdPreferenceSource: input.healthScore.thresholdPreferenceSource,
    localOnly: true,
    safeExport: true,
  };
}

export function buildResultShareRegistryPresetWorkspaceHealthReport(input: {
  healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
  workspaceViewModel: ResultShareRegistryPresetWorkspaceViewModel;
  auditSummary: ResultShareRegistryPresetLocalAuditSummary;
  now?: string;
}): ResultShareRegistryPresetWorkspaceHealthReport {
  const generatedAt = input.now ?? new Date().toISOString();
  const metadata = buildResultShareRegistryPresetWorkspaceHealthReportMetadata({
    healthScore: input.healthScore,
    generatedAt,
  });
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION,
    generatedAt,
    app: "research-pulse-cn",
    source: "group-workspace-admin-web",
    reportKind: "preset_workspace_health",
    metadata,
    health: {
      score: input.healthScore.score,
      status: input.healthScore.status,
      checkedAt: input.healthScore.checkedAt,
      summary: input.healthScore.summary,
      breakdown: { ...input.healthScore.breakdown },
    },
    thresholds: {
      source: input.healthScore.thresholdPreferenceSource,
      summary: [...input.healthScore.thresholdSummary],
      warnings: [...input.healthScore.thresholdWarnings],
    },
    diagnostics: {
      checkedAt: input.diagnostics.checkedAt,
      issueCount: input.diagnostics.warningCount + input.diagnostics.errorCount,
      warningCount: input.diagnostics.warningCount,
      errorCount: input.diagnostics.errorCount,
      validPresetCount: input.diagnostics.validPresetCount,
      invalidPresetCount: input.diagnostics.invalidPresetCount,
      lastBackupPresent: input.diagnostics.lastBackupPresent,
      workspaceStatePresent: input.diagnostics.workspaceStatePresent,
      workspaceStateWarningPresent: Boolean(input.diagnostics.workspaceStateWarning),
      latestValidationAt: input.diagnostics.latestValidationAt,
      auditStorageWarningPresent: Boolean(input.auditSummary.storageWarning),
    },
    workspaceSummary: {
      totalGrantPresets: input.diagnostics.grantPresetCount,
      totalAliasPresets: input.diagnostics.aliasPresetCount,
      pinnedGrantPresetCount: input.workspaceViewModel.pinnedGrantPresets.length,
      pinnedAliasPresetCount: input.workspaceViewModel.pinnedAliasPresets.length,
      staleGrantPinCount: input.workspaceViewModel.staleGrantPinIds.length,
      staleAliasPinCount: input.workspaceViewModel.staleAliasPinIds.length,
      recentGrantPresetCount: input.workspaceViewModel.recentGrantPresets.length,
      recentAliasPresetCount: input.workspaceViewModel.recentAliasPresets.length,
      hasLastActivePreset: Boolean(input.workspaceViewModel.lastActivePresetLabel),
      integrityStatusLabel: buildPresetWorkspaceIntegrityStatusLabel(input.diagnostics),
    },
    auditSummary: {
      totalEvents: input.auditSummary.totalEvents,
      successCount: input.auditSummary.successCount,
      warningCount: input.auditSummary.warningCount,
      failedCount: input.auditSummary.failedCount,
      lastEventAt: input.auditSummary.lastEventAt,
      backupRelatedCount: input.auditSummary.backupRelatedCount,
      recoveryRelatedCount: input.auditSummary.recoveryRelatedCount,
      importRelatedCount: input.auditSummary.importRelatedCount,
      exportRelatedCount: input.auditSummary.exportRelatedCount,
    },
    findings: input.healthScore.findings.map((finding) => sanitizeHealthReportFinding(finding)),
    recommendations: input.healthScore.recommendations.map((recommendation) =>
      sanitizeHealthReportRecommendation(recommendation),
    ),
    safetyExclusions: buildHealthReportSafeExclusions(),
    notes: [
      ...input.healthScore.notes,
      "This report is generated from browser-local operator workspace state only.",
      "Export never performs automatic recovery or repair.",
    ],
  };
}

function collectUnsafeHealthReportKeys(
  value: unknown,
  path: string,
  errors: string[],
): void {
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      collectUnsafeHealthReportKeys(item, `${path}[${index}]`, errors);
    });
    return;
  }
  if (!isRecord(value)) {
    return;
  }
  for (const [key, nestedValue] of Object.entries(value)) {
    if (looksUnsafeFieldName(key)) {
      errors.push(`${path} contains unsafe field "${key}".`);
      continue;
    }
    collectUnsafeHealthReportKeys(nestedValue, `${path}.${key}`, errors);
  }
}

export function validateResultShareRegistryPresetWorkspaceHealthReport(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): ResultShareRegistryPresetWorkspaceHealthReportValidationResult {
  const warnings: string[] = [];
  const errors: string[] = [];

  if (
    report.schemaVersion !== RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION
  ) {
    errors.push(
      `Health report schemaVersion must be "${RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION}".`,
    );
  }
  if (!report.generatedAt.trim()) {
    errors.push("Health report generatedAt is required.");
  }
  if (report.app !== "research-pulse-cn") {
    errors.push('Health report app must be "research-pulse-cn".');
  }
  if (report.source !== "group-workspace-admin-web") {
    errors.push('Health report source must be "group-workspace-admin-web".');
  }
  if (report.reportKind !== "preset_workspace_health") {
    errors.push('Health report reportKind must be "preset_workspace_health".');
  }
  if (report.metadata.schemaVersion !== report.schemaVersion) {
    errors.push("Health report metadata schemaVersion must match the top-level schemaVersion.");
  }
  if (report.metadata.thresholdPreferenceSource !== report.thresholds.source) {
    errors.push("Health report threshold preference source must match the threshold summary source.");
  }
  if (!Number.isInteger(report.health.score) || report.health.score < 0 || report.health.score > 100) {
    errors.push("Health report score must be an integer within 0..100.");
  }
  if (
    !["healthy", "attention", "risk", "critical"].includes(report.health.status)
  ) {
    errors.push("Health report status is invalid.");
  }
  if (!report.health.checkedAt.trim()) {
    errors.push("Health report checkedAt is required.");
  }
  if (!Array.isArray(report.thresholds.summary) || report.thresholds.summary.length === 0) {
    errors.push("Health report threshold summary must contain at least one item.");
  } else if (report.thresholds.summary.some((item) => typeof item !== "string" || !item.trim())) {
    errors.push("Health report threshold summary entries must be non-empty strings.");
  }
  if (!Array.isArray(report.safetyExclusions) || report.safetyExclusions.length === 0) {
    errors.push("Health report safety exclusions are required.");
  }
  if (!Array.isArray(report.findings) || !Array.isArray(report.recommendations)) {
    errors.push("Health report findings and recommendations must be arrays.");
  }
  if (!report.notes.every((item) => typeof item === "string" && item.trim())) {
    warnings.push("Health report contains one or more empty notes.");
  }

  collectUnsafeHealthReportKeys(report, "Health report", errors);

  return {
    valid: errors.length === 0,
    warnings,
    errors,
  };
}

export function serializeResultShareRegistryPresetWorkspaceHealthReportJson(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return JSON.stringify(report, null, 2);
}

export function serializeResultShareRegistryPresetWorkspaceHealthReportMarkdown(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  const lines = [
    "# Result Share Registry Preset Workspace Health Report",
    "",
    "## Report Metadata",
    `- Generated at: ${report.generatedAt}`,
    `- Schema version: ${report.schemaVersion}`,
    `- App: ${report.app}`,
    `- Source: ${report.source}`,
    `- Threshold source: ${report.thresholds.source}`,
    `- Local only: ${report.metadata.localOnly ? "yes" : "no"}`,
    "",
    "## Health Summary",
    `- Score: ${report.health.score}`,
    `- Status: ${formatPresetWorkspaceHealthStatus(report.health.status)}`,
    `- Checked at: ${report.health.checkedAt}`,
    `- Summary: ${report.health.summary}`,
    "",
    "## Thresholds",
    ...report.thresholds.summary.map((item) => `- ${item}`),
    ...(report.thresholds.warnings.length > 0
      ? ["", "Threshold warnings:", ...report.thresholds.warnings.map((item) => `- ${item}`)]
      : []),
    "",
    "## Breakdown",
    `- Storage integrity: ${report.health.breakdown.storageIntegrity}/100`,
    `- Preset validity: ${report.health.breakdown.presetValidity}/100`,
    `- Pinned preset hygiene: ${report.health.breakdown.pinnedPresetHygiene}/100`,
    `- Backup readiness: ${report.health.breakdown.backupReadiness}/100`,
    `- Audit reliability: ${report.health.breakdown.auditReliability}/100`,
    `- Import/export safety: ${report.health.breakdown.importExportSafety}/100`,
    `- Drilldown context completeness: ${report.health.breakdown.drilldownContextCompleteness}/100`,
    "",
    "## Findings",
    ...(report.findings.length > 0
      ? report.findings.flatMap((finding) => [
          `- [${finding.severity}] ${finding.summary}`,
          `  - Code: ${finding.code}`,
          `  - Detail: ${finding.detail}`,
        ])
      : ["- None"]),
    "",
    "## Recommendations",
    ...(report.recommendations.length > 0
      ? report.recommendations.flatMap((recommendation) => [
          `- ${recommendation.label}`,
          `  - Kind: ${recommendation.kind}`,
          `  - Detail: ${recommendation.detail}`,
        ])
      : ["- None"]),
    "",
    "## Local Diagnostics Summary",
    `- Issues: ${report.diagnostics.issueCount}`,
    `- Warnings: ${report.diagnostics.warningCount}`,
    `- Errors: ${report.diagnostics.errorCount}`,
    `- Valid presets: ${report.diagnostics.validPresetCount}`,
    `- Invalid presets: ${report.diagnostics.invalidPresetCount}`,
    `- Last preset backup present: ${report.diagnostics.lastBackupPresent ? "yes" : "no"}`,
    `- Workspace state present: ${report.diagnostics.workspaceStatePresent ? "yes" : "no"}`,
    `- Workspace state warning present: ${report.diagnostics.workspaceStateWarningPresent ? "yes" : "no"}`,
    `- Audit storage warning present: ${report.diagnostics.auditStorageWarningPresent ? "yes" : "no"}`,
    `- Latest validation at: ${report.diagnostics.latestValidationAt ?? "Not available"}`,
    "",
    "## Preset Workspace Summary",
    `- Grant presets: ${report.workspaceSummary.totalGrantPresets}`,
    `- Alias presets: ${report.workspaceSummary.totalAliasPresets}`,
    `- Pinned grant presets: ${report.workspaceSummary.pinnedGrantPresetCount}`,
    `- Pinned alias presets: ${report.workspaceSummary.pinnedAliasPresetCount}`,
    `- Stale grant pins: ${report.workspaceSummary.staleGrantPinCount}`,
    `- Stale alias pins: ${report.workspaceSummary.staleAliasPinCount}`,
    `- Recent grant presets: ${report.workspaceSummary.recentGrantPresetCount}`,
    `- Recent alias presets: ${report.workspaceSummary.recentAliasPresetCount}`,
    `- Last active preset present: ${report.workspaceSummary.hasLastActivePreset ? "yes" : "no"}`,
    `- Integrity status label: ${report.workspaceSummary.integrityStatusLabel}`,
    "",
    "## Local Audit Summary",
    `- Total events: ${report.auditSummary.totalEvents}`,
    `- Success: ${report.auditSummary.successCount}`,
    `- Warnings: ${report.auditSummary.warningCount}`,
    `- Failed: ${report.auditSummary.failedCount}`,
    `- Last event at: ${report.auditSummary.lastEventAt ?? "Not available"}`,
    `- Backup-related events: ${report.auditSummary.backupRelatedCount}`,
    `- Recovery-related events: ${report.auditSummary.recoveryRelatedCount}`,
    `- Import-related events: ${report.auditSummary.importRelatedCount}`,
    `- Export-related events: ${report.auditSummary.exportRelatedCount}`,
    "",
    "## Safety Exclusions",
    ...report.safetyExclusions.map((item) => `- ${item}`),
    "",
    "## Notes",
    ...report.notes.map((item) => `- ${item}`),
  ];
  return lines.join("\n");
}

export function buildPresetWorkspaceHealthReportPreview(input: {
  healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
  workspaceViewModel: ResultShareRegistryPresetWorkspaceViewModel;
  auditSummary: ResultShareRegistryPresetLocalAuditSummary;
  now?: string;
}): ResultShareRegistryPresetWorkspaceHealthReportPreview {
  const report = buildResultShareRegistryPresetWorkspaceHealthReport(input);
  const validation = validateResultShareRegistryPresetWorkspaceHealthReport(report);
  return {
    report,
    validation,
    json: validation.valid
      ? serializeResultShareRegistryPresetWorkspaceHealthReportJson(report)
      : null,
    markdown: validation.valid
      ? serializeResultShareRegistryPresetWorkspaceHealthReportMarkdown(report)
      : null,
  };
}

function buildHealthClipboardLocalOnlyCaveat(): string {
  return "Local operator hygiene only. This is not backend health, security scoring, or compliance scoring.";
}

function buildHealthClipboardTitle(
  format: ResultShareRegistryPresetWorkspaceHealthClipboardFormat,
): string {
  if (format === "health_summary") {
    return "Result Share Registry Preset Workspace Health Summary";
  }
  if (format === "findings_summary") {
    return "Result Share Registry Preset Workspace Findings Summary";
  }
  if (format === "recommendations_summary") {
    return "Result Share Registry Preset Workspace Recommendations Summary";
  }
  if (format === "compact_markdown") {
    return "Result Share Registry Preset Workspace Compact Markdown Summary";
  }
  return "Result Share Registry Preset Workspace Compact JSON Summary";
}

export function buildPresetWorkspaceHealthSummaryText(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return [
    buildHealthClipboardTitle("health_summary"),
    `Generated at: ${report.generatedAt}`,
    `Score: ${report.health.score}`,
    `Status: ${formatPresetWorkspaceHealthStatus(report.health.status)}`,
    `Summary: ${report.health.summary}`,
    `Threshold source: ${report.thresholds.source}`,
    `Diagnostics issues: ${report.diagnostics.issueCount}`,
    buildHealthClipboardLocalOnlyCaveat(),
  ].join("\n");
}

export function buildPresetWorkspaceHealthFindingsText(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return [
    buildHealthClipboardTitle("findings_summary"),
    `Score: ${report.health.score}`,
    `Status: ${formatPresetWorkspaceHealthStatus(report.health.status)}`,
    ...(report.findings.length > 0
      ? report.findings.map(
          (finding) => `- [${finding.severity}] ${finding.code}: ${finding.summary}`,
        )
      : ["- No findings"]),
    buildHealthClipboardLocalOnlyCaveat(),
  ].join("\n");
}

export function buildPresetWorkspaceHealthRecommendationsText(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return [
    buildHealthClipboardTitle("recommendations_summary"),
    ...(report.recommendations.length > 0
      ? report.recommendations.map(
          (recommendation) =>
            `- ${recommendation.label} (${recommendation.kind})`,
        )
      : ["- No recommendations"]),
    "Recommendations are local operator actions only.",
    buildHealthClipboardLocalOnlyCaveat(),
  ].join("\n");
}

export function buildPresetWorkspaceHealthCompactMarkdown(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return [
    "# Result Share Registry Preset Workspace Health Summary",
    "",
    "## Health Summary",
    `- Score: ${report.health.score}`,
    `- Status: ${formatPresetWorkspaceHealthStatus(report.health.status)}`,
    `- Summary: ${report.health.summary}`,
    "",
    "## Threshold Source",
    `- ${report.thresholds.source}`,
    "",
    "## Findings",
    ...(report.findings.length > 0
      ? report.findings.map((finding) => `- [${finding.severity}] ${finding.summary}`)
      : ["- None"]),
    "",
    "## Recommendations",
    ...(report.recommendations.length > 0
      ? report.recommendations.map((recommendation) => `- ${recommendation.label}`)
      : ["- None"]),
    "",
    "## Safety Exclusions",
    ...report.safetyExclusions.map((item) => `- ${item}`),
    "",
    buildHealthClipboardLocalOnlyCaveat(),
  ].join("\n");
}

export function buildPresetWorkspaceHealthCompactJson(
  report: ResultShareRegistryPresetWorkspaceHealthReport,
): string {
  return JSON.stringify(
    {
      schemaVersion: report.schemaVersion,
      generatedAt: report.generatedAt,
      localOnly: true,
      thresholdPreferenceSource: report.thresholds.source,
      health: {
        score: report.health.score,
        status: report.health.status,
        summary: report.health.summary,
      },
      findings: report.findings.map((finding) => ({
        severity: finding.severity,
        code: finding.code,
        summary: finding.summary,
      })),
      recommendations: report.recommendations.map((recommendation) => ({
        kind: recommendation.kind,
        label: recommendation.label,
      })),
      safetyExclusions: [...report.safetyExclusions],
    },
    null,
    2,
  );
}

export function buildPresetWorkspaceHealthClipboardSummary(input: {
  report: ResultShareRegistryPresetWorkspaceHealthReport;
  format: ResultShareRegistryPresetWorkspaceHealthClipboardFormat;
  now?: string;
}): ResultShareRegistryPresetWorkspaceHealthClipboardSummary {
  const generatedAt = input.now ?? new Date().toISOString();
  const body =
    input.format === "health_summary"
      ? buildPresetWorkspaceHealthSummaryText(input.report)
      : input.format === "findings_summary"
        ? buildPresetWorkspaceHealthFindingsText(input.report)
        : input.format === "recommendations_summary"
          ? buildPresetWorkspaceHealthRecommendationsText(input.report)
          : input.format === "compact_markdown"
            ? buildPresetWorkspaceHealthCompactMarkdown(input.report)
            : buildPresetWorkspaceHealthCompactJson(input.report);
  return {
    format: input.format,
    generatedAt,
    title: buildHealthClipboardTitle(input.format),
    body,
    safetyExclusions: [...input.report.safetyExclusions],
    sourceReportSchemaVersion: input.report.schemaVersion,
  };
}

function collectUnsafeClipboardPayloadKeys(
  value: unknown,
  path: string,
  errors: string[],
): void {
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      collectUnsafeClipboardPayloadKeys(item, `${path}[${index}]`, errors);
    });
    return;
  }
  if (!isRecord(value)) {
    return;
  }
  for (const [key, nestedValue] of Object.entries(value)) {
    if (looksUnsafeFieldName(key)) {
      errors.push(`${path} contains unsafe field "${key}".`);
      continue;
    }
    collectUnsafeClipboardPayloadKeys(nestedValue, `${path}.${key}`, errors);
  }
}

export function validatePresetWorkspaceHealthClipboardPayload(
  summary: ResultShareRegistryPresetWorkspaceHealthClipboardSummary,
): ResultShareRegistryPresetWorkspaceHealthClipboardValidationResult {
  const warnings: string[] = [];
  const errors: string[] = [];

  if (!summary.title.trim()) {
    errors.push("Clipboard summary title is required.");
  }
  if (!summary.body.trim()) {
    errors.push("Clipboard summary body is required.");
  }
  if (
    summary.sourceReportSchemaVersion !==
    RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION
  ) {
    errors.push(
      `Clipboard summary source schemaVersion must be "${RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_HEALTH_REPORT_SCHEMA_VERSION}".`,
    );
  }
  if (summary.body.length > 12000) {
    warnings.push("Clipboard summary is large and may be truncated by some clipboard targets.");
  }
  if (looksUnsafeFieldName(summary.title)) {
    errors.push("Clipboard summary title contains an unsafe field name.");
  }

  if (summary.format === "compact_json") {
    try {
      const parsed = JSON.parse(summary.body);
      collectUnsafeClipboardPayloadKeys(parsed, "Clipboard payload", errors);
    } catch {
      errors.push("Compact JSON clipboard payload is not valid JSON.");
    }
  } else {
    const unsafeBodyMatches = summary.body.match(
      /\b(rawAlias|rawShareToken|token_hash|alias_hash|localPath|absolutePath|sourceFile|responsePayload)\b/g,
    );
    if (unsafeBodyMatches && unsafeBodyMatches.length > 0) {
      errors.push("Clipboard summary contains an unsafe field label.");
    }
  }

  return {
    valid: errors.length === 0,
    warnings,
    errors,
  };
}

function collectUnexpectedKeys(
  value: Record<string, unknown>,
  allowedKeys: Set<string>,
  path: string,
  warnings: string[],
  errors: string[],
): boolean {
  let hasUnsafeKey = false;
  for (const key of Object.keys(value)) {
    if (allowedKeys.has(key)) {
      continue;
    }
    if (looksUnsafeFieldName(key)) {
      errors.push(`${path} contains unsafe field "${key}".`);
      hasUnsafeKey = true;
      continue;
    }
    warnings.push(`${path} contains unsupported field "${key}" and it will be ignored.`);
  }
  return hasUnsafeKey;
}

function generateImportedPresetId(
  existingIds: Set<string>,
  preferredId: string,
): string {
  if (!existingIds.has(preferredId)) {
    existingIds.add(preferredId);
    return preferredId;
  }
  let suffix = 1;
  let candidate = `${preferredId}-imported-${suffix}`;
  while (existingIds.has(candidate)) {
    suffix += 1;
    candidate = `${preferredId}-imported-${suffix}`;
  }
  existingIds.add(candidate);
  return candidate;
}

function generateImportedPresetName(
  existingNames: Set<string>,
  preferredName: string,
): string {
  const baseCopyName = `${preferredName} (Imported copy)`;
  if (!existingNames.has(baseCopyName)) {
    existingNames.add(baseCopyName);
    return baseCopyName;
  }
  let suffix = 2;
  let candidate = `${preferredName} (Imported copy ${suffix})`;
  while (existingNames.has(candidate)) {
    suffix += 1;
    candidate = `${preferredName} (Imported copy ${suffix})`;
  }
  existingNames.add(candidate);
  return candidate;
}

function readStorageItemSafely(
  storage: Storage | null | undefined,
  key: string,
  issues: ResultShareRegistryPresetIntegrityIssue[],
): string | null {
  if (!storage) {
    return null;
  }
  try {
    return storage.getItem(key);
  } catch {
    pushIssue(issues, {
      severity: "error",
      scope: "storage",
      presetId: null,
      presetName: null,
      code: "storage_key_unreadable",
      message: `Local preset storage key "${key}" could not be read.`,
      safeDetails: key,
    });
    return null;
  }
}

function inspectUnexpectedStoredKeys(
  value: Record<string, unknown>,
  allowedKeys: Set<string>,
  issueCode: ResultShareRegistryPresetIntegrityIssueCode,
  issues: ResultShareRegistryPresetIntegrityIssue[],
  options: {
    scope: ResultShareRegistrySavedViewScope | "storage";
    presetId?: string | null;
    presetName?: string | null;
    path: string;
    severity?: "warning" | "error";
  },
): boolean {
  let hasUnsafeKey = false;
  for (const key of Object.keys(value)) {
    if (allowedKeys.has(key)) {
      continue;
    }
    if (looksUnsafeFieldName(key)) {
      pushIssue(issues, {
        severity: "error",
        scope: options.scope,
        presetId: options.presetId ?? null,
        presetName: options.presetName ?? null,
        code: "unsafe_field_detected",
        message: `${options.path} contains an unsafe field name and was quarantined.`,
        safeDetails: redactUnsafeImportIssueDetails(key),
      });
      hasUnsafeKey = true;
      continue;
    }
    pushIssue(issues, {
      severity: options.severity ?? "warning",
      scope: options.scope,
      presetId: options.presetId ?? null,
      presetName: options.presetName ?? null,
      code: issueCode,
      message: `${options.path} contains an unsupported field and it will be ignored.`,
      safeDetails: key,
    });
  }
  return hasUnsafeKey;
}

function validateStoredSavedView(
  value: unknown,
  scope: ResultShareRegistrySavedViewScope,
  issues: ResultShareRegistryPresetIntegrityIssue[],
  path: string,
): ResultShareRegistrySavedView | null {
  if (!isRecord(value)) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId: null,
      presetName: null,
      code: "missing_required_field",
      message: `${path} is not a valid preset object.`,
      safeDetails: null,
    });
    return null;
  }

  const presetId = typeof value.id === "string" ? value.id.trim() : null;
  const presetName = typeof value.name === "string" ? value.name.trim() : null;

  if (
    inspectUnexpectedStoredKeys(value, presetAllowedKeys, "missing_required_field", issues, {
      scope,
      presetId,
      presetName,
      path,
    })
  ) {
    return null;
  }

  const missingFields = ["id", "name", "createdAt", "updatedAt"].filter((field) => {
    const candidate = value[field];
    return typeof candidate !== "string" || candidate.trim().length === 0;
  });
  if (missingFields.length > 0) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId,
      presetName,
      code: "missing_required_field",
      message: `${path} is missing required preset fields.`,
      safeDetails: missingFields.join(", "),
    });
    return null;
  }

  if (value.scope !== scope) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId,
      presetName,
      code: "invalid_scope",
      message: `${path} has an invalid preset scope.`,
      safeDetails: typeof value.scope === "string" ? value.scope : null,
    });
    return null;
  }

  if (!isRecord(value.filters)) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId,
      presetName,
      code: "invalid_filter_shape",
      message: `${path}.filters must be an object.`,
      safeDetails: null,
    });
    return null;
  }
  if (
    inspectUnexpectedStoredKeys(value.filters, presetFilterAllowedKeys, "invalid_filter_shape", issues, {
      scope,
      presetId,
      presetName,
      path: `${path}.filters`,
    })
  ) {
    return null;
  }

  if (!isRecord(value.sort)) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId,
      presetName,
      code: "invalid_sort_shape",
      message: `${path}.sort must be an object.`,
      safeDetails: null,
    });
    return null;
  }
  if (
    inspectUnexpectedStoredKeys(value.sort, presetSortAllowedKeys, "invalid_sort_shape", issues, {
      scope,
      presetId,
      presetName,
      path: `${path}.sort`,
    })
  ) {
    return null;
  }

  if (value.drilldownContext !== undefined && value.drilldownContext !== null) {
    if (!isRecord(value.drilldownContext)) {
      pushIssue(issues, {
        severity: "error",
        scope,
        presetId,
        presetName,
        code: "invalid_drilldown_context",
        message: `${path}.drilldownContext must be an object or null.`,
        safeDetails: null,
      });
      return null;
    }
    if (
      inspectUnexpectedStoredKeys(
        value.drilldownContext,
        presetDrilldownAllowedKeys,
        "invalid_drilldown_context",
        issues,
        {
          scope,
          presetId,
          presetName,
          path: `${path}.drilldownContext`,
        },
      )
    ) {
      return null;
    }
  }

  const normalized = normalizeSavedView(value, scope);
  if (!normalized) {
    pushIssue(issues, {
      severity: "error",
      scope,
      presetId,
      presetName,
      code: "missing_required_field",
      message: `${path} does not match the expected preset shape.`,
      safeDetails: null,
    });
    return null;
  }
  return normalized;
}

function inspectStoredSavedViewList(
  raw: string | null,
  scope: ResultShareRegistrySavedViewScope,
  issues: ResultShareRegistryPresetIntegrityIssue[],
  storageKey: string,
): StorageInspectionScopeResult {
  if (!raw) {
    return {
      keyPresent: false,
      rawCount: 0,
      validPresets: [],
    };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    pushIssue(issues, {
      severity: "error",
      scope: "storage",
      presetId: null,
      presetName: null,
      code: "invalid_json",
      message: `Local preset storage key "${storageKey}" is not valid JSON.`,
      safeDetails: storageKey,
    });
    return {
      keyPresent: true,
      rawCount: 0,
      validPresets: [],
    };
  }
  if (!Array.isArray(parsed)) {
    pushIssue(issues, {
      severity: "error",
      scope: "storage",
      presetId: null,
      presetName: null,
      code: "storage_key_not_array",
      message: `Local preset storage key "${storageKey}" must contain an array.`,
      safeDetails: storageKey,
    });
    return {
      keyPresent: true,
      rawCount: 0,
      validPresets: [],
    };
  }
  return {
    keyPresent: true,
    rawCount: parsed.length,
    validPresets: parsed
      .map((item, index) =>
        validateStoredSavedView(item, scope, issues, `${storageKey}[${index}]`),
      )
      .filter((item): item is ResultShareRegistrySavedView => item !== null),
  };
}

function normalizeBackupSnapshot(
  value: unknown,
): ResultShareRegistryPresetBackupSnapshot | null {
  if (!isRecord(value)) {
    return null;
  }
  if (value.schemaVersion !== RESULT_SHARE_REGISTRY_PRESET_BACKUP_SCHEMA_VERSION) {
    return null;
  }
  if (typeof value.createdAt !== "string" || typeof value.reason !== "string") {
    return null;
  }
  if (!Array.isArray(value.grantRegistry) || !Array.isArray(value.aliasRegistry)) {
    return null;
  }
  const grantRegistry = value.grantRegistry
    .map((preset) => normalizeSavedView(preset, "grant_registry"))
    .filter((preset): preset is ResultShareRegistrySavedView => preset !== null);
  const aliasRegistry = value.aliasRegistry
    .map((preset) => normalizeSavedView(preset, "alias_registry"))
    .filter((preset): preset is ResultShareRegistrySavedView => preset !== null);
  if (
    grantRegistry.length !== value.grantRegistry.length ||
    aliasRegistry.length !== value.aliasRegistry.length
  ) {
    return null;
  }
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_BACKUP_SCHEMA_VERSION,
    createdAt: value.createdAt,
    reason: value.reason,
    grantRegistry,
    aliasRegistry,
    defaultPresetId: typeof value.defaultPresetId === "string" ? value.defaultPresetId : null,
  };
}

function deduplicatePresets(
  store: ResultShareRegistrySavedViewStoreState,
  issues: ResultShareRegistryPresetIntegrityIssue[],
): ResultShareRegistrySavedViewStoreState {
  const seenIds = new Set<string>();
  const dedupe = (
    presets: ResultShareRegistrySavedView[],
    scope: ResultShareRegistrySavedViewScope,
  ) =>
    presets.filter((preset) => {
      if (seenIds.has(preset.id)) {
        pushIssue(issues, {
          severity: "error",
          scope,
          presetId: preset.id,
          presetName: preset.name,
          code: "duplicate_preset_id",
          message: `Preset ID "${preset.id}" is duplicated and later copies were quarantined.`,
          safeDetails: preset.id,
        });
        return false;
      }
      seenIds.add(preset.id);
      return true;
    });

  return {
    grantPresets: dedupe(store.grantPresets, "grant_registry"),
    aliasPresets: dedupe(store.aliasPresets, "alias_registry"),
    defaultPresetId: store.defaultPresetId,
  };
}

export function buildResultShareRegistryPresetIntegrityReport(
  store: ResultShareRegistrySavedViewStoreState,
  issues: ResultShareRegistryPresetIntegrityIssue[],
  options?: {
    checkedAt?: string;
    rawGrantPresetCount?: number;
    rawAliasPresetCount?: number;
  },
): ResultShareRegistryPresetIntegrityReport {
  const checkedAt = options?.checkedAt ?? new Date().toISOString();
  const warningCount = issues.filter((issue) => issue.severity === "warning").length;
  const errorCount = issues.filter((issue) => issue.severity === "error").length;
  const validPresetCount = store.grantPresets.length + store.aliasPresets.length;
  const invalidPresetCount = issues.filter(
    (issue) =>
      issue.severity === "error" &&
      issue.scope !== "storage" &&
      issue.code !== "dangling_default_preset",
  ).length;

  return {
    checkedAt,
    grantPresetCount: options?.rawGrantPresetCount ?? store.grantPresets.length,
    aliasPresetCount: options?.rawAliasPresetCount ?? store.aliasPresets.length,
    validPresetCount,
    invalidPresetCount,
    warningCount,
    errorCount,
    issues,
    canAutoRepair: issues.some((issue) =>
      [
        "invalid_json",
        "storage_key_not_array",
        "duplicate_preset_id",
        "dangling_default_preset",
        "unsafe_field_detected",
        "missing_required_field",
        "invalid_filter_shape",
        "invalid_sort_shape",
        "invalid_drilldown_context",
        "invalid_scope",
      ].includes(issue.code),
    ),
    canResetGrantScope: (options?.rawGrantPresetCount ?? store.grantPresets.length) > 0,
    canResetAliasScope: (options?.rawAliasPresetCount ?? store.aliasPresets.length) > 0,
    notes: [
      "Diagnostics are local-only and inspect browser preset storage only.",
      invalidPresetCount > 0
        ? "Invalid presets stay quarantined from active shell state until you discard them or reset a scope."
        : "All currently loaded presets passed local integrity checks.",
    ],
  };
}

export function createResultShareRegistryPresetBackup(
  store: ResultShareRegistrySavedViewStoreState,
  reason: string,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetBackupSnapshot {
  return {
    schemaVersion: RESULT_SHARE_REGISTRY_PRESET_BACKUP_SCHEMA_VERSION,
    createdAt: options?.now ?? new Date().toISOString(),
    reason,
    grantRegistry: store.grantPresets,
    aliasRegistry: store.aliasPresets,
    defaultPresetId: store.defaultPresetId,
  };
}

export function loadResultShareRegistryPresetBackup(
  storage: Storage | null | undefined,
): ResultShareRegistryPresetBackupSnapshot | null {
  if (!storage) {
    return null;
  }
  const raw = storage.getItem(RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return normalizeBackupSnapshot(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function persistResultShareRegistryPresetBackup(
  storage: Storage | null | undefined,
  backup: ResultShareRegistryPresetBackupSnapshot | null,
): void {
  if (!storage) {
    return;
  }
  if (!backup) {
    storage.removeItem(RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY);
    return;
  }
  storage.setItem(RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY, JSON.stringify(backup));
}

export function restoreResultShareRegistryPresetBackup(
  backup: ResultShareRegistryPresetBackupSnapshot | null,
): ResultShareRegistrySavedViewStoreState | null {
  if (!backup) {
    return null;
  }
  const restoredStore: ResultShareRegistrySavedViewStoreState = {
    grantPresets: backup.grantRegistry,
    aliasPresets: backup.aliasRegistry,
    defaultPresetId: backup.defaultPresetId,
  };
  return {
    ...restoredStore,
    defaultPresetId: findSavedViewById(restoredStore, restoredStore.defaultPresetId)
      ? restoredStore.defaultPresetId
      : null,
  };
}

export function applyResultShareRegistryPresetRecoveryAction(
  store: ResultShareRegistrySavedViewStoreState,
  report: ResultShareRegistryPresetIntegrityReport,
  action: ResultShareRegistryPresetRecoveryAction,
  backup: ResultShareRegistryPresetBackupSnapshot | null,
): {
  store: ResultShareRegistrySavedViewStoreState;
  restoredBackup: boolean;
  defaultPresetCleared: boolean;
} {
  if (action === "restore_last_good_backup") {
    const restored = restoreResultShareRegistryPresetBackup(backup);
    return {
      store: restored ?? store,
      restoredBackup: restored !== null,
      defaultPresetCleared: false,
    };
  }

  let nextStore = store;
  if (action === "reset_grant_scope") {
    nextStore = {
      ...store,
      grantPresets: [],
      defaultPresetId:
        store.defaultPresetId && store.grantPresets.some((preset) => preset.id === store.defaultPresetId)
          ? null
          : store.defaultPresetId,
    };
  } else if (action === "reset_alias_scope") {
    nextStore = {
      ...store,
      aliasPresets: [],
      defaultPresetId:
        store.defaultPresetId && store.aliasPresets.some((preset) => preset.id === store.defaultPresetId)
          ? null
          : store.defaultPresetId,
    };
  } else if (action === "reset_all_presets") {
    nextStore = {
      grantPresets: [],
      aliasPresets: [],
      defaultPresetId: null,
    };
  } else if (
    action === "clear_dangling_default_preset" ||
    report.issues.some((issue) => issue.code === "dangling_default_preset")
  ) {
    nextStore = {
      ...store,
      defaultPresetId: null,
    };
  }

  return {
    store: nextStore,
    restoredBackup: false,
    defaultPresetCleared: nextStore.defaultPresetId !== store.defaultPresetId,
  };
}

export function inspectResultShareRegistryPresetStorage(
  storage: Storage | null | undefined,
  options?: {
    now?: string;
  },
): ResultShareRegistryPresetStorageInspection {
  const checkedAt = options?.now ?? new Date().toISOString();
  const issues: ResultShareRegistryPresetIntegrityIssue[] = [];
  const grantRaw = readStorageItemSafely(
    storage,
    RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
    issues,
  );
  const aliasRaw = readStorageItemSafely(
    storage,
    RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
    issues,
  );
  const defaultPresetId = readStorageItemSafely(
    storage,
    RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY,
    issues,
  );

  const grantScope = inspectStoredSavedViewList(
    grantRaw,
    "grant_registry",
    issues,
    RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
  );
  const aliasScope = inspectStoredSavedViewList(
    aliasRaw,
    "alias_registry",
    issues,
    RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
  );

  const deduplicatedStore = deduplicatePresets(
    {
      grantPresets: grantScope.validPresets,
      aliasPresets: aliasScope.validPresets,
      defaultPresetId,
    },
    issues,
  );
  const defaultPresetStillExists = Boolean(
    deduplicatedStore.defaultPresetId &&
      findSavedViewById(deduplicatedStore, deduplicatedStore.defaultPresetId),
  );
  if (deduplicatedStore.defaultPresetId && !defaultPresetStillExists) {
    pushIssue(issues, {
      severity: "warning",
      scope: "storage",
      presetId: deduplicatedStore.defaultPresetId,
      presetName: null,
      code: "dangling_default_preset",
      message: "The local default preset marker no longer points to a valid preset.",
      safeDetails: deduplicatedStore.defaultPresetId,
    });
  }
  const store: ResultShareRegistrySavedViewStoreState = {
    ...deduplicatedStore,
    defaultPresetId: defaultPresetStillExists ? deduplicatedStore.defaultPresetId : null,
  };

  let lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null = null;
  const rawBackup = readStorageItemSafely(
    storage,
    RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY,
    issues,
  );
  if (rawBackup) {
    try {
      lastGoodBackup = normalizeBackupSnapshot(JSON.parse(rawBackup));
      if (!lastGoodBackup) {
        pushIssue(issues, {
          severity: "warning",
          scope: "storage",
          presetId: null,
          presetName: null,
          code: "invalid_schema_version",
          message: "The last-good preset backup could not be validated and cannot be restored.",
          safeDetails: RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY,
        });
      }
    } catch {
      pushIssue(issues, {
        severity: "warning",
        scope: "storage",
        presetId: null,
        presetName: null,
        code: "invalid_json",
        message: "The last-good preset backup is not valid JSON and cannot be restored.",
        safeDetails: RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY,
      });
    }
  }

  const workspaceStateLoad = loadResultShareRegistryPresetWorkspaceState(storage);

  const report = buildResultShareRegistryPresetIntegrityReport(store, issues, {
    checkedAt,
    rawGrantPresetCount: grantScope.rawCount,
    rawAliasPresetCount: aliasScope.rawCount,
  });
  const diagnostics: ResultShareRegistryPresetStorageDiagnostics = {
    checkedAt,
    storageKeysPresent: {
      grantPresets: grantScope.keyPresent,
      aliasPresets: aliasScope.keyPresent,
      defaultPresetId: defaultPresetId !== null,
      lastGoodBackup: rawBackup !== null,
      workspaceState: workspaceStateLoad.keyPresent,
    },
    grantPresetCount: report.grantPresetCount,
    aliasPresetCount: report.aliasPresetCount,
    validPresetCount: report.validPresetCount,
    invalidPresetCount: report.invalidPresetCount,
    defaultPresetIdPresent: defaultPresetId !== null,
    lastBackupPresent: lastGoodBackup !== null,
    workspaceStatePresent: workspaceStateLoad.keyPresent,
    workspaceStateWarning: workspaceStateLoad.storageWarning,
    latestValidationAt: report.checkedAt,
    warningCount: report.warningCount,
    errorCount: report.errorCount,
    notes: [
      "Diagnostics inspect browser-local preset storage only.",
      lastGoodBackup
        ? `Last-good backup available from ${lastGoodBackup.createdAt}.`
        : "No last-good backup snapshot is stored yet.",
      workspaceStateLoad.storageWarning
        ? workspaceStateLoad.storageWarning
        : workspaceStateLoad.keyPresent
          ? "Local preset workspace organization state is present."
          : "No local preset workspace organization state is stored yet.",
    ],
  };

  return {
    store,
    report,
    diagnostics,
    lastGoodBackup,
  };
}

export function loadResultShareRegistrySavedViewStore(
  storage: Storage | null | undefined,
): ResultShareRegistrySavedViewStoreState {
  return inspectResultShareRegistryPresetStorage(storage).store;
}

export function persistResultShareRegistrySavedViewStore(
  storage: Storage | null | undefined,
  store: ResultShareRegistrySavedViewStoreState,
): void {
  if (!storage) {
    return;
  }
  storage.setItem(
    RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
    JSON.stringify(store.grantPresets),
  );
  storage.setItem(
    RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
    JSON.stringify(store.aliasPresets),
  );
  if (store.defaultPresetId) {
    storage.setItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY, store.defaultPresetId);
  } else {
    storage.removeItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY);
  }
}

export function saveResultShareRegistrySavedView(
  store: ResultShareRegistrySavedViewStoreState,
  preset: ResultShareRegistrySavedView,
): ResultShareRegistrySavedViewStoreState {
  if (preset.scope === "grant_registry") {
    return {
      ...store,
      grantPresets: [...store.grantPresets, preset],
    };
  }
  return {
    ...store,
    aliasPresets: [...store.aliasPresets, preset],
  };
}

export function overwriteResultShareRegistrySavedView(
  store: ResultShareRegistrySavedViewStoreState,
  presetId: string,
  draft: ResultShareRegistrySavedViewDraft,
  options?: {
    now?: string;
  },
): ResultShareRegistrySavedViewStoreState {
  const existing = findSavedViewById(store, presetId);
  if (!existing || existing.scope !== draft.scope) {
    return store;
  }
  const nextPreset: ResultShareRegistrySavedView = {
    ...existing,
    name: draft.name.trim(),
    filters: normalizeFiltersForScope(draft.scope, draft.filters),
    sort: normalizeResultShareRegistrySectionSortInput(draft.sort),
    drilldownContext: normalizeDrilldownContext(draft.drilldownContext),
    updatedAt: options?.now ?? new Date().toISOString(),
  };
  if (draft.scope === "grant_registry") {
    return {
      ...store,
      grantPresets: replaceSavedView(store.grantPresets, nextPreset),
    };
  }
  return {
    ...store,
    aliasPresets: replaceSavedView(store.aliasPresets, nextPreset),
  };
}

export function deleteResultShareRegistrySavedView(
  store: ResultShareRegistrySavedViewStoreState,
  scope: ResultShareRegistrySavedViewScope,
  presetId: string,
): ResultShareRegistrySavedViewStoreState {
  const nextStore =
    scope === "grant_registry"
      ? {
          ...store,
          grantPresets: store.grantPresets.filter((preset) => preset.id !== presetId),
        }
      : {
          ...store,
          aliasPresets: store.aliasPresets.filter((preset) => preset.id !== presetId),
        };
  return {
    ...nextStore,
    defaultPresetId: nextStore.defaultPresetId === presetId ? null : nextStore.defaultPresetId,
  };
}

export function setResultShareRegistryDefaultPresetId(
  store: ResultShareRegistrySavedViewStoreState,
  presetId: string | null,
): ResultShareRegistrySavedViewStoreState {
  return {
    ...store,
    defaultPresetId: presetId && findSavedViewById(store, presetId) ? presetId : null,
  };
}

export function applyResultShareRegistrySavedView(
  currentFilters: ResultShareRegistryFilterInput,
  currentSorts: ResultShareRegistrySortInput,
  currentDrilldownFilters: ConversionFilterInput,
  preset: ResultShareRegistrySavedView,
  mode: ResultShareRegistrySavedViewApplyMode = "registry_only",
): {
  filters: ResultShareRegistryFilterInput;
  sorts: ResultShareRegistrySortInput;
  drilldownFilters: ConversionFilterInput;
  didApplyDrilldownContext: boolean;
} {
  const normalizedFilters = normalizeResultShareRegistryFilterInput(currentFilters);
  const normalizedSorts = normalizeResultShareRegistrySortInput(currentSorts);
  const normalizedDrilldownFilters = normalizeConversionFilterInput({
    ...currentDrilldownFilters,
    shareKind: null,
  });
  const didApplyDrilldownContext =
    mode === "registry_and_drilldown" && preset.drilldownContext !== null;
  const drilldownFilters = didApplyDrilldownContext
    ? normalizeConversionFilterInput({
        ...normalizedDrilldownFilters,
        ...preset.drilldownContext,
        shareKind: null,
      })
    : normalizedDrilldownFilters;

  if (preset.scope === "grant_registry") {
    return {
      filters: normalizeResultShareRegistryFilterInput({
        ...normalizedFilters,
        shareKind: preset.filters.shareKind,
        grantStatus: preset.filters.grantStatus,
        workspaceId: preset.filters.workspaceId,
      }),
      sorts: normalizeResultShareRegistrySortInput({
        ...normalizedSorts,
        grants: preset.sort,
      }),
      drilldownFilters,
      didApplyDrilldownContext,
    };
  }

  return {
    filters: normalizeResultShareRegistryFilterInput({
      ...normalizedFilters,
      shareKind: preset.filters.shareKind,
      aliasStatus: preset.filters.aliasStatus,
      resultShareGrantId: preset.filters.resultShareGrantId,
    }),
    sorts: normalizeResultShareRegistrySortInput({
      ...normalizedSorts,
      aliases: preset.sort,
    }),
    drilldownFilters,
    didApplyDrilldownContext,
  };
}

export function buildInitialResultShareRegistrySavedViewState(
  store: ResultShareRegistrySavedViewStoreState,
): {
  filters: ResultShareRegistryFilterInput;
  sorts: ResultShareRegistrySortInput;
  drilldownFilters: ConversionFilterInput;
  defaultPreset: ResultShareRegistrySavedView | null;
} {
  const defaultPreset = findSavedViewById(store, store.defaultPresetId);
  if (!defaultPreset) {
    return {
      filters: DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
      sorts: DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      drilldownFilters: DEFAULT_CONVERSION_FILTER_INPUT,
      defaultPreset: null,
    };
  }
  const applied = applyResultShareRegistrySavedView(
    DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
    DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
    DEFAULT_CONVERSION_FILTER_INPUT,
    defaultPreset,
    defaultPreset.drilldownContext ? "registry_and_drilldown" : "registry_only",
  );
  return {
    filters: applied.filters,
    sorts: applied.sorts,
    drilldownFilters: applied.drilldownFilters,
    defaultPreset,
  };
}

export function buildResultShareRegistrySavedViewSummaries(
  store: ResultShareRegistrySavedViewStoreState,
  workspaceState?: ResultShareRegistryPresetWorkspaceState,
): {
  grantPresets: ResultShareRegistrySavedViewSummary[];
  aliasPresets: ResultShareRegistrySavedViewSummary[];
  defaultPreset: ResultShareRegistrySavedViewSummary | null;
} {
  const pinnedGrantIds = new Set(workspaceState?.pinnedGrantPresetIds ?? []);
  const pinnedAliasIds = new Set(workspaceState?.pinnedAliasPresetIds ?? []);
  const buildDrilldownSummaryItems = (
    drilldownContext: ResultShareRegistrySavedViewDrilldownContext | null,
  ): string[] => {
    if (!drilldownContext) {
      return [];
    }
    const summary = buildConversionFilterSummaryViewModel(
      {
        ...DEFAULT_CONVERSION_FILTER_INPUT,
        ...drilldownContext,
        shareKind: null,
      },
      PER_SHARE_DRILLDOWN_FILTER_SUPPORT,
    );
    if (summary.chips.length === 0) {
      return ["Default per-share drilldown filters"];
    }
    return summary.chips.map((chip) => `${chip.label}: ${chip.value}`);
  };

  const buildSummary = (
    preset: ResultShareRegistrySavedView,
  ): ResultShareRegistrySavedViewSummary => {
    const summaryItems =
      preset.scope === "grant_registry"
        ? [
            preset.filters.shareKind ? `Share kind: ${preset.filters.shareKind}` : null,
            preset.filters.grantStatus ? `Grant status: ${preset.filters.grantStatus}` : null,
            preset.filters.workspaceId ? `Workspace: ${preset.filters.workspaceId}` : null,
            `Sort: ${formatResultShareRegistrySectionSortLabel(preset.sort)}`,
          ]
        : [
            preset.filters.shareKind ? `Share kind: ${preset.filters.shareKind}` : null,
            preset.filters.aliasStatus ? `Alias status: ${preset.filters.aliasStatus}` : null,
            preset.filters.resultShareGrantId
              ? `Grant: ${preset.filters.resultShareGrantId}`
              : null,
            `Sort: ${formatResultShareRegistrySectionSortLabel(preset.sort)}`,
          ];

    return {
      id: preset.id,
      name: preset.name,
      scope: preset.scope,
      summaryItems: summaryItems.filter((item): item is string => item !== null),
      drilldownSummaryItems: buildDrilldownSummaryItems(preset.drilldownContext),
      hasDrilldownContext: preset.drilldownContext !== null,
      createdAt: preset.createdAt,
      updatedAt: preset.updatedAt,
      isDefault: store.defaultPresetId === preset.id,
      isPinned:
        preset.scope === "grant_registry"
          ? pinnedGrantIds.has(preset.id)
          : pinnedAliasIds.has(preset.id),
    };
  };

  const grantPresets = store.grantPresets.map(buildSummary);
  const aliasPresets = store.aliasPresets.map(buildSummary);
  const defaultPreset =
    grantPresets.find((preset) => preset.isDefault) ??
    aliasPresets.find((preset) => preset.isDefault) ??
    null;

  return {
    grantPresets,
    aliasPresets,
    defaultPreset,
  };
}
