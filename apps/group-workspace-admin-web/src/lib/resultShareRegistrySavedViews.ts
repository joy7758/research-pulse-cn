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
  ResultShareRegistryPresetExportPayload,
  ResultShareRegistryPresetImportApplyResult,
  ResultShareRegistryPresetImportMode,
  ResultShareRegistryPresetImportPreview,
  ResultShareRegistrySavedViewApplyMode,
  ResultShareRegistrySavedView,
  ResultShareRegistrySavedViewDrilldownContext,
  ResultShareRegistrySavedViewDraft,
  ResultShareRegistrySavedViewScope,
  ResultShareRegistrySavedViewStoreState,
  ResultShareRegistrySavedViewSummary,
  ResultShareRegistrySortInput,
} from "./types";

export const RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY = "resultShareRegistryGrantPresets";
export const RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY = "resultShareRegistryAliasPresets";
export const RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY =
  "resultShareRegistryDefaultPresetId";
export const RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION =
  "result-share-registry-presets.v1";

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

function parseSavedViewList(
  raw: string | null,
  scope: ResultShareRegistrySavedViewScope,
): ResultShareRegistrySavedView[] {
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((item) => normalizeSavedView(item, scope))
      .filter((item): item is ResultShareRegistrySavedView => item !== null);
  } catch {
    return [];
  }
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
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

export function loadResultShareRegistrySavedViewStore(
  storage: Storage | null | undefined,
): ResultShareRegistrySavedViewStoreState {
  if (!storage) {
    return {
      grantPresets: [],
      aliasPresets: [],
      defaultPresetId: null,
    };
  }

  const store: ResultShareRegistrySavedViewStoreState = {
    grantPresets: parseSavedViewList(
      storage.getItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY),
      "grant_registry",
    ),
    aliasPresets: parseSavedViewList(
      storage.getItem(RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY),
      "alias_registry",
    ),
    defaultPresetId: storage.getItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY),
  };

  return findSavedViewById(store, store.defaultPresetId)
    ? store
    : {
        ...store,
        defaultPresetId: null,
      };
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
