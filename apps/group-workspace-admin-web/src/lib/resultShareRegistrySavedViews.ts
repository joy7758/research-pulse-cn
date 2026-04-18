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
export const RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION =
  "result-share-registry-presets.v1";
export const RESULT_SHARE_REGISTRY_PRESET_BACKUP_SCHEMA_VERSION =
  "result-share-registry-presets-backup.v1";
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
const unsafeFieldPattern =
  /(^|_)(token|secret|password|hash|rawalias|rawsharetoken|localpath|absolutepath|sourcefile)(_|$)|rawAlias|rawShareToken|localPath|absolutePath|sourceFile|alias_hash|token_hash/i;

const presetLocalAuditActionTypes: ResultShareRegistryPresetLocalAuditActionType[] = [
  "preset_saved",
  "preset_applied",
  "preset_overwritten",
  "preset_deleted",
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
    byActionType.backup_created + byActionType.backup_restored;
  const recoveryRelatedCount =
    byActionType.invalid_presets_discarded +
    byActionType.scope_reset +
    byActionType.all_presets_reset +
    byActionType.dangling_default_cleared +
    byActionType.backup_restored +
    byActionType.recovery_failed;
  const importRelatedCount =
    byActionType.import_dry_run +
    byActionType.import_merge +
    byActionType.import_replace +
    byActionType.validation_failed;
  const exportRelatedCount = byActionType.export_created;

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
    },
    grantPresetCount: report.grantPresetCount,
    aliasPresetCount: report.aliasPresetCount,
    validPresetCount: report.validPresetCount,
    invalidPresetCount: report.invalidPresetCount,
    defaultPresetIdPresent: defaultPresetId !== null,
    lastBackupPresent: lastGoodBackup !== null,
    latestValidationAt: report.checkedAt,
    warningCount: report.warningCount,
    errorCount: report.errorCount,
    notes: [
      "Diagnostics inspect browser-local preset storage only.",
      lastGoodBackup
        ? `Last-good backup available from ${lastGoodBackup.createdAt}.`
        : "No last-good backup snapshot is stored yet.",
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
): {
  grantPresets: ResultShareRegistrySavedViewSummary[];
  aliasPresets: ResultShareRegistrySavedViewSummary[];
  defaultPreset: ResultShareRegistrySavedViewSummary | null;
} {
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
