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
  ResultShareRegistryPresetWorkspaceBackupSnapshot,
  ResultShareRegistryPresetWorkspaceHealthReportExportFormat,
  ResultShareRegistryPresetWorkspaceHealthReportPreview,
  ResultShareRegistryPresetWorkspaceHealthThresholdDraft,
  ResultShareRegistryPresetWorkspaceHealthThresholdPreferences,
  ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult,
  ResultShareRegistryPresetWorkspaceHealthThresholdPreview,
  ResultShareRegistryPresetWorkspaceHealthScore,
  ResultShareRegistryPresetWorkspaceHealthRecommendation,
  ResultShareAliasRegistryItemViewModel,
  ResultShareGrantRegistryItemViewModel,
  ResultShareRegistryFilterInput,
  ResultShareRegistryPresetImportMode,
  ResultShareRegistryPresetImportPreview,
  ResultShareRegistryPresetIntegrityIssue,
  ResultShareRegistryPresetIntegrityReport,
  ResultShareRegistryPresetLocalAuditSummary,
  ResultShareRegistryPresetRecoveryAction,
  ResultShareRegistryPresetStorageDiagnostics,
  ResultShareRegistryPresetWorkspaceViewModel,
  ResultShareRegistryPresetWorkspaceImportPreview,
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
  presetAudit: {
    summary: ResultShareRegistryPresetLocalAuditSummary;
  };
  presetWorkspace: {
    viewModel: ResultShareRegistryPresetWorkspaceViewModel;
    healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
    healthReport: ResultShareRegistryPresetWorkspaceHealthReportPreview;
    healthThresholds: {
      current: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences;
      draft: ResultShareRegistryPresetWorkspaceHealthThresholdDraft;
      validation: ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult;
      preview: ResultShareRegistryPresetWorkspaceHealthThresholdPreview | null;
      storageWarning: string | null;
    };
    transfer: {
      importMode: ResultShareRegistryPresetImportMode;
      preview: ResultShareRegistryPresetWorkspaceImportPreview | null;
      lastGoodBackup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null;
    };
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
  onClearPresetAudit: () => void;
  onPresetWorkspaceImportModeChange: (mode: ResultShareRegistryPresetImportMode) => void;
  onImportPresetWorkspaceFile: (file: File | null) => void;
  onApplyPresetWorkspaceImport: () => void;
  onClearPresetWorkspaceImportPreview: () => void;
  onExportPresetWorkspace: () => void;
  onRestorePresetWorkspaceBackup: () => void;
  onRecalculatePresetWorkspaceHealth: () => void;
  onExportPresetWorkspaceHealthReport: (
    format: ResultShareRegistryPresetWorkspaceHealthReportExportFormat,
  ) => void;
  onHealthThresholdDraftChange: (
    field: "healthyMin" | "attentionMin" | "riskMin" | "criticalMin",
    value: string,
  ) => void;
  onHealthPenaltyOverrideDraftChange: (
    key:
      | "stalePinnedPreset"
      | "missingPresetBackup"
      | "missingWorkspaceBackup"
      | "recentFailedImport"
      | "recentFailedRecovery",
    value: string,
  ) => void;
  onHealthVisibilityChange: (
    field: "showInfo" | "showWarnings" | "showErrors" | "showCritical",
    value: boolean,
  ) => void;
  onApplyHealthThresholds: () => void;
  onResetHealthThresholds: () => void;
  onPinSavedView: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onUnpinSavedView: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onMovePinnedSavedView: (
    scope: ResultShareRegistrySavedViewScope,
    presetId: string,
    direction: "up" | "down",
  ) => void;
  onClearWorkspacePins: () => void;
  onResetWorkspace: () => void;
  onCleanStaleWorkspacePins: () => void;
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

function WorkspaceImportPreviewPanel({
  preview,
  importMode,
  onImportModeChange,
  onApply,
  onClear,
}: {
  preview: ResultShareRegistryPresetWorkspaceImportPreview | null;
  importMode: ResultShareRegistryPresetImportMode;
  onImportModeChange: (mode: ResultShareRegistryPresetImportMode) => void;
  onApply: () => void;
  onClear: () => void;
}) {
  if (!preview) {
    return (
      <div className="empty-state">
        <strong>No workspace import preview yet.</strong>
        <p>
          Select a local preset workspace JSON file to validate browser-only pinning and
          organization state before applying merge or replace.
        </p>
      </div>
    );
  }

  return (
    <section className="conversion-section-card">
      <div className="conversion-section-header">
        <div>
          <h4>Workspace import preview</h4>
          <p className="section-subtle-copy">
            This validates local workspace organization only. Saved preset definitions are not
            included and are never overwritten here.
          </p>
        </div>
      </div>

      <div className="stat-grid">
        <article className="stat-card">
          <span>Schema</span>
          <strong>{preview.schemaVersion ?? "Missing"}</strong>
        </article>
        <article className="stat-card">
          <span>Grant pins</span>
          <strong>{preview.pinnedGrantPresetCount}</strong>
        </article>
        <article className="stat-card">
          <span>Alias pins</span>
          <strong>{preview.pinnedAliasPresetCount}</strong>
        </article>
        <article className="stat-card">
          <span>Last active preset</span>
          <strong>{preview.lastActivePresetExists ? "Valid or empty" : "Will clear"}</strong>
        </article>
      </div>

      <div className="button-row">
        <label className="field-stack">
          <span>Workspace import mode</span>
          <select
            value={importMode}
            onChange={(event) =>
              onImportModeChange(event.target.value as ResultShareRegistryPresetImportMode)
            }
          >
            <option value="merge">Merge workspace state</option>
            <option value="replace">Replace workspace state</option>
          </select>
        </label>
      </div>

      <ul className="filter-chip-list">
        <li className="filter-chip">
          <span>Valid preview</span>
          <strong>{preview.valid ? "Yes" : "No"}</strong>
        </li>
        <li className="filter-chip">
          <span>Can apply</span>
          <strong>{preview.canApply ? "Yes" : "No"}</strong>
        </li>
      </ul>

      {preview.stalePinnedGrantPresetIds.length > 0 || preview.stalePinnedAliasPresetIds.length > 0 ? (
        <div className="inline-banner info">
          <strong>Stale pin preview</strong>
          <ul className="note-list">
            {preview.stalePinnedGrantPresetIds.map((presetId) => (
              <li key={`stale-grant-${presetId}`}>Grant pin missing locally: {presetId}</li>
            ))}
            {preview.stalePinnedAliasPresetIds.map((presetId) => (
              <li key={`stale-alias-${presetId}`}>Alias pin missing locally: {presetId}</li>
            ))}
          </ul>
        </div>
      ) : null}

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
            {preview.errors.map((error) => (
              <li key={error}>{error}</li>
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
          Apply workspace import
        </button>
        <button type="button" className="button-secondary" onClick={onClear}>
          Clear workspace import preview
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
  onPin,
  onUnpin,
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
  onPin: (presetId: string) => void;
  onUnpin: (presetId: string) => void;
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
                  onClick={() => (preset.isPinned ? onUnpin(preset.id) : onPin(preset.id))}
                >
                  {preset.isPinned ? "Unpin preset" : "Pin preset"}
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

function jumpToRegistrySection(scope: ResultShareRegistrySavedViewScope): void {
  if (typeof document === "undefined") {
    return;
  }
  const target = document.getElementById(
    scope === "grant_registry"
      ? "result-share-grant-registry-section"
      : "result-share-alias-registry-section",
  );
  target?.scrollIntoView?.({
    block: "start",
    behavior: "smooth",
  });
}

function WorkspacePresetList({
  title,
  emptyTitle,
  emptyMessage,
  presets,
  scope,
  staleIds,
  onApply,
  onMove,
  onUnpin,
}: {
  title: string;
  emptyTitle: string;
  emptyMessage: string;
  presets: ResultShareRegistrySavedViewSummary[];
  scope: ResultShareRegistrySavedViewScope;
  staleIds: string[];
  onApply: (presetId: string, mode: ResultShareRegistrySavedViewApplyMode) => void;
  onMove: (presetId: string, direction: "up" | "down") => void;
  onUnpin: (presetId: string) => void;
}) {
  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h4>{title}</h4>
          <p className="section-subtle-copy">
            Scope-aware pinned presets for quick apply and quick jumps back to the current registry.
          </p>
        </div>
      </div>

      {staleIds.length > 0 ? (
        <div className="inline-banner info">
          <strong>Stale pins detected</strong>
          <span>{staleIds.join(", ")}</span>
        </div>
      ) : null}

      {presets.length === 0 ? (
        <div className="empty-state">
          <strong>{emptyTitle}</strong>
          <p>{emptyMessage}</p>
        </div>
      ) : (
        <ul className="data-list">
          {presets.map((preset, index) => (
            <li key={preset.id} className="data-list-item">
              <div className="registry-item-stack">
                <div className="registry-item-header">
                  <div>
                    <strong>{preset.name}</strong>
                    <p>
                      {preset.scope === "grant_registry" ? "Grant preset" : "Alias preset"} · updated{" "}
                      {preset.updatedAt}
                    </p>
                  </div>
                  <div className="button-row">
                    {preset.isDefault ? <span className="status-pill active">Default</span> : null}
                    <span className="status-pill active">Pinned</span>
                  </div>
                </div>
                <ul className="filter-chip-list">
                  {preset.summaryItems.map((item) => (
                    <li key={`${preset.id}-${item}`} className="filter-chip">
                      <strong>{item}</strong>
                    </li>
                  ))}
                </ul>
                {preset.hasDrilldownContext ? (
                  <ul className="filter-chip-list">
                    {preset.drilldownSummaryItems.map((item) => (
                      <li key={`${preset.id}-drilldown-${item}`} className="filter-chip">
                        <strong>{item}</strong>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onApply(preset.id, "registry_only")}
                >
                  Quick apply
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onApply(preset.id, "registry_and_drilldown")}
                  disabled={!preset.hasDrilldownContext}
                >
                  {preset.hasDrilldownContext
                    ? "Quick apply + drilldown"
                    : "No drilldown context saved"}
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => jumpToRegistrySection(scope)}
                >
                  Jump to {scope === "grant_registry" ? "grant" : "alias"} registry
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onMove(preset.id, "up")}
                  disabled={index === 0}
                >
                  Move up
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onMove(preset.id, "down")}
                  disabled={index === presets.length - 1}
                >
                  Move down
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onUnpin(preset.id)}
                >
                  Unpin
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function RecentPresetList({
  title,
  presets,
  onApply,
  onPin,
}: {
  title: string;
  presets: ResultShareRegistrySavedViewSummary[];
  onApply: (scope: ResultShareRegistrySavedViewScope, presetId: string, mode: ResultShareRegistrySavedViewApplyMode) => void;
  onPin: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
}) {
  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h4>{title}</h4>
          <p className="section-subtle-copy">
            Recently updated local presets for quick operator reuse.
          </p>
        </div>
      </div>
      {presets.length === 0 ? (
        <div className="empty-state">
          <strong>No recent presets.</strong>
          <p>Save or import presets in this scope to populate the local workspace overview.</p>
        </div>
      ) : (
        <ul className="data-list">
          {presets.map((preset) => (
            <li key={preset.id} className="data-list-item">
              <div className="registry-item-stack">
                <strong>{preset.name}</strong>
                <p>
                  {preset.scope === "grant_registry" ? "Grant preset" : "Alias preset"} · updated{" "}
                  {preset.updatedAt}
                </p>
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onApply(preset.scope, preset.id, "registry_only")}
                >
                  Apply
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => onPin(preset.scope, preset.id)}
                  disabled={preset.isPinned}
                >
                  {preset.isPinned ? "Pinned" : "Pin"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function buildHealthStatusPillClass(
  status: ResultShareRegistryPresetWorkspaceHealthScore["status"],
): string {
  if (status === "healthy") {
    return "active";
  }
  if (status === "attention") {
    return "expired";
  }
  return "revoked";
}

function buildHealthRecommendationAction(
  recommendation: ResultShareRegistryPresetWorkspaceHealthRecommendation,
  handlers: {
    onValidateStorage: () => void;
    onCleanStalePins: () => void;
    onRestoreWorkspaceBackup: () => void;
    onResetWorkspace: () => void;
  },
): {
  label: string;
  onClick: () => void;
} | null {
  if (recommendation.kind === "run_integrity_check") {
    return {
      label: "Run integrity check",
      onClick: handlers.onValidateStorage,
    };
  }
  if (recommendation.kind === "clean_stale_pins") {
    return {
      label: "Clean stale pins",
      onClick: handlers.onCleanStalePins,
    };
  }
  if (recommendation.kind === "restore_last_good_backup") {
    return {
      label: "Restore workspace backup",
      onClick: handlers.onRestoreWorkspaceBackup,
    };
  }
  if (recommendation.kind === "reset_workspace_state") {
    return {
      label: "Reset workspace",
      onClick: handlers.onResetWorkspace,
    };
  }
  return null;
}

function PresetWorkspaceHealthPanel({
  healthScore,
  healthReport,
  healthThresholds,
  onRecalculate,
  onValidateStorage,
  onCleanStalePins,
  onRestoreWorkspaceBackup,
  onResetWorkspace,
  onExportHealthReport,
  onThresholdDraftChange,
  onPenaltyOverrideDraftChange,
  onVisibilityChange,
  onApplyThresholds,
  onResetThresholds,
}: {
  healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
  healthReport: ResultShareRegistryPresetWorkspaceHealthReportPreview;
  healthThresholds: {
    current: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences;
    draft: ResultShareRegistryPresetWorkspaceHealthThresholdDraft;
    validation: ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult;
    preview: ResultShareRegistryPresetWorkspaceHealthThresholdPreview | null;
    storageWarning: string | null;
  };
  onRecalculate: () => void;
  onValidateStorage: () => void;
  onCleanStalePins: () => void;
  onRestoreWorkspaceBackup: () => void;
  onResetWorkspace: () => void;
  onExportHealthReport: (
    format: ResultShareRegistryPresetWorkspaceHealthReportExportFormat,
  ) => void;
  onThresholdDraftChange: (
    field: "healthyMin" | "attentionMin" | "riskMin" | "criticalMin",
    value: string,
  ) => void;
  onPenaltyOverrideDraftChange: (
    key:
      | "stalePinnedPreset"
      | "missingPresetBackup"
      | "missingWorkspaceBackup"
      | "recentFailedImport"
      | "recentFailedRecovery",
    value: string,
  ) => void;
  onVisibilityChange: (
    field: "showInfo" | "showWarnings" | "showErrors" | "showCritical",
    value: boolean,
  ) => void;
  onApplyThresholds: () => void;
  onResetThresholds: () => void;
}) {
  const visibleFindings = healthScore.findings.filter((finding) => {
    if (finding.severity === "info") {
      return healthThresholds.current.recommendationVisibility.showInfo;
    }
    if (finding.severity === "warning") {
      return healthThresholds.current.recommendationVisibility.showWarnings;
    }
    if (finding.severity === "error") {
      return healthThresholds.current.recommendationVisibility.showErrors;
    }
    return healthThresholds.current.recommendationVisibility.showCritical;
  });
  const breakdownCards = [
    {
      label: "Storage integrity",
      value: `${healthScore.breakdown.storageIntegrity}/100`,
    },
    {
      label: "Preset validity",
      value: `${healthScore.breakdown.presetValidity}/100`,
    },
    {
      label: "Pinned preset hygiene",
      value: `${healthScore.breakdown.pinnedPresetHygiene}/100`,
    },
    {
      label: "Backup readiness",
      value: `${healthScore.breakdown.backupReadiness}/100`,
    },
    {
      label: "Audit reliability",
      value: `${healthScore.breakdown.auditReliability}/100`,
    },
    {
      label: "Import/export safety",
      value: `${healthScore.breakdown.importExportSafety}/100`,
    },
    {
      label: "Drilldown context completeness",
      value: `${healthScore.breakdown.drilldownContextCompleteness}/100`,
    },
  ];

  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h4>Workspace health score</h4>
          <p className="section-subtle-copy">
            Local operator hygiene only. This score summarizes browser-local preset workspace
            state and is not a security or compliance rating.
          </p>
        </div>
        <div className="button-row">
          <span className={`status-pill ${buildHealthStatusPillClass(healthScore.status)}`}>
            {healthScore.status}
          </span>
          <button type="button" className="button-secondary" onClick={onRecalculate}>
            Recalculate health
          </button>
        </div>
      </div>

      <div className="stat-grid">
        <article className="stat-card">
          <span>Health score</span>
          <strong>{healthScore.score}</strong>
          <p className="stat-hint">{healthScore.summary}</p>
        </article>
        <article className="stat-card">
          <span>Findings</span>
          <strong>{visibleFindings.length}</strong>
          <p className="stat-hint">Checked {healthScore.checkedAt}</p>
        </article>
        <article className="stat-card">
          <span>Recommendations</span>
          <strong>{healthScore.recommendations.length}</strong>
          <p className="stat-hint">No auto-repair is performed.</p>
        </article>
      </div>

      <div className="stat-grid">
        {breakdownCards.map((item) => (
          <article key={item.label} className="stat-card">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </article>
        ))}
      </div>

      <section className="conversion-section-card">
        <div className="conversion-section-header">
          <div>
            <h5>Health threshold settings</h5>
            <p className="section-subtle-copy">
              Local-only threshold and display preferences. Raw score remains deterministic; status
              bands and optional local penalty overrides can be previewed before apply.
            </p>
          </div>
        </div>

        <ul className="filter-chip-list">
          <li className="filter-chip">
            <span>Preference source</span>
            <strong>{healthScore.thresholdPreferenceSource}</strong>
          </li>
          {healthScore.thresholdSummary.map((item) => (
            <li key={item} className="filter-chip">
              <span>Threshold</span>
              <strong>{item}</strong>
            </li>
          ))}
        </ul>

        {healthThresholds.storageWarning ? (
          <div className="inline-banner error" role="alert">
            {healthThresholds.storageWarning}
          </div>
        ) : null}
        {healthScore.thresholdWarnings.length > 0 ? (
          <div className="inline-banner warning" role="status">
            {healthScore.thresholdWarnings.join(" ")}
          </div>
        ) : null}

        <div className="filter-grid">
          <label className="field-stack">
            <span>Healthy minimum</span>
            <input
              aria-label="Healthy minimum threshold"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.statusThresholds.healthyMin}
              onChange={(event) => onThresholdDraftChange("healthyMin", event.target.value)}
            />
          </label>
          <label className="field-stack">
            <span>Attention minimum</span>
            <input
              aria-label="Attention minimum threshold"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.statusThresholds.attentionMin}
              onChange={(event) => onThresholdDraftChange("attentionMin", event.target.value)}
            />
          </label>
          <label className="field-stack">
            <span>Risk minimum</span>
            <input
              aria-label="Risk minimum threshold"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.statusThresholds.riskMin}
              onChange={(event) => onThresholdDraftChange("riskMin", event.target.value)}
            />
          </label>
          <label className="field-stack">
            <span>Critical minimum</span>
            <input
              aria-label="Critical minimum threshold"
              type="number"
              min="0"
              max="0"
              value={healthThresholds.draft.statusThresholds.criticalMin}
              onChange={(event) => onThresholdDraftChange("criticalMin", event.target.value)}
              disabled
            />
          </label>
        </div>

        <div className="filter-grid">
          <label className="field-stack">
            <span>Stale pin penalty</span>
            <input
              aria-label="Stale pin penalty"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.findingPenaltyOverrides.stalePinnedPreset ?? ""}
              onChange={(event) =>
                onPenaltyOverrideDraftChange("stalePinnedPreset", event.target.value)
              }
            />
          </label>
          <label className="field-stack">
            <span>Preset backup penalty</span>
            <input
              aria-label="Preset backup penalty"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.findingPenaltyOverrides.missingPresetBackup ?? ""}
              onChange={(event) =>
                onPenaltyOverrideDraftChange("missingPresetBackup", event.target.value)
              }
            />
          </label>
          <label className="field-stack">
            <span>Workspace backup penalty</span>
            <input
              aria-label="Workspace backup penalty"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.findingPenaltyOverrides.missingWorkspaceBackup ?? ""}
              onChange={(event) =>
                onPenaltyOverrideDraftChange("missingWorkspaceBackup", event.target.value)
              }
            />
          </label>
          <label className="field-stack">
            <span>Failed import penalty</span>
            <input
              aria-label="Failed import penalty"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.findingPenaltyOverrides.recentFailedImport ?? ""}
              onChange={(event) =>
                onPenaltyOverrideDraftChange("recentFailedImport", event.target.value)
              }
            />
          </label>
          <label className="field-stack">
            <span>Failed recovery penalty</span>
            <input
              aria-label="Failed recovery penalty"
              type="number"
              min="0"
              max="100"
              value={healthThresholds.draft.findingPenaltyOverrides.recentFailedRecovery ?? ""}
              onChange={(event) =>
                onPenaltyOverrideDraftChange("recentFailedRecovery", event.target.value)
              }
            />
          </label>
        </div>

        <div className="button-row">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={healthThresholds.draft.recommendationVisibility.showInfo}
              onChange={(event) => onVisibilityChange("showInfo", event.target.checked)}
            />
            <span>Show info findings</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={healthThresholds.draft.recommendationVisibility.showWarnings}
              onChange={(event) => onVisibilityChange("showWarnings", event.target.checked)}
            />
            <span>Show warnings</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={healthThresholds.draft.recommendationVisibility.showErrors}
              onChange={(event) => onVisibilityChange("showErrors", event.target.checked)}
            />
            <span>Show errors</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={healthThresholds.draft.recommendationVisibility.showCritical}
              onChange={(event) => onVisibilityChange("showCritical", event.target.checked)}
            />
            <span>Show critical</span>
          </label>
        </div>

        {healthThresholds.validation.errors.length > 0 ? (
          <div className="inline-banner error" role="alert">
            {healthThresholds.validation.errors.join(" ")}
          </div>
        ) : null}
        {healthThresholds.validation.warnings.length > 0 ? (
          <div className="inline-banner warning" role="status">
            {healthThresholds.validation.warnings.join(" ")}
          </div>
        ) : null}
        {healthThresholds.preview ? (
          <div className="inline-banner info" role="status">
            <strong>Threshold preview</strong>
            <span>{healthThresholds.preview.summary}</span>
          </div>
        ) : null}

        <div className="button-row">
          <button
            type="button"
            className="button-secondary"
            onClick={onApplyThresholds}
          >
            Apply thresholds
          </button>
          <button type="button" className="button-secondary" onClick={onResetThresholds}>
            Reset thresholds
          </button>
        </div>
      </section>

      <section className="conversion-section-card">
        <div className="conversion-section-header">
          <div>
            <h5>Health report preview</h5>
            <p className="section-subtle-copy">
              Local operator hygiene report only. Exported reports include safe summary data,
              threshold source, findings, recommendations, and local diagnostics without preset
              payload dumps or source-file semantics.
            </p>
          </div>
          <div className="button-row">
            <button
              type="button"
              className="button-secondary"
              onClick={() => onExportHealthReport("json")}
              disabled={!healthReport.validation.valid}
            >
              Export health report JSON
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => onExportHealthReport("markdown")}
              disabled={!healthReport.validation.valid}
            >
              Export health report Markdown
            </button>
          </div>
        </div>

        <ul className="filter-chip-list">
          <li className="filter-chip">
            <span>Schema</span>
            <strong>{healthReport.report.schemaVersion}</strong>
          </li>
          <li className="filter-chip">
            <span>Generated for preview</span>
            <strong>{healthReport.report.generatedAt}</strong>
          </li>
          <li className="filter-chip">
            <span>Threshold source</span>
            <strong>{healthReport.report.thresholds.source}</strong>
          </li>
          <li className="filter-chip">
            <span>Safe export</span>
            <strong>{healthReport.report.metadata.safeExport ? "yes" : "no"}</strong>
          </li>
        </ul>

        <div className="stat-grid">
          <article className="stat-card">
            <span>Report score</span>
            <strong>{healthReport.report.health.score}</strong>
            <p className="stat-hint">{healthReport.report.health.summary}</p>
          </article>
          <article className="stat-card">
            <span>Findings</span>
            <strong>{healthReport.report.findings.length}</strong>
            <p className="stat-hint">
              {healthReport.report.recommendations.length} recommendation(s)
            </p>
          </article>
          <article className="stat-card">
            <span>Local diagnostics</span>
            <strong>{healthReport.report.diagnostics.issueCount}</strong>
            <p className="stat-hint">
              {healthReport.report.diagnostics.warningCount} warning /{" "}
              {healthReport.report.diagnostics.errorCount} error
            </p>
          </article>
        </div>

        <div className="inline-banner info">
          <strong>Report safety note</strong>
          <span>{healthReport.report.safetyExclusions.join(" ")}</span>
        </div>

        {healthReport.validation.errors.length > 0 ? (
          <div className="inline-banner error" role="alert">
            {healthReport.validation.errors.join(" ")}
          </div>
        ) : null}
        {healthReport.validation.warnings.length > 0 ? (
          <div className="inline-banner warning" role="status">
            {healthReport.validation.warnings.join(" ")}
          </div>
        ) : null}

        <details className="report-preview-block">
          <summary>JSON preview</summary>
          <pre>{healthReport.json ?? "Report preview is unavailable until validation passes."}</pre>
        </details>
        <details className="report-preview-block">
          <summary>Markdown preview</summary>
          <pre>
            {healthReport.markdown ?? "Report preview is unavailable until validation passes."}
          </pre>
        </details>
      </section>

      {visibleFindings.length > 0 ? (
        <section className="conversion-section-card">
          <div className="conversion-section-header">
            <div>
              <h5>Safety findings</h5>
              <p className="section-subtle-copy">
                Deterministic local signals from integrity, backup, audit, pin hygiene, and import
                preview state.
              </p>
            </div>
          </div>
          <ul className="data-list">
            {visibleFindings.map((finding) => (
              <li key={`${finding.code}-${finding.summary}`} className="data-list-item">
                <div className="registry-item-stack">
                  <div className="registry-item-header">
                    <div>
                      <strong>{finding.summary}</strong>
                      <p>{finding.detail}</p>
                    </div>
                    <span
                      className={`status-pill ${
                        finding.severity === "info"
                          ? "active"
                          : finding.severity === "warning"
                            ? "expired"
                            : "revoked"
                      }`}
                    >
                      {finding.severity}
                    </span>
                  </div>
                  <p className="section-subtle-copy">Code: {finding.code}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {healthScore.recommendations.length > 0 ? (
        <section className="conversion-section-card">
          <div className="conversion-section-header">
            <div>
              <h5>Recommended local actions</h5>
              <p className="section-subtle-copy">
                These are local operator suggestions that point back to existing preset workspace,
                diagnostics, recovery, and import/export controls.
              </p>
            </div>
          </div>
          <ul className="data-list">
            {healthScore.recommendations.map((recommendation) => {
              const action = buildHealthRecommendationAction(recommendation, {
                onValidateStorage,
                onCleanStalePins,
                onRestoreWorkspaceBackup,
                onResetWorkspace,
              });
              return (
                <li key={recommendation.kind} className="data-list-item">
                  <div className="registry-item-stack">
                    <strong>{recommendation.label}</strong>
                    <p>{recommendation.detail}</p>
                  </div>
                  {action ? (
                    <div className="button-row">
                      <button
                        type="button"
                        className="button-secondary"
                        onClick={action.onClick}
                      >
                        {action.label}
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <ul className="note-list">
        {healthScore.notes.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}

function PresetWorkspacePanel({
  viewModel,
  healthScore,
  healthReport,
  healthThresholds,
  transfer,
  onApply,
  onUnpin,
  onPin,
  onMovePinned,
  onCleanStalePins,
  onClearPins,
  onResetWorkspace,
  onValidateStorage,
  onWorkspaceImportModeChange,
  onImportWorkspaceFile,
  onApplyWorkspaceImport,
  onClearWorkspaceImportPreview,
  onExportWorkspace,
  onRestoreWorkspaceBackup,
  onRecalculateHealth,
  onExportHealthReport,
  onThresholdDraftChange,
  onPenaltyOverrideDraftChange,
  onVisibilityChange,
  onApplyThresholds,
  onResetThresholds,
}: {
  viewModel: ResultShareRegistryPresetWorkspaceViewModel;
  healthScore: ResultShareRegistryPresetWorkspaceHealthScore;
  healthReport: ResultShareRegistryPresetWorkspaceHealthReportPreview;
  healthThresholds: {
    current: ResultShareRegistryPresetWorkspaceHealthThresholdPreferences;
    draft: ResultShareRegistryPresetWorkspaceHealthThresholdDraft;
    validation: ResultShareRegistryPresetWorkspaceHealthThresholdValidationResult;
    preview: ResultShareRegistryPresetWorkspaceHealthThresholdPreview | null;
    storageWarning: string | null;
  };
  transfer: {
    importMode: ResultShareRegistryPresetImportMode;
    preview: ResultShareRegistryPresetWorkspaceImportPreview | null;
    lastGoodBackup: ResultShareRegistryPresetWorkspaceBackupSnapshot | null;
  };
  onApply: (
    scope: ResultShareRegistrySavedViewScope,
    presetId: string,
    mode: ResultShareRegistrySavedViewApplyMode,
  ) => void;
  onUnpin: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onPin: (scope: ResultShareRegistrySavedViewScope, presetId: string) => void;
  onMovePinned: (
    scope: ResultShareRegistrySavedViewScope,
    presetId: string,
    direction: "up" | "down",
  ) => void;
  onCleanStalePins: () => void;
  onClearPins: () => void;
  onResetWorkspace: () => void;
  onValidateStorage: () => void;
  onWorkspaceImportModeChange: (mode: ResultShareRegistryPresetImportMode) => void;
  onImportWorkspaceFile: (file: File | null) => void;
  onApplyWorkspaceImport: () => void;
  onClearWorkspaceImportPreview: () => void;
  onExportWorkspace: () => void;
  onRestoreWorkspaceBackup: () => void;
  onRecalculateHealth: () => void;
  onExportHealthReport: (
    format: ResultShareRegistryPresetWorkspaceHealthReportExportFormat,
  ) => void;
  onThresholdDraftChange: (
    field: "healthyMin" | "attentionMin" | "riskMin" | "criticalMin",
    value: string,
  ) => void;
  onPenaltyOverrideDraftChange: (
    key:
      | "stalePinnedPreset"
      | "missingPresetBackup"
      | "missingWorkspaceBackup"
      | "recentFailedImport"
      | "recentFailedRecovery",
    value: string,
  ) => void;
  onVisibilityChange: (
    field: "showInfo" | "showWarnings" | "showErrors" | "showCritical",
    value: boolean,
  ) => void;
  onApplyThresholds: () => void;
  onResetThresholds: () => void;
}) {
  const stalePinCount = viewModel.staleGrantPinIds.length + viewModel.staleAliasPinIds.length;

  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h3>Preset workspace</h3>
          <p className="section-subtle-copy">
            Local-only operator organization for preset pinning, recent activity, and storage
            health. This never syncs to backend and never stores bearer tokens or source-file
            data.
          </p>
        </div>
        <div className="button-row">
          <button type="button" className="button-secondary" onClick={onExportWorkspace}>
            Export workspace state JSON
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={onRestoreWorkspaceBackup}
            disabled={transfer.lastGoodBackup === null}
          >
            Restore workspace backup
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={onCleanStalePins}
            disabled={stalePinCount === 0}
          >
            Clean stale pins
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={onClearPins}
            disabled={
              viewModel.pinnedGrantPresets.length === 0 &&
              viewModel.pinnedAliasPresets.length === 0 &&
              stalePinCount === 0
            }
          >
            Clear all pins
          </button>
          <button type="button" className="button-danger" onClick={onResetWorkspace}>
            Reset workspace
          </button>
        </div>
      </div>

      <SummaryCardList items={viewModel.overviewSummary} />

      <PresetWorkspaceHealthPanel
        healthScore={healthScore}
        healthReport={healthReport}
        healthThresholds={healthThresholds}
        onRecalculate={onRecalculateHealth}
        onValidateStorage={onValidateStorage}
        onCleanStalePins={onCleanStalePins}
        onRestoreWorkspaceBackup={onRestoreWorkspaceBackup}
        onResetWorkspace={onResetWorkspace}
        onExportHealthReport={onExportHealthReport}
        onThresholdDraftChange={onThresholdDraftChange}
        onPenaltyOverrideDraftChange={onPenaltyOverrideDraftChange}
        onVisibilityChange={onVisibilityChange}
        onApplyThresholds={onApplyThresholds}
        onResetThresholds={onResetThresholds}
      />

      <ul className="filter-chip-list">
        <li className="filter-chip">
          <span>Last active preset</span>
          <strong>{viewModel.lastActivePresetLabel ?? "None"}</strong>
        </li>
        <li className="filter-chip">
          <span>Latest validation</span>
          <strong>{viewModel.storageHealth.latestValidationAt ?? "Not validated yet"}</strong>
        </li>
        <li className="filter-chip">
          <span>Last backup</span>
          <strong>{viewModel.storageHealth.lastBackupLabel}</strong>
        </li>
        <li className="filter-chip">
          <span>Workspace backup</span>
          <strong>{viewModel.storageHealth.workspaceBackupLabel}</strong>
        </li>
      </ul>

      {viewModel.storageHealth.workspaceWarning ? (
        <div className="inline-banner error" role="alert">
          <strong>Workspace state warning</strong>
          <span>{viewModel.storageHealth.workspaceWarning}</span>
        </div>
      ) : null}

      {viewModel.storageHealth.auditWarning ? (
        <div className="inline-banner info">
          <strong>Audit storage warning</strong>
          <span>{viewModel.storageHealth.auditWarning}</span>
        </div>
      ) : null}

      <div className="split-grid">
        <WorkspacePresetList
          title="Pinned grant presets"
          emptyTitle="No pinned grant presets."
          emptyMessage="Pin grant presets from the saved views list to keep high-signal grant workflows close at hand."
          presets={viewModel.pinnedGrantPresets}
          scope="grant_registry"
          staleIds={viewModel.staleGrantPinIds}
          onApply={(presetId, mode) => onApply("grant_registry", presetId, mode)}
          onMove={(presetId, direction) => onMovePinned("grant_registry", presetId, direction)}
          onUnpin={(presetId) => onUnpin("grant_registry", presetId)}
        />
        <WorkspacePresetList
          title="Pinned alias presets"
          emptyTitle="No pinned alias presets."
          emptyMessage="Pin alias presets from the saved views list to keep alias follow-up workflows close at hand."
          presets={viewModel.pinnedAliasPresets}
          scope="alias_registry"
          staleIds={viewModel.staleAliasPinIds}
          onApply={(presetId, mode) => onApply("alias_registry", presetId, mode)}
          onMove={(presetId, direction) => onMovePinned("alias_registry", presetId, direction)}
          onUnpin={(presetId) => onUnpin("alias_registry", presetId)}
        />
      </div>

      <div className="split-grid">
        <RecentPresetList
          title="Recent grant presets"
          presets={viewModel.recentGrantPresets}
          onApply={onApply}
          onPin={onPin}
        />
        <RecentPresetList
          title="Recent alias presets"
          presets={viewModel.recentAliasPresets}
          onApply={onApply}
          onPin={onPin}
        />
      </div>

      <section className="conversion-section-card saved-view-card">
        <div className="conversion-section-header">
          <div>
            <h4>Workspace import / export</h4>
            <p className="section-subtle-copy">
              Local browser organization state only. This does not include saved preset
              definitions, backend data, bearer tokens, or share payloads.
            </p>
          </div>
        </div>
        <label className="field-stack">
          <span>Import workspace state JSON file</span>
          <input
            type="file"
            accept=".json,application/json"
            onChange={(event) => onImportWorkspaceFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <WorkspaceImportPreviewPanel
          preview={transfer.preview}
          importMode={transfer.importMode}
          onImportModeChange={onWorkspaceImportModeChange}
          onApply={onApplyWorkspaceImport}
          onClear={onClearWorkspaceImportPreview}
        />
      </section>

      <section className="conversion-section-card">
        <div className="conversion-section-header">
          <div>
            <h4>Recent local activity</h4>
            <p className="section-subtle-copy">
              Compact recent preset operations from the local audit history.
            </p>
          </div>
        </div>
        {viewModel.recentActivity.length > 0 ? (
          <ul className="data-list">
            {viewModel.recentActivity.map((event) => (
              <li key={event.id} className="data-list-item">
                <div className="registry-item-stack">
                  <strong>{event.summary}</strong>
                  <p>
                    {event.actionType} · {event.occurredAt}
                    {event.scope ? ` · ${event.scope}` : ""}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>No local preset activity yet.</strong>
            <p>Saved-view, import/export, diagnostics, and recovery actions will appear here.</p>
          </div>
        )}
      </section>
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
          <span>Workspace state</span>
          <strong>{diagnostics.workspaceStatePresent ? "Present" : "Missing"}</strong>
        </li>
        <li className="filter-chip">
          <span>Validated at</span>
          <strong>{diagnostics.latestValidationAt ?? diagnostics.checkedAt}</strong>
        </li>
      </ul>

      {diagnostics.workspaceStateWarning ? (
        <div className="inline-banner info">
          <strong>Workspace organization warning</strong>
          <span>{diagnostics.workspaceStateWarning}</span>
        </div>
      ) : null}

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

function PresetLocalAuditPanel({
  summary,
  onClear,
}: {
  summary: ResultShareRegistryPresetLocalAuditSummary;
  onClear: () => void;
}) {
  return (
    <section className="conversion-section-card saved-view-card">
      <div className="conversion-section-header">
        <div>
          <h3>Local preset activity</h3>
          <p className="section-subtle-copy">
            Browser-local history only. This is an operator convenience summary, not backend audit
            logging, and it never stores bearer tokens, raw aliases, or payload dumps.
          </p>
        </div>
        <div className="button-row">
          <button
            type="button"
            className="button-secondary"
            onClick={onClear}
            disabled={summary.totalEvents === 0 && !summary.storageWarning}
          >
            Clear local audit history
          </button>
        </div>
      </div>

      <SummaryCardList
        items={[
          { label: "Total events", value: summary.totalEvents, hint: null },
          { label: "Success", value: summary.successCount, hint: null },
          { label: "Warnings", value: summary.warningCount, hint: null },
          { label: "Failed", value: summary.failedCount, hint: null },
          { label: "Imports", value: summary.importRelatedCount, hint: null },
          { label: "Backups", value: summary.backupRelatedCount, hint: null },
          { label: "Recovery", value: summary.recoveryRelatedCount, hint: null },
          { label: "Exports", value: summary.exportRelatedCount, hint: null },
        ]}
      />

      <ul className="filter-chip-list">
        <li className="filter-chip">
          <span>Grant-scope events</span>
          <strong>{summary.byScope.grant_registry}</strong>
        </li>
        <li className="filter-chip">
          <span>Alias-scope events</span>
          <strong>{summary.byScope.alias_registry}</strong>
        </li>
        <li className="filter-chip">
          <span>Storage events</span>
          <strong>{summary.byScope.storage}</strong>
        </li>
        <li className="filter-chip">
          <span>Unscoped events</span>
          <strong>{summary.byScope.unscoped}</strong>
        </li>
        <li className="filter-chip">
          <span>Last event</span>
          <strong>{summary.lastEventAt ?? "No history yet"}</strong>
        </li>
      </ul>

      {summary.storageWarning ? (
        <div className="inline-banner error" role="alert">
          <strong>Audit storage warning</strong>
          <span>{summary.storageWarning}</span>
        </div>
      ) : null}

      <section className="conversion-section-card">
        <div className="conversion-section-header">
          <div>
            <h4>Action-type counts</h4>
            <p className="section-subtle-copy">
              Compact aggregation over local preset operations recorded in this browser.
            </p>
          </div>
        </div>
        <ul className="filter-chip-list">
          {Object.entries(summary.byActionType)
            .filter(([, count]) => count > 0)
            .map(([actionType, count]) => (
              <li key={actionType} className="filter-chip">
                <span>{actionType}</span>
                <strong>{count}</strong>
              </li>
            ))}
        </ul>
        {Object.values(summary.byActionType).every((count) => count === 0) ? (
          <div className="empty-state">
            <strong>No preset activity recorded yet.</strong>
            <p>Save, apply, import, export, validate, or recover presets to build local history.</p>
          </div>
        ) : null}
      </section>

      <section className="conversion-section-card">
        <div className="conversion-section-header">
          <div>
            <h4>Recent preset activity</h4>
            <p className="section-subtle-copy">
              Latest local-only preset operations with safe summaries only.
            </p>
          </div>
        </div>
        {summary.recentEvents.length > 0 ? (
          <ul className="data-list">
            {summary.recentEvents.map((event) => (
              <li key={event.id} className="data-list-item">
                <div className="registry-item-stack">
                  <div className="registry-item-header">
                    <div>
                      <strong>{event.summary}</strong>
                      <p>
                        {event.actionType} · {event.occurredAt}
                        {event.scope ? ` · ${event.scope}` : ""}
                        {event.presetName ? ` · ${event.presetName}` : ""}
                      </p>
                    </div>
                    <span
                      className={`status-pill ${
                        event.status === "failed"
                          ? "revoked"
                          : event.status === "warning"
                            ? "expired"
                            : "active"
                      }`}
                    >
                      {event.status}
                    </span>
                  </div>
                  {event.safeDetails ? (
                    <p className="section-subtle-copy">Details: {event.safeDetails}</p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="empty-state">
            <strong>No recent activity yet.</strong>
            <p>Local preset history will appear here after saved-view and recovery actions.</p>
          </div>
        )}
      </section>
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
  presetAudit,
  presetWorkspace,
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
  onClearPresetAudit,
  onPresetWorkspaceImportModeChange,
  onImportPresetWorkspaceFile,
  onApplyPresetWorkspaceImport,
  onClearPresetWorkspaceImportPreview,
  onExportPresetWorkspace,
  onRestorePresetWorkspaceBackup,
  onRecalculatePresetWorkspaceHealth,
  onExportPresetWorkspaceHealthReport,
  onHealthThresholdDraftChange,
  onHealthPenaltyOverrideDraftChange,
  onHealthVisibilityChange,
  onApplyHealthThresholds,
  onResetHealthThresholds,
  onPinSavedView,
  onUnpinSavedView,
  onMovePinnedSavedView,
  onClearWorkspacePins,
  onResetWorkspace,
  onCleanStaleWorkspacePins,
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

        <PresetWorkspacePanel
          viewModel={presetWorkspace.viewModel}
          healthScore={presetWorkspace.healthScore}
          healthReport={presetWorkspace.healthReport}
          healthThresholds={presetWorkspace.healthThresholds}
          transfer={presetWorkspace.transfer}
          onApply={onApplySavedView}
          onUnpin={onUnpinSavedView}
          onPin={onPinSavedView}
          onMovePinned={onMovePinnedSavedView}
          onCleanStalePins={onCleanStaleWorkspacePins}
          onClearPins={onClearWorkspacePins}
          onResetWorkspace={onResetWorkspace}
          onValidateStorage={onValidatePresetStorage}
          onWorkspaceImportModeChange={onPresetWorkspaceImportModeChange}
          onImportWorkspaceFile={onImportPresetWorkspaceFile}
          onApplyWorkspaceImport={onApplyPresetWorkspaceImport}
          onClearWorkspaceImportPreview={onClearPresetWorkspaceImportPreview}
          onExportWorkspace={onExportPresetWorkspace}
          onRestoreWorkspaceBackup={onRestorePresetWorkspaceBackup}
          onRecalculateHealth={onRecalculatePresetWorkspaceHealth}
          onExportHealthReport={onExportPresetWorkspaceHealthReport}
          onThresholdDraftChange={onHealthThresholdDraftChange}
          onPenaltyOverrideDraftChange={onHealthPenaltyOverrideDraftChange}
          onVisibilityChange={onHealthVisibilityChange}
          onApplyThresholds={onApplyHealthThresholds}
          onResetThresholds={onResetHealthThresholds}
        />

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
            onPin={(presetId) => onPinSavedView("grant_registry", presetId)}
            onUnpin={(presetId) => onUnpinSavedView("grant_registry", presetId)}
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
            onPin={(presetId) => onPinSavedView("alias_registry", presetId)}
            onUnpin={(presetId) => onUnpinSavedView("alias_registry", presetId)}
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

        <PresetLocalAuditPanel
          summary={presetAudit.summary}
          onClear={onClearPresetAudit}
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
          <section className="conversion-section-card" id="result-share-grant-registry-section">
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

          <section className="conversion-section-card" id="result-share-alias-registry-section">
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
