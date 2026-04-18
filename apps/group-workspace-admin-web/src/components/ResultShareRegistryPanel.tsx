import {
  parseResultShareRegistrySectionSortInput,
  RESULT_SHARE_REGISTRY_ALIAS_STATUS_OPTIONS,
  RESULT_SHARE_REGISTRY_GRANT_STATUS_OPTIONS,
  RESULT_SHARE_REGISTRY_SHARE_KIND_OPTIONS,
  RESULT_SHARE_REGISTRY_SORT_OPTIONS,
  serializeResultShareRegistrySectionSortInput,
} from "../lib/resultShareRegistryFilters";
import type {
  ApiErrorViewModel,
  ResultShareRegistryPresetBackupSnapshot,
  ResultShareAliasRegistryItemViewModel,
  ResultShareGrantRegistryItemViewModel,
  ResultShareRegistryFilterInput,
  ResultShareRegistryPresetImportMode,
  ResultShareRegistryPresetImportPreview,
  ResultShareRegistryPresetIntegrityIssue,
  ResultShareRegistryPresetIntegrityReport,
  ResultShareRegistryPresetRecoveryAction,
  ResultShareRegistryPresetStorageDiagnostics,
  ResultShareRegistryFilterSummaryViewModel,
  ResultShareRegistrySavedViewApplyMode,
  ResultShareRegistrySavedViewScope,
  ResultShareRegistrySavedViewSummary,
  ResultShareRegistrySortInput,
  ResultShareRegistrySummaryViewModel,
  ResultShareRegistryViewModel,
} from "../lib/types";

type ResultShareRegistryPanelProps = {
  filters: ResultShareRegistryFilterInput;
  sorts: ResultShareRegistrySortInput;
  filterSummary: ResultShareRegistryFilterSummaryViewModel;
  savedViewDrafts: {
    grantName: string;
    aliasName: string;
    grantIncludeDrilldown: boolean;
    aliasIncludeDrilldown: boolean;
  };
  savedViews: {
    grantPresets: ResultShareRegistrySavedViewSummary[];
    aliasPresets: ResultShareRegistrySavedViewSummary[];
    defaultPreset: ResultShareRegistrySavedViewSummary | null;
  };
  presetTransfer: {
    importMode: ResultShareRegistryPresetImportMode;
    preview: ResultShareRegistryPresetImportPreview | null;
  };
  presetSafety: {
    integrityReport: ResultShareRegistryPresetIntegrityReport;
    diagnostics: ResultShareRegistryPresetStorageDiagnostics;
    lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null;
  };
  registry: ResultShareRegistryViewModel | null;
  currentTargetLabel: string | null;
  activePresetLabel: string | null;
  activeDrilldownContextLabel: string;
  loading: boolean;
  error: ApiErrorViewModel | null;
  onFilterChange: (patch: Partial<ResultShareRegistryFilterInput>) => void;
  onSortChange: (patch: Partial<ResultShareRegistrySortInput>) => void;
  onSavedViewDraftChange: (scope: ResultShareRegistrySavedViewScope, name: string) => void;
  onSavedViewIncludeDrilldownChange: (
    scope: ResultShareRegistrySavedViewScope,
    include: boolean,
  ) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  onSaveSavedView: (scope: ResultShareRegistrySavedViewScope) => void;
  onApplySavedView: (
    scope: ResultShareRegistrySavedViewScope,
    presetId: string,
    mode: ResultShareRegistrySavedViewApplyMode,
  ) => void;
  onOverwriteSavedView: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onDeleteSavedView: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onSetDefaultSavedView: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onClearDefaultSavedView: () => void;
  onRestoreDefaultSavedView: () => void;
  onResetDrilldownContext: () => void;
  onPresetImportModeChange: (mode: ResultShareRegistryPresetImportMode) => void;
  onImportPresetFile: (file: File | null) => void;
  onApplyPresetImport: () => void;
  onClearPresetImportPreview: () => void;
  onExportPresets: () => void;
  onValidatePresetStorage: () => void;
  onRunPresetRecoveryAction: (action: ResultShareRegistryPresetRecoveryAction) => void;
  onOpenGrantDrilldown: (grantId: string) => void;
  onOpenAliasDrilldown: (aliasId: string) => void;
  onFilterAliasesForGrant: (grantId: string, shareKind: ResultShareGrantRegistryItemViewModel["shareKind"]) => void;
};

function SummaryCardList({ items }: { items: ResultShareRegistrySummaryViewModel[] }) {
  return (
    <div className="stat-grid">
      {items.map((item) => (
        <article key={item.label} className="stat-card">
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.hint ? <p className="stat-hint">{item.hint}</p> : null}
        </article>
      ))}
    </div>
  );
}

function ImportPreviewPanel({
  preview,
  importMode,
  onImportModeChange,
  onApply,
  onClear,
}: {
  preview: ResultShareRegistryPresetImportPreview | null;
  importMode: ResultShareRegistryPresetImportMode;
  onImportModeChange: (mode: ResultShareRegistryPresetImportMode) => void;
  onApply: () => void;
  onClear: () => void;
}) {
  if (!preview) {
    return (
      <div className="empty-state">
        <strong>No import preview yet.</strong>
        <p>Select a local preset JSON file to validate it before applying merge or replace.</p>
      </div>
    );
  }

  return (
    <section className="conversion-section-card">
      <div className="conversion-section-header">
        <div>
          <h3>Import preview</h3>
          <p className="section-subtle-copy">
            Validation runs before local preset storage is changed. Invalid files do not mutate browser state.
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <article className="stat-card">
          <span>Schema</span>
          <strong>{preview.schemaVersion ?? "Missing"}</strong>
        </article>
        <article className="stat-card">
          <span>Valid presets</span>
          <strong>{preview.validPresetCount}</strong>
        </article>
        <article className="stat-card">
          <span>Invalid presets</span>
          <strong>{preview.invalidPresetCount}</strong>
        </article>
        <article className="stat-card">
          <span>Grant presets</span>
          <strong>{preview.grantPresetCount}</strong>
        </article>
        <article className="stat-card">
          <span>Alias presets</span>
          <strong>{preview.aliasPresetCount}</strong>
        </article>
      </div>

      <div className="button-row">
        <label className="field-stack">
          <span>Import mode</span>
          <select
            value={importMode}
            onChange={(event) =>
              onImportModeChange(event.target.value as ResultShareRegistryPresetImportMode)
            }
          >
            <option value="merge">Merge imported presets</option>
            <option value="replace">Replace imported scopes</option>
          </select>
        </label>
      </div>

      <ul className="filter-chip-list">
        <li className="filter-chip">
          <strong>
            {preview.importedScopes.grantRegistry ? "Grant scope present" : "Grant scope absent"}
          </strong>
        </li>
        <li className="filter-chip">
          <strong>
            {preview.importedScopes.aliasRegistry ? "Alias scope present" : "Alias scope absent"}
          </strong>
        </li>
      </ul>

      {preview.warnings.length > 0 ? (
        <div className="inline-banner info">
          <strong>Validation warnings</strong>
          <ul className="note-list">
            {preview.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {preview.errors.length > 0 ? (
        <div className="inline-banner error" role="alert">
          <strong>Validation errors</strong>
          <ul className="note-list">
            {preview.errors.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="button-row">
        <button
          type="button"
          className="button-primary"
          disabled={!preview.canApply}
          onClick={onApply}
        >
          Apply import
        </button>
        <button type="button" className="button-secondary" onClick={onClear}>
          Clear import preview
        </button>
      </div>
    </section>
  );
}

function SavedViewList({
  scope,
  title,
  description,
  draftName,
  includeDrilldownContext,
  presets,
  onDraftChange,
  onIncludeDrilldownChange,
  onSave,
  onApply,
  onOverwrite,
  onDelete,
  onSetDefault,
}: {
  scope: ResultShareRegistrySavedViewScope;
  title: string;
  description: string;
  draftName: string;
  includeDrilldownContext: boolean;
  presets: ResultShareRegistrySavedViewSummary[];
  onDraftChange: (name: string) => void;
  onIncludeDrilldownChange: (include: boolean) => void;
  onSave: () => void;
  onApply: (presetId: string, mode: ResultShareRegistrySavedViewApplyMode) => void;
  onOverwrite: (presetId: string) => void;
  onDelete: (presetId: string) => void;
  onSetDefault: (presetId: string) => void;
}) {
  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h3>{title}</h3>
          <p className="section-subtle-copy">{description}</p>
        </div>
      </div>

      <div className="saved-view-toolbar">
        <label className="field-stack">
          <span>{scope === "grant_registry" ? "Grant preset name" : "Alias preset name"}</span>
          <input
            type="text"
            placeholder={
              scope === "grant_registry"
                ? "e.g. Active workspace-board grants"
                : "e.g. Grant-specific alias follow-up"
            }
            value={draftName}
            onChange={(event) => onDraftChange(event.target.value)}
          />
        </label>
        <div className="field-stack">
          <span>Saved preset options</span>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={includeDrilldownContext}
              onChange={(event) => onIncludeDrilldownChange(event.target.checked)}
            />
            <span>Include current per-share drilldown filters</span>
          </label>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="button-primary"
            onClick={onSave}
            disabled={draftName.trim().length === 0}
          >
            {scope === "grant_registry" ? "Save current grant view" : "Save current alias view"}
          </button>
        </div>
      </div>

      {presets.length === 0 ? (
        <div className="empty-state">
          <strong>No saved views yet.</strong>
          <p>
            Saved views are local to this browser profile and contain only safe registry filter,
            sort, and optional drilldown-filter state.
          </p>
        </div>
      ) : (
        <ul className="data-list">
          {presets.map((preset) => (
            <li key={preset.id} className="data-list-item">
              <div className="registry-item-stack">
                <div className="registry-item-header">
                  <div>
                    <strong>{preset.name}</strong>
                    <p>
                      {preset.scope === "grant_registry" ? "Grant registry preset" : "Alias registry preset"} ·
                      {" "}
                      updated {preset.updatedAt}
                    </p>
                  </div>
                  {preset.isDefault ? <span className="status-pill active">Default</span> : null}
                </div>
                <ul className="filter-chip-list">
                  {preset.summaryItems.map((item) => (
                    <li key={`${preset.id}-${item}`} className="filter-chip">
                      <strong>{item}</strong>
                    </li>
                  ))}
                </ul>
                {preset.hasDrilldownContext ? (
                  <>
                    <p className="section-subtle-copy">
                      Linked per-share drilldown context
                    </p>
                    <ul className="filter-chip-list">
                      {preset.drilldownSummaryItems.map((item) => (
                        <li key={`${preset.id}-drilldown-${item}`} className="filter-chip">
                          <strong>{item}</strong>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onApply(preset.id, "registry_only")}
                >
                  Apply registry only
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onApply(preset.id, "registry_and_drilldown")}
                  disabled={!preset.hasDrilldownContext}
                >
                  {preset.hasDrilldownContext
                    ? "Apply registry + drilldown"
                    : "No drilldown context saved"}
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onOverwrite(preset.id)}
                >
                  Overwrite with current view
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onSetDefault(preset.id)}
                  disabled={preset.isDefault}
                >
                  {preset.isDefault ? "Default preset" : "Make default"}
                </button>
                <button
                  type="button"
                  className="button-danger"
                  onClick={() => onDelete(preset.id)}
                >
                  Delete preset
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function hasScopeIssue(
  issues: ResultShareRegistryPresetIntegrityIssue[],
  scope: ResultShareRegistrySavedViewScope,
): boolean {
  const keyName =
    scope === "grant_registry"
      ? "resultShareRegistryGrantPresets"
      : "resultShareRegistryAliasPresets";
  return issues.some(
    (issue) =>
      issue.scope === scope ||
      (issue.scope === "storage" && issue.safeDetails === keyName),
  );
}

function PresetDiagnosticsPanel({
  integrityReport,
  diagnostics,
  lastGoodBackup,
  onValidate,
  onRecover,
}: {
  integrityReport: ResultShareRegistryPresetIntegrityReport;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
  lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null;
  onValidate: () => void;
  onRecover: (action: ResultShareRegistryPresetRecoveryAction) => void;
}) {
  const hasGrantIssues = hasScopeIssue(integrityReport.issues, "grant_registry");
  const hasAliasIssues = hasScopeIssue(integrityReport.issues, "alias_registry");
  const hasDanglingDefault = integrityReport.issues.some(
    (issue) => issue.code === "dangling_default_preset",
  );

  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h3>Preset storage diagnostics</h3>
          <p className="section-subtle-copy">
            Local-only integrity checks over browser preset storage. This does not touch backend
            data, share payloads, or admin bearer tokens.
          </p>
        </div>
        <div className="button-row">
          <button type="button" className="button-secondary" onClick={onValidate}>
            Run integrity check
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => onRecover("restore_last_good_backup")}
            disabled={lastGoodBackup === null}
          >
            Restore last-good backup
          </button>
        </div>
      </div>

      <SummaryCardList
        items={[
          { label: "Grant presets", value: diagnostics.grantPresetCount, hint: null },
          { label: "Alias presets", value: diagnostics.aliasPresetCount, hint: null },
          { label: "Valid presets", value: diagnostics.validPresetCount, hint: null },
          { label: "Invalid presets", value: diagnostics.invalidPresetCount, hint: null },
          { label: "Warnings", value: diagnostics.warningCount, hint: null },
          { label: "Errors", value: diagnostics.errorCount, hint: null },
        ]}
      />

      <ul className="filter-chip-list">
        <li className="filter-chip">
          <span>Grant key</span>
          <strong>{diagnostics.storageKeysPresent.grantPresets ? "Present" : "Missing"}</strong>
        </li>
        <li className="filter-chip">
          <span>Alias key</span>
          <strong>{diagnostics.storageKeysPresent.aliasPresets ? "Present" : "Missing"}</strong>
        </li>
        <li className="filter-chip">
          <span>Default marker</span>
          <strong>{diagnostics.defaultPresetIdPresent ? "Present" : "Missing"}</strong>
        </li>
        <li className="filter-chip">
          <span>Last backup</span>
          <strong>{diagnostics.lastBackupPresent ? "Available" : "Not stored"}</strong>
        </li>
        <li className="filter-chip">
          <span>Validated at</span>
          <strong>{diagnostics.latestValidationAt ?? diagnostics.checkedAt}</strong>
        </li>
      </ul>

      {lastGoodBackup ? (
        <div className="inline-banner info">
          <strong>Last-good backup</strong>
          <span>
            {lastGoodBackup.createdAt} · {lastGoodBackup.reason}
          </span>
        </div>
      ) : null}

      {integrityReport.issues.length > 0 ? (
        <ul className="data-list">
          {integrityReport.issues.map((issue, index) => (
            <li
              key={`${issue.code}-${issue.scope}-${issue.presetId ?? "none"}-${index}`}
              className="data-list-item"
            >
              <div className="registry-item-stack">
                <div className="registry-item-header">
                  <div>
                    <strong>{issue.message}</strong>
                    <p>
                      {issue.scope} · {issue.code}
                      {issue.presetName ? ` · ${issue.presetName}` : ""}
                    </p>
                  </div>
                  <span className={`status-pill ${issue.severity === "error" ? "revoked" : "active"}`}>
                    {issue.severity}
                  </span>
                </div>
                {issue.safeDetails ? (
                  <p className="section-subtle-copy">Details: {issue.safeDetails}</p>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty-state">
          <strong>No integrity issues detected.</strong>
          <p>Current browser preset storage passed the latest local validation run.</p>
        </div>
      )}

      <div className="button-row">
        <button
          type="button"
          className="button-secondary"
          onClick={() => onRecover("discard_invalid_grant_presets")}
          disabled={!hasGrantIssues}
        >
          Discard invalid grant presets
        </button>
        <button
          type="button"
          className="button-secondary"
          onClick={() => onRecover("discard_invalid_alias_presets")}
          disabled={!hasAliasIssues}
        >
          Discard invalid alias presets
        </button>
        <button
          type="button"
          className="button-secondary"
          onClick={() => onRecover("clear_dangling_default_preset")}
          disabled={!hasDanglingDefault}
        >
          Clear dangling default
        </button>
      </div>

      <div className="button-row">
        <button
          type="button"
          className="button-danger"
          onClick={() => onRecover("reset_grant_scope")}
          disabled={!integrityReport.canResetGrantScope}
        >
          Reset grant preset scope
        </button>
        <button
          type="button"
          className="button-danger"
          onClick={() => onRecover("reset_alias_scope")}
          disabled={!integrityReport.canResetAliasScope}
        >
          Reset alias preset scope
        </button>
        <button
          type="button"
          className="button-danger"
          onClick={() => onRecover("reset_all_presets")}
          disabled={
            diagnostics.grantPresetCount === 0 &&
            diagnostics.aliasPresetCount === 0 &&
            !hasGrantIssues &&
            !hasAliasIssues &&
            !hasDanglingDefault
          }
        >
          Reset all registry presets
        </button>
      </div>

      <ul className="note-list">
        {diagnostics.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
        {integrityReport.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

function GrantRegistryList({
  items,
  emptyState,
  onOpenGrantDrilldown,
  onFilterAliasesForGrant,
}: {
  items: ResultShareGrantRegistryItemViewModel[];
  emptyState: ResultShareRegistryViewModel["grants"]["emptyState"];
  onOpenGrantDrilldown: (grantId: string) => void;
  onFilterAliasesForGrant: (grantId: string, shareKind: ResultShareGrantRegistryItemViewModel["shareKind"]) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>{emptyState.title}</strong>
        <p>{emptyState.message}</p>
      </div>
    );
  }

  return (
    <ul className="data-list">
      {items.map((item) => (
        <li key={item.grantId} className="data-list-item">
          <div className="registry-item-stack">
            <div className="registry-item-header">
              <div>
                <strong>{item.title}</strong>
                <p>{item.subtitle}</p>
              </div>
              <span className={`status-pill ${item.status}`}>{item.status}</span>
            </div>
            <dl className="registry-meta-grid">
              <div className="metric-kv-item">
                <dt>Grant</dt>
                <dd>{item.grantId}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Share kind</dt>
                <dd>{item.shareKind}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Relation</dt>
                <dd>{item.relationshipHint}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Expires at</dt>
                <dd>{item.expiresAt ?? "No expiry"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Last used</dt>
                <dd>{item.lastUsedAt ?? "Never"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Created at</dt>
                <dd>{item.createdAt}</dd>
              </div>
            </dl>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenGrantDrilldown(item.grantId)}
            >
              Open grant drilldown
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => onFilterAliasesForGrant(item.grantId, item.shareKind)}
            >
              Show aliases for this grant
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function AliasRegistryList({
  items,
  emptyState,
  onOpenGrantDrilldown,
  onOpenAliasDrilldown,
}: {
  items: ResultShareAliasRegistryItemViewModel[];
  emptyState: ResultShareRegistryViewModel["aliases"]["emptyState"];
  onOpenGrantDrilldown: (grantId: string) => void;
  onOpenAliasDrilldown: (aliasId: string) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>{emptyState.title}</strong>
        <p>{emptyState.message}</p>
      </div>
    );
  }

  return (
    <ul className="data-list">
      {items.map((item) => (
        <li key={item.aliasId} className="data-list-item">
          <div className="registry-item-stack">
            <div className="registry-item-header">
              <div>
                <strong>{item.title}</strong>
                <p>{item.subtitle}</p>
              </div>
              <span className={`status-pill ${item.status}`}>{item.status}</span>
            </div>
            <dl className="registry-meta-grid">
              <div className="metric-kv-item">
                <dt>Alias</dt>
                <dd>{item.aliasId}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Prefix</dt>
                <dd>{item.aliasPrefix ?? "Hidden"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Linked grant</dt>
                <dd>{item.relationshipHint}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Grant listed</dt>
                <dd>{item.linkedGrantInRegistry ? "Yes" : "Not in current grant rows"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Expires at</dt>
                <dd>{item.expiresAt ?? "No expiry"}</dd>
              </div>
              <div className="metric-kv-item">
                <dt>Last used</dt>
                <dd>{item.lastUsedAt ?? "Never"}</dd>
              </div>
            </dl>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenAliasDrilldown(item.aliasId)}
            >
              Open alias drilldown
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => onOpenGrantDrilldown(item.grantId)}
            >
              Open linked grant
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ResultShareRegistryPanel({
  filters,
  sorts,
  filterSummary,
  savedViewDrafts,
  savedViews,
  presetTransfer,
  presetSafety,
  registry,
  currentTargetLabel,
  activePresetLabel,
  activeDrilldownContextLabel,
  loading,
  error,
  onFilterChange,
  onSortChange,
  onSavedViewDraftChange,
  onSavedViewIncludeDrilldownChange,
  onApplyFilters,
  onResetFilters,
  onSaveSavedView,
  onApplySavedView,
  onOverwriteSavedView,
  onDeleteSavedView,
  onSetDefaultSavedView,
  onClearDefaultSavedView,
  onRestoreDefaultSavedView,
  onResetDrilldownContext,
  onPresetImportModeChange,
  onImportPresetFile,
  onApplyPresetImport,
  onClearPresetImportPreview,
  onExportPresets,
  onValidatePresetStorage,
  onRunPresetRecoveryAction,
  onOpenGrantDrilldown,
  onOpenAliasDrilldown,
  onFilterAliasesForGrant,
}: ResultShareRegistryPanelProps) {
  return (
    <section className="panel-card">
      <div className="panel-card-header">
        <div>
          <p className="eyebrow">Per-share registry</p>
          <h2>Result share registry</h2>
          <p className="panel-copy">
            Browse safe share-grant and alias rows, then quick-open the existing read-only
            per-share drilldown without manual ID entry.
          </p>
        </div>
        {currentTargetLabel ? (
          <div className="hero-chip registry-current-target">
            <span>Current drilldown</span>
            <strong>{currentTargetLabel}</strong>
          </div>
        ) : null}
      </div>

        <div className="button-row">
          {activePresetLabel ? (
            <div className="meta-chip">
            <span>Active registry preset</span>
            <strong>{activePresetLabel}</strong>
          </div>
        ) : null}
        <div className="meta-chip">
          <span>Drilldown context</span>
          <strong>{activeDrilldownContextLabel}</strong>
        </div>
        <button
          type="button"
          className="button-secondary"
          onClick={onResetDrilldownContext}
        >
          Reset drilldown context
        </button>
      </div>

      <div className="filter-grid">
        <label className="field-stack">
          <span>Share kind</span>
          <select
            value={filters.shareKind ?? ""}
            onChange={(event) =>
              onFilterChange({
                shareKind:
                  event.target.value === ""
                    ? null
                    : (event.target.value as ResultShareRegistryFilterInput["shareKind"]),
              })
            }
          >
            <option value="">All share kinds</option>
            {RESULT_SHARE_REGISTRY_SHARE_KIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Grant status</span>
          <select
            value={filters.grantStatus ?? ""}
            onChange={(event) =>
              onFilterChange({
                grantStatus:
                  event.target.value === ""
                    ? null
                    : (event.target.value as ResultShareRegistryFilterInput["grantStatus"]),
              })
            }
          >
            <option value="">All grant statuses</option>
            {RESULT_SHARE_REGISTRY_GRANT_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Alias status</span>
          <select
            value={filters.aliasStatus ?? ""}
            onChange={(event) =>
              onFilterChange({
                aliasStatus:
                  event.target.value === ""
                    ? null
                    : (event.target.value as ResultShareRegistryFilterInput["aliasStatus"]),
              })
            }
          >
            <option value="">All alias statuses</option>
            {RESULT_SHARE_REGISTRY_ALIAS_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Workspace ID</span>
          <input
            type="text"
            placeholder="grant registry only"
            value={filters.workspaceId ?? ""}
            onChange={(event) => onFilterChange({ workspaceId: event.target.value })}
          />
        </label>

        <label className="field-stack">
          <span>Grant ID</span>
          <input
            type="text"
            placeholder="alias registry only"
            value={filters.resultShareGrantId ?? ""}
            onChange={(event) => onFilterChange({ resultShareGrantId: event.target.value })}
          />
        </label>

        <label className="field-stack">
          <span>Grant sort</span>
          <select
            value={serializeResultShareRegistrySectionSortInput(sorts.grants)}
            onChange={(event) =>
              onSortChange({
                grants: parseResultShareRegistrySectionSortInput(event.target.value),
              })
            }
          >
            {RESULT_SHARE_REGISTRY_SORT_OPTIONS.map((option) => (
              <option key={`grant-${option.key}`} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field-stack">
          <span>Alias sort</span>
          <select
            value={serializeResultShareRegistrySectionSortInput(sorts.aliases)}
            onChange={(event) =>
              onSortChange({
                aliases: parseResultShareRegistrySectionSortInput(event.target.value),
              })
            }
          >
            {RESULT_SHARE_REGISTRY_SORT_OPTIONS.map((option) => (
              <option key={`alias-${option.key}`} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="button-row">
        <button type="button" className="button-primary" disabled={loading} onClick={onApplyFilters}>
          {loading ? "Loading..." : "Apply filters"}
        </button>
        <button type="button" className="button-secondary" disabled={loading} onClick={onResetFilters}>
          Clear current filters
        </button>
      </div>

      <section className="filter-summary-card">
        <div className="conversion-section-header">
          <h3>Applied registry filters and sort</h3>
          <p className="section-subtle-copy">
            Grant-only and alias-only filters stay explicit, while each registry keeps its own
            stable sort mode.
          </p>
        </div>
        {filterSummary.chips.length > 0 ? (
          <ul className="filter-chip-list">
            {filterSummary.chips.map((chip) => (
              <li key={chip.key} className="filter-chip">
                <span>{chip.label}</span>
                <strong>{chip.value}</strong>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">No registry filters are active.</div>
        )}
        <ul className="note-list">
          {filterSummary.scopeNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>

      <section className="conversion-notes-card saved-view-shell">
        <div className="conversion-section-header">
          <div>
            <h3>Saved views</h3>
            <p className="section-subtle-copy">
              Local-only presets for safe registry filters and sorts. These views never include
              admin bearer tokens or share payloads. Import/export only touches local preset JSON.
            </p>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={onExportPresets}
            >
              Export presets JSON
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={onRestoreDefaultSavedView}
              disabled={savedViews.defaultPreset === null}
            >
              Restore default view
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={onClearDefaultSavedView}
              disabled={savedViews.defaultPreset === null}
            >
              Clear default marker
            </button>
          </div>
        </div>
        {savedViews.defaultPreset ? (
          <div className="meta-chip saved-view-default-chip">
            <span>Default local view</span>
            <strong>{savedViews.defaultPreset.name}</strong>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No default saved view is set.</strong>
            <p>Mark one preset as default if you want a one-click restore target for the registry.</p>
          </div>
        )}

        <div className="split-grid">
          <SavedViewList
            scope="grant_registry"
            title="Grant saved views"
            description="Store common grant-registry filters and grant sort modes locally in this browser."
            draftName={savedViewDrafts.grantName}
            includeDrilldownContext={savedViewDrafts.grantIncludeDrilldown}
            presets={savedViews.grantPresets}
            onDraftChange={(name) => onSavedViewDraftChange("grant_registry", name)}
            onIncludeDrilldownChange={(include) =>
              onSavedViewIncludeDrilldownChange("grant_registry", include)
            }
            onSave={() => onSaveSavedView("grant_registry")}
            onApply={(presetId, mode) => onApplySavedView("grant_registry", presetId, mode)}
            onOverwrite={(presetId) => onOverwriteSavedView("grant_registry", presetId)}
            onDelete={(presetId) => onDeleteSavedView("grant_registry", presetId)}
            onSetDefault={(presetId) => onSetDefaultSavedView("grant_registry", presetId)}
          />
          <SavedViewList
            scope="alias_registry"
            title="Alias saved views"
            description="Store common alias-registry filters and alias sort modes locally in this browser."
            draftName={savedViewDrafts.aliasName}
            includeDrilldownContext={savedViewDrafts.aliasIncludeDrilldown}
            presets={savedViews.aliasPresets}
            onDraftChange={(name) => onSavedViewDraftChange("alias_registry", name)}
            onIncludeDrilldownChange={(include) =>
              onSavedViewIncludeDrilldownChange("alias_registry", include)
            }
            onSave={() => onSaveSavedView("alias_registry")}
            onApply={(presetId, mode) => onApplySavedView("alias_registry", presetId, mode)}
            onOverwrite={(presetId) => onOverwriteSavedView("alias_registry", presetId)}
            onDelete={(presetId) => onDeleteSavedView("alias_registry", presetId)}
            onSetDefault={(presetId) => onSetDefaultSavedView("alias_registry", presetId)}
          />
        </div>

        <section className="conversion-section-card saved-view-card">
          <div className="conversion-section-header">
            <div>
              <h3>Preset import / export</h3>
              <p className="section-subtle-copy">
                Local JSON only. Selecting a file is validation-only until you explicitly apply a
                merge or replace action. No backend sync, no team sharing, no bearer token
                persistence.
              </p>
            </div>
          </div>
          <label className="field-stack">
            <span>Import preset JSON file</span>
            <input
              type="file"
              accept=".json,application/json"
              onChange={(event) => onImportPresetFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <ImportPreviewPanel
            preview={presetTransfer.preview}
            importMode={presetTransfer.importMode}
            onImportModeChange={onPresetImportModeChange}
            onApply={onApplyPresetImport}
            onClear={onClearPresetImportPreview}
          />
        </section>

        <PresetDiagnosticsPanel
          integrityReport={presetSafety.integrityReport}
          diagnostics={presetSafety.diagnostics}
          lastGoodBackup={presetSafety.lastGoodBackup}
          onValidate={onValidatePresetStorage}
          onRecover={onRunPresetRecoveryAction}
        />
      </section>

      {error ? (
        <div className="inline-banner error" role="alert">
          <strong>{error.title}</strong>
          <span>{error.message}</span>
        </div>
      ) : null}

      {loading && registry === null ? (
        <div className="empty-state">Loading read-only share registries...</div>
      ) : null}

      {registry ? (
        <div className="split-grid">
          <section className="conversion-section-card">
            <div className="conversion-section-header">
              <h3>{registry.grants.title}</h3>
              <p className="section-subtle-copy">{registry.grants.description}</p>
            </div>
            <SummaryCardList items={registry.grants.summaryMetrics} />
            <GrantRegistryList
              items={registry.grants.items}
              emptyState={registry.grants.emptyState}
              onOpenGrantDrilldown={onOpenGrantDrilldown}
              onFilterAliasesForGrant={onFilterAliasesForGrant}
            />
          </section>

          <section className="conversion-section-card">
            <div className="conversion-section-header">
              <h3>{registry.aliases.title}</h3>
              <p className="section-subtle-copy">{registry.aliases.description}</p>
            </div>
            <SummaryCardList items={registry.aliases.summaryMetrics} />
            <AliasRegistryList
              items={registry.aliases.items}
              emptyState={registry.aliases.emptyState}
              onOpenGrantDrilldown={onOpenGrantDrilldown}
              onOpenAliasDrilldown={onOpenAliasDrilldown}
            />
          </section>
        </div>
      ) : null}
    </section>
  );
}
