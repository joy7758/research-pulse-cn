import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import "./App.css";
import { ConversionDrilldownPanel } from "./components/ConversionDrilldownPanel";
import { ConversionFilterBar } from "./components/ConversionFilterBar";
import { ConversionOverviewPanel } from "./components/ConversionOverviewPanel";
import { ResultShareRegistryPanel } from "./components/ResultShareRegistryPanel";
import { TokenEntryView } from "./components/TokenEntryView";
import { WorkspaceDetailView } from "./components/WorkspaceDetailView";
import { WorkspaceListPanel } from "./components/WorkspaceListPanel";
import {
  buildConversionFilterSummaryViewModel,
  DEFAULT_CONVERSION_FILTER_INPUT,
  GLOBAL_CONVERSION_FILTER_SUPPORT,
  normalizeConversionFilterInput,
  PER_SHARE_DRILLDOWN_FILTER_SUPPORT,
  WORKSPACE_CONVERSION_FILTER_SUPPORT,
} from "./lib/conversionFilters";
import {
  buildApiErrorViewModel,
  buildGlobalConversionDrilldownViewModel,
  buildGlobalConversionOverviewViewModel,
  buildPaperLookupOptions,
  buildResultShareAliasDrilldownViewModel,
  buildResultShareGrantDrilldownViewModel,
  buildResultShareRegistryViewModel,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
  buildWorkspaceConversionDrilldownViewModel,
  buildWorkspaceConversionOverviewViewModel,
  buildWorkspaceListItems,
} from "./lib/adminModel";
import {
  createGroupWorkspaceAdminApiClient,
  GroupWorkspaceAdminApiError,
  type GroupWorkspaceAdminApiClient,
} from "./lib/apiClient";
import {
  buildResultShareRegistryFilterSummaryViewModel,
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
  normalizeResultShareRegistryFilterInput,
  normalizeResultShareRegistrySortInput,
} from "./lib/resultShareRegistryFilters";
import {
  appendResultShareRegistryPresetAuditEvent,
  buildResultShareRegistryPresetWorkspaceViewModel,
  buildResultShareRegistryPresetWorkspaceHealthScore,
  buildResultShareRegistryPresetIntegrityReport,
  buildResultShareRegistryPresetAuditSummary,
  applyResultShareRegistryPresetImport,
  applyResultShareRegistrySavedView,
  buildInitialResultShareRegistrySavedViewState,
  buildResultShareRegistryPresetExport,
  buildResultShareRegistryPresetWorkspaceExport,
  buildResultShareRegistrySavedViewDraft,
  buildResultShareRegistrySavedViewSummaries,
  cleanStaleResultShareRegistryPresetWorkspacePins,
  clearResultShareRegistryPresetAuditEvents,
  clearAllResultShareRegistryPresetWorkspacePins,
  createPresetAuditEvent,
  createResultShareRegistryPresetBackup,
  createResultShareRegistryPresetWorkspaceBackup,
  createResultShareRegistrySavedView,
  deleteResultShareRegistrySavedView,
  inspectResultShareRegistryPresetStorage,
  loadResultShareRegistryPresetAuditEvents,
  loadResultShareRegistryPresetWorkspaceBackup,
  loadResultShareRegistryPresetWorkspaceState,
  movePinnedResultShareRegistryPresetWorkspacePreset,
  overwriteResultShareRegistrySavedView,
  parseResultShareRegistryPresetImport,
  parseResultShareRegistryPresetWorkspaceImport,
  persistResultShareRegistryPresetWorkspaceState,
  persistResultShareRegistryPresetWorkspaceBackup,
  persistResultShareRegistrySavedViewStore,
  persistResultShareRegistryPresetBackup,
  pinResultShareRegistryPresetWorkspacePreset,
  RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
  RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
  RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
  resetResultShareRegistryPresetWorkspaceState,
  saveResultShareRegistrySavedView,
  setResultShareRegistryDefaultPresetId,
  setResultShareRegistryPresetWorkspaceLastActive,
  syncResultShareRegistryPresetWorkspaceStateWithStore,
  applyResultShareRegistryPresetWorkspaceImport,
  restoreResultShareRegistryPresetWorkspaceBackup,
  unpinResultShareRegistryPresetWorkspacePreset,
} from "./lib/resultShareRegistrySavedViews";
import {
  clearVisibleAdminTokenHints,
  extractAdminTokenFromLocation,
} from "./lib/token";
import type {
  ApiErrorViewModel,
  ConversionFilterInput,
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionDrilldownRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionDrilldownRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  PaperProfileRead,
  ResultShareAliasRead,
  ResultShareAliasConversionDrilldownRead,
  ResultShareGrantConversionDrilldownRead,
  ResultShareGrantRead,
  ResultShareRegistryFilterInput,
  ResultShareRegistryPresetBackupSnapshot,
  ResultShareRegistryPresetIntegrityReport,
  ResultShareRegistryPresetImportMode,
  ResultShareRegistryPresetImportPreview,
  ResultShareRegistryPresetLocalAuditEvent,
  ResultShareRegistryPresetLocalAuditSummary,
  ResultShareRegistryPresetRecoveryAction,
  ResultShareRegistryPresetWorkspaceBackupSnapshot,
  ResultShareRegistryPresetWorkspaceHealthScore,
  ResultShareRegistryPresetWorkspaceImportPreview,
  ResultShareRegistrySavedViewApplyMode,
  ResultShareRegistrySavedView,
  ResultShareRegistrySavedViewScope,
  ResultShareRegistrySavedViewStoreState,
  ResultShareRegistryPresetStorageDiagnostics,
  ResultShareRegistryPresetWorkspaceState,
  ResultShareRegistryPresetWorkspaceViewModel,
  ResultShareRegistrySortInput,
  ShareGrantOneTimeDisplayModel,
  UserProfileRead,
  WorkspaceBoardShareCreateInput,
  WorkspaceCreateInput,
  WorkspaceMemberAddInput,
  WorkspacePaperAddInput,
  WorkspaceUpdateInput,
} from "./lib/types";

const DEFAULT_API_BASE_URL =
  import.meta.env.VITE_GROUP_WORKSPACE_ADMIN_API_BASE_URL?.trim() || "http://127.0.0.1:8000";

function getLocalStorageSafe(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

async function readLocalFileText(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read local preset JSON file."));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsText(file);
  });
}

type ShareDrilldownTarget =
  | {
      kind: "grant";
      id: string;
    }
  | {
      kind: "alias";
      id: string;
    };

type ActiveRegistryPresetState = {
  scope: ResultShareRegistrySavedViewScope;
  presetId: string;
  presetName: string;
  source: "saved_view" | "default_preset";
} | null;

type ShareDrilldownContextSourceState = {
  kind: "manual" | "saved_view" | "default_preset";
  presetId: string | null;
  presetName: string | null;
};

function findSavedViewInStore(
  store: ResultShareRegistrySavedViewStoreState,
  presetId: string | null,
  scope?: ResultShareRegistrySavedViewScope,
): ResultShareRegistrySavedView | null {
  if (!presetId) {
    return null;
  }
  if (scope === "grant_registry") {
    return store.grantPresets.find((preset) => preset.id === presetId) ?? null;
  }
  if (scope === "alias_registry") {
    return store.aliasPresets.find((preset) => preset.id === presetId) ?? null;
  }
  return (
    store.grantPresets.find((preset) => preset.id === presetId) ??
    store.aliasPresets.find((preset) => preset.id === presetId) ??
    null
  );
}

function buildActiveRegistryPresetState(
  preset: ResultShareRegistrySavedView | null,
  source: "saved_view" | "default_preset",
): ActiveRegistryPresetState {
  if (!preset) {
    return null;
  }
  return {
    scope: preset.scope,
    presetId: preset.id,
    presetName: preset.name,
    source,
  };
}

function buildShareDrilldownContextSourceState(
  preset: ResultShareRegistrySavedView | null,
  source: "saved_view" | "default_preset",
): ShareDrilldownContextSourceState {
  if (!preset?.drilldownContext) {
    return {
      kind: "manual",
      presetId: null,
      presetName: null,
    };
  }
  return {
    kind: source,
    presetId: preset.id,
    presetName: preset.name,
  };
}

function buildFallbackPresetStorageDiagnostics(
  store: ResultShareRegistrySavedViewStoreState,
  backup: ResultShareRegistryPresetBackupSnapshot | null,
  workspaceState: ResultShareRegistryPresetWorkspaceState,
  workspaceStateWarning: string | null,
  checkedAt: string,
): {
  report: ResultShareRegistryPresetIntegrityReport;
  diagnostics: ResultShareRegistryPresetStorageDiagnostics;
} {
  const report = buildResultShareRegistryPresetIntegrityReport(store, [], {
    checkedAt,
    rawGrantPresetCount: store.grantPresets.length,
    rawAliasPresetCount: store.aliasPresets.length,
  });
  return {
    report,
    diagnostics: {
      checkedAt,
      storageKeysPresent: {
        grantPresets: store.grantPresets.length > 0,
        aliasPresets: store.aliasPresets.length > 0,
        defaultPresetId: Boolean(store.defaultPresetId),
        lastGoodBackup: backup !== null,
        workspaceState:
          workspaceState.pinnedGrantPresetIds.length > 0 ||
          workspaceState.pinnedAliasPresetIds.length > 0 ||
          workspaceState.lastActivePresetId !== null,
      },
      grantPresetCount: report.grantPresetCount,
      aliasPresetCount: report.aliasPresetCount,
      validPresetCount: report.validPresetCount,
      invalidPresetCount: report.invalidPresetCount,
      defaultPresetIdPresent: Boolean(store.defaultPresetId),
      lastBackupPresent: backup !== null,
      workspaceStatePresent:
        workspaceState.pinnedGrantPresetIds.length > 0 ||
        workspaceState.pinnedAliasPresetIds.length > 0 ||
        workspaceState.lastActivePresetId !== null,
      workspaceStateWarning,
      latestValidationAt: report.checkedAt,
      warningCount: report.warningCount,
      errorCount: report.errorCount,
      notes: [
        "Diagnostics inspect browser-local preset storage only.",
        backup
          ? `Last-good backup available from ${backup.createdAt}.`
          : "No last-good backup snapshot is stored yet.",
        workspaceStateWarning
          ? workspaceStateWarning
          : "Local preset workspace organization state is derived from browser-only preferences.",
      ],
    },
  };
}

type GroupWorkspaceAdminShellProps = {
  initialApiBaseUrl?: string;
  locationLike?: Pick<Location, "pathname" | "search" | "hash">;
  historyLike?: Pick<History, "replaceState">;
  apiClientFactory?: typeof createGroupWorkspaceAdminApiClient;
};

function App() {
  return <GroupWorkspaceAdminShell />;
}

export function GroupWorkspaceAdminShell({
  initialApiBaseUrl,
  locationLike,
  historyLike,
  apiClientFactory = createGroupWorkspaceAdminApiClient,
}: GroupWorkspaceAdminShellProps) {
  const resolvedLocation =
    locationLike ?? (typeof window === "undefined" ? undefined : window.location);
  const resolvedHistory =
    historyLike ?? (typeof window === "undefined" ? undefined : window.history);
  const initialPresetInspectionRef = useRef(
    inspectResultShareRegistryPresetStorage(getLocalStorageSafe()),
  );
  const initialPresetAuditRef = useRef(
    loadResultShareRegistryPresetAuditEvents(getLocalStorageSafe()),
  );
  const initialPresetWorkspaceStateRef = useRef(
    loadResultShareRegistryPresetWorkspaceState(getLocalStorageSafe()),
  );
  const initialPresetWorkspaceBackupRef = useRef(
    loadResultShareRegistryPresetWorkspaceBackup(getLocalStorageSafe()),
  );
  const initialSavedViewStoreRef = useRef<ResultShareRegistrySavedViewStoreState>(
    initialPresetInspectionRef.current.store,
  );
  const initialSavedViewStateRef = useRef(
    buildInitialResultShareRegistrySavedViewState(initialSavedViewStoreRef.current),
  );
  const initialActiveRegistryPresetRef = useRef<ActiveRegistryPresetState>(
    buildActiveRegistryPresetState(initialSavedViewStateRef.current.defaultPreset, "default_preset"),
  );
  const initialShareDrilldownContextSourceRef = useRef<ShareDrilldownContextSourceState>(
    buildShareDrilldownContextSourceState(
      initialSavedViewStateRef.current.defaultPreset,
      "default_preset",
    ),
  );

  const [apiBaseUrlInput, setApiBaseUrlInput] = useState(
    initialApiBaseUrl ?? DEFAULT_API_BASE_URL,
  );
  const [adminTokenInput, setAdminTokenInput] = useState("");
  const [session, setSession] = useState<{
    apiBaseUrl: string;
    adminToken: string;
    client: GroupWorkspaceAdminApiClient;
  } | null>(null);
  const [workspaces, setWorkspaces] = useState<GroupWorkspaceRead[]>([]);
  const [users, setUsers] = useState<UserProfileRead[]>([]);
  const [papers, setPapers] = useState<PaperProfileRead[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<GroupWorkspaceRead | null>(null);
  const [selectedBoard, setSelectedBoard] = useState<GroupWorkspaceBoardRead | null>(null);
  const [selectedShareGrants, setSelectedShareGrants] = useState<ResultShareGrantRead[]>([]);
  const [resultShareGrants, setResultShareGrants] = useState<ResultShareGrantRead[]>([]);
  const [resultShareAliases, setResultShareAliases] = useState<ResultShareAliasRead[]>([]);
  const [globalConversionOverview, setGlobalConversionOverview] =
    useState<GroupWorkspaceConversionOverviewRead | null>(null);
  const [globalConversionDrilldown, setGlobalConversionDrilldown] =
    useState<GroupWorkspaceConversionDrilldownRead | null>(null);
  const [workspaceConversionOverview, setWorkspaceConversionOverview] =
    useState<GroupWorkspaceWorkspaceConversionOverviewRead | null>(null);
  const [workspaceConversionDrilldown, setWorkspaceConversionDrilldown] =
    useState<GroupWorkspaceWorkspaceConversionDrilldownRead | null>(null);
  const [shareGrantDrilldown, setShareGrantDrilldown] =
    useState<ResultShareGrantConversionDrilldownRead | null>(null);
  const [shareAliasDrilldown, setShareAliasDrilldown] =
    useState<ResultShareAliasConversionDrilldownRead | null>(null);
  const [shareDrilldownTarget, setShareDrilldownTarget] = useState<ShareDrilldownTarget | null>(
    null,
  );
  const [boardCache, setBoardCache] = useState<Record<string, GroupWorkspaceBoardRead | undefined>>(
    {},
  );
  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);
  const [globalConversionLoading, setGlobalConversionLoading] = useState(false);
  const [globalConversionDrilldownLoading, setGlobalConversionDrilldownLoading] = useState(false);
  const [workspaceConversionLoading, setWorkspaceConversionLoading] = useState(false);
  const [workspaceConversionDrilldownLoading, setWorkspaceConversionDrilldownLoading] =
    useState(false);
  const [resultShareRegistryLoading, setResultShareRegistryLoading] = useState(false);
  const [shareDrilldownLoading, setShareDrilldownLoading] = useState(false);
  const [connectError, setConnectError] = useState<ApiErrorViewModel | null>(null);
  const [actionError, setActionError] = useState<ApiErrorViewModel | null>(null);
  const [globalConversionError, setGlobalConversionError] = useState<ApiErrorViewModel | null>(null);
  const [globalConversionDrilldownError, setGlobalConversionDrilldownError] =
    useState<ApiErrorViewModel | null>(null);
  const [workspaceConversionError, setWorkspaceConversionError] =
    useState<ApiErrorViewModel | null>(null);
  const [workspaceConversionDrilldownError, setWorkspaceConversionDrilldownError] =
    useState<ApiErrorViewModel | null>(null);
  const [resultShareRegistryError, setResultShareRegistryError] =
    useState<ApiErrorViewModel | null>(null);
  const [shareDrilldownError, setShareDrilldownError] = useState<ApiErrorViewModel | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [oneTimeGrant, setOneTimeGrant] = useState<ShareGrantOneTimeDisplayModel | null>(null);
  const [globalConversionFilters, setGlobalConversionFilters] = useState<ConversionFilterInput>(
    DEFAULT_CONVERSION_FILTER_INPUT,
  );
  const [globalConversionFilterDraft, setGlobalConversionFilterDraft] =
    useState<ConversionFilterInput>(DEFAULT_CONVERSION_FILTER_INPUT);
  const [workspaceConversionFilters, setWorkspaceConversionFilters] =
    useState<ConversionFilterInput>(DEFAULT_CONVERSION_FILTER_INPUT);
  const [workspaceConversionFilterDraft, setWorkspaceConversionFilterDraft] =
    useState<ConversionFilterInput>(DEFAULT_CONVERSION_FILTER_INPUT);
  const [shareDrilldownFilters, setShareDrilldownFilters] = useState<ConversionFilterInput>(
    initialSavedViewStateRef.current.drilldownFilters,
  );
  const [shareDrilldownFilterDraft, setShareDrilldownFilterDraft] =
    useState<ConversionFilterInput>(initialSavedViewStateRef.current.drilldownFilters);
  const [resultShareRegistryFilters, setResultShareRegistryFilters] =
    useState<ResultShareRegistryFilterInput>(initialSavedViewStateRef.current.filters);
  const [resultShareRegistryFilterDraft, setResultShareRegistryFilterDraft] =
    useState<ResultShareRegistryFilterInput>(initialSavedViewStateRef.current.filters);
  const [resultShareRegistrySorts, setResultShareRegistrySorts] =
    useState<ResultShareRegistrySortInput>(initialSavedViewStateRef.current.sorts);
  const [resultShareRegistrySortDraft, setResultShareRegistrySortDraft] =
    useState<ResultShareRegistrySortInput>(initialSavedViewStateRef.current.sorts);
  const [resultShareRegistrySavedViews, setResultShareRegistrySavedViews] =
    useState<ResultShareRegistrySavedViewStoreState>(initialSavedViewStoreRef.current);
  const [grantSavedViewName, setGrantSavedViewName] = useState("");
  const [aliasSavedViewName, setAliasSavedViewName] = useState("");
  const [grantSavedViewIncludesDrilldown, setGrantSavedViewIncludesDrilldown] = useState(false);
  const [aliasSavedViewIncludesDrilldown, setAliasSavedViewIncludesDrilldown] = useState(false);
  const [activeRegistryPreset, setActiveRegistryPreset] = useState<ActiveRegistryPresetState>(
    initialActiveRegistryPresetRef.current,
  );
  const [shareDrilldownContextSource, setShareDrilldownContextSource] =
    useState<ShareDrilldownContextSourceState>(initialShareDrilldownContextSourceRef.current);
  const [resultShareRegistryPresetImportMode, setResultShareRegistryPresetImportMode] =
    useState<ResultShareRegistryPresetImportMode>("merge");
  const [resultShareRegistryPresetImportPreview, setResultShareRegistryPresetImportPreview] =
    useState<ResultShareRegistryPresetImportPreview | null>(null);
  const [resultShareRegistryPresetWorkspaceImportMode, setResultShareRegistryPresetWorkspaceImportMode] =
    useState<ResultShareRegistryPresetImportMode>("merge");
  const [resultShareRegistryPresetWorkspaceImportPreview, setResultShareRegistryPresetWorkspaceImportPreview] =
    useState<ResultShareRegistryPresetWorkspaceImportPreview | null>(null);
  const [
    resultShareRegistryPresetWorkspaceHealthCheckedAt,
    setResultShareRegistryPresetWorkspaceHealthCheckedAt,
  ] = useState<string>(() => new Date().toISOString());
  const [resultShareRegistryPresetLocalAuditEvents, setResultShareRegistryPresetLocalAuditEvents] =
    useState<ResultShareRegistryPresetLocalAuditEvent[]>(initialPresetAuditRef.current.events);
  const [
    resultShareRegistryPresetLocalAuditStorageWarning,
    setResultShareRegistryPresetLocalAuditStorageWarning,
  ] = useState<string | null>(initialPresetAuditRef.current.storageWarning);
  const [resultShareRegistryPresetWorkspaceState, setResultShareRegistryPresetWorkspaceState] =
    useState<ResultShareRegistryPresetWorkspaceState>(
      initialPresetWorkspaceStateRef.current.state,
    );
  const [resultShareRegistryPresetWorkspaceLastGoodBackup, setResultShareRegistryPresetWorkspaceLastGoodBackup] =
    useState<ResultShareRegistryPresetWorkspaceBackupSnapshot | null>(
      initialPresetWorkspaceBackupRef.current,
    );
  const [
    resultShareRegistryPresetWorkspaceStorageWarning,
    setResultShareRegistryPresetWorkspaceStorageWarning,
  ] = useState<string | null>(initialPresetWorkspaceStateRef.current.storageWarning);
  const [resultShareRegistryPresetIntegrityReport, setResultShareRegistryPresetIntegrityReport] =
    useState<ResultShareRegistryPresetIntegrityReport>(
      initialPresetInspectionRef.current.report,
    );
  const [
    resultShareRegistryPresetStorageDiagnostics,
    setResultShareRegistryPresetStorageDiagnostics,
  ] = useState<ResultShareRegistryPresetStorageDiagnostics>(
    initialPresetInspectionRef.current.diagnostics,
  );
  const [resultShareRegistryPresetLastGoodBackup, setResultShareRegistryPresetLastGoodBackup] =
    useState<ResultShareRegistryPresetBackupSnapshot | null>(
      initialPresetInspectionRef.current.lastGoodBackup,
    );
  const [shareGrantLookupId, setShareGrantLookupId] = useState("");
  const [shareAliasLookupId, setShareAliasLookupId] = useState("");
  const [createInput, setCreateInput] = useState<WorkspaceCreateInput>({
    slug: "",
    name: "",
    description: "",
  });
  const [updateInput, setUpdateInput] = useState<WorkspaceUpdateInput>({
    name: "",
    description: "",
    status: "active",
  });
  const [memberInput, setMemberInput] = useState<WorkspaceMemberAddInput>({
    user_id: "",
    role: "viewer",
  });
  const [paperInput, setPaperInput] = useState<WorkspacePaperAddInput>({
    paper_id: "",
  });
  const [shareInput, setShareInput] = useState<WorkspaceBoardShareCreateInput>({
    display_label: "",
    expires_at: null,
  });
  const locationConsumedRef = useRef(false);
  const defaultRegistrySavedViewState = useMemo(
    () => buildInitialResultShareRegistrySavedViewState(resultShareRegistrySavedViews),
    [resultShareRegistrySavedViews],
  );

  const resetConnectedState = useCallback(() => {
    setSession(null);
    setWorkspaces([]);
    setUsers([]);
    setPapers([]);
    setSelectedWorkspaceId(null);
    setSelectedWorkspace(null);
    setSelectedBoard(null);
    setSelectedShareGrants([]);
    setResultShareGrants([]);
    setResultShareAliases([]);
    setGlobalConversionOverview(null);
    setGlobalConversionDrilldown(null);
    setWorkspaceConversionOverview(null);
    setWorkspaceConversionDrilldown(null);
    setShareGrantDrilldown(null);
    setShareAliasDrilldown(null);
    setShareDrilldownTarget(null);
    setBoardCache({});
    setGlobalConversionError(null);
    setGlobalConversionDrilldownError(null);
    setWorkspaceConversionError(null);
    setWorkspaceConversionDrilldownError(null);
    setResultShareRegistryError(null);
    setShareDrilldownError(null);
    setGlobalConversionFilters(DEFAULT_CONVERSION_FILTER_INPUT);
    setGlobalConversionFilterDraft(DEFAULT_CONVERSION_FILTER_INPUT);
    setWorkspaceConversionFilters(DEFAULT_CONVERSION_FILTER_INPUT);
    setWorkspaceConversionFilterDraft(DEFAULT_CONVERSION_FILTER_INPUT);
    setShareDrilldownFilters(defaultRegistrySavedViewState.drilldownFilters);
    setShareDrilldownFilterDraft(defaultRegistrySavedViewState.drilldownFilters);
    setResultShareRegistryFilters(defaultRegistrySavedViewState.filters);
    setResultShareRegistryFilterDraft(defaultRegistrySavedViewState.filters);
    setResultShareRegistrySorts(defaultRegistrySavedViewState.sorts);
    setResultShareRegistrySortDraft(defaultRegistrySavedViewState.sorts);
    setGrantSavedViewName("");
    setAliasSavedViewName("");
    setGrantSavedViewIncludesDrilldown(false);
    setAliasSavedViewIncludesDrilldown(false);
    setResultShareRegistryPresetImportMode("merge");
    setResultShareRegistryPresetImportPreview(null);
    setResultShareRegistryPresetWorkspaceImportMode("merge");
    setResultShareRegistryPresetWorkspaceImportPreview(null);
    setActiveRegistryPreset(
      buildActiveRegistryPresetState(
        defaultRegistrySavedViewState.defaultPreset,
        "default_preset",
      ),
    );
    setShareDrilldownContextSource(
      buildShareDrilldownContextSourceState(
        defaultRegistrySavedViewState.defaultPreset,
        "default_preset",
      ),
    );
    setShareGrantLookupId("");
    setShareAliasLookupId("");
    setOneTimeGrant(null);
  }, [
    defaultRegistrySavedViewState.defaultPreset,
    defaultRegistrySavedViewState.drilldownFilters,
    defaultRegistrySavedViewState.filters,
    defaultRegistrySavedViewState.sorts,
  ]);

  const toApiErrorViewModel = useCallback((error: unknown): ApiErrorViewModel => {
    if (error instanceof GroupWorkspaceAdminApiError) {
      return buildApiErrorViewModel(error);
    }
    return buildApiErrorViewModel({
      kind: "request_failed",
      detail: error instanceof Error ? error.message : String(error),
    });
  }, []);

  const handleError = useCallback(
    (error: unknown, setter: (error: ApiErrorViewModel | null) => void) => {
      setter(toApiErrorViewModel(error));
    },
    [toApiErrorViewModel],
  );

  const loadGlobalConversionPanels = useCallback(
    async (
      client: GroupWorkspaceAdminApiClient,
      filters: ConversionFilterInput,
    ) => {
      setGlobalConversionLoading(true);
      setGlobalConversionDrilldownLoading(true);
      setGlobalConversionError(null);
      setGlobalConversionDrilldownError(null);
      try {
        const [overviewResult, drilldownResult] = await Promise.all([
          client
            .getConversionOverview(filters)
            .then((overview) => ({ overview, error: null }))
            .catch((error: unknown) => ({
              overview: null,
              error: toApiErrorViewModel(error),
            })),
          client
            .getConversionDrilldown(filters)
            .then((drilldown) => ({ drilldown, error: null }))
            .catch((error: unknown) => ({
              drilldown: null,
              error: toApiErrorViewModel(error),
            })),
        ]);
        setGlobalConversionOverview(overviewResult.overview);
        setGlobalConversionError(overviewResult.error);
        setGlobalConversionDrilldown(drilldownResult.drilldown);
        setGlobalConversionDrilldownError(drilldownResult.error);
      } finally {
        setGlobalConversionLoading(false);
        setGlobalConversionDrilldownLoading(false);
      }
    },
    [toApiErrorViewModel],
  );

  const loadWorkspaceConversionPanels = useCallback(
    async (
      client: GroupWorkspaceAdminApiClient,
      workspaceId: string,
      filters: ConversionFilterInput,
    ) => {
      setWorkspaceConversionLoading(true);
      setWorkspaceConversionDrilldownLoading(true);
      setWorkspaceConversionError(null);
      setWorkspaceConversionDrilldownError(null);
      try {
        const [overviewResult, drilldownResult] = await Promise.all([
          client
            .getWorkspaceConversionOverview(workspaceId, filters)
            .then((conversion) => ({ conversion, error: null }))
            .catch((error: unknown) => ({
              conversion: null,
              error: toApiErrorViewModel(error),
            })),
          client
            .getWorkspaceConversionDrilldown(workspaceId, filters)
            .then((drilldown) => ({ drilldown, error: null }))
            .catch((error: unknown) => ({
              drilldown: null,
              error: toApiErrorViewModel(error),
            })),
        ]);
        setWorkspaceConversionOverview(overviewResult.conversion);
        setWorkspaceConversionError(overviewResult.error);
        setWorkspaceConversionDrilldown(drilldownResult.drilldown);
        setWorkspaceConversionDrilldownError(drilldownResult.error);
      } finally {
        setWorkspaceConversionLoading(false);
        setWorkspaceConversionDrilldownLoading(false);
      }
    },
    [toApiErrorViewModel],
  );

  const loadResultShareRegistry = useCallback(
    async (
      client: GroupWorkspaceAdminApiClient,
      filters: ResultShareRegistryFilterInput,
    ) => {
      setResultShareRegistryLoading(true);
      setResultShareRegistryError(null);
      try {
        const [grants, aliases] = await Promise.all([
          client.listResultShareGrants({
            workspaceId: filters.workspaceId ?? undefined,
            shareKind: filters.shareKind ?? undefined,
            status: filters.grantStatus ?? undefined,
          }),
          client.listResultShareAliases({
            resultShareGrantId: filters.resultShareGrantId ?? undefined,
            shareKind: filters.shareKind ?? undefined,
            status: filters.aliasStatus ?? undefined,
          }),
        ]);
        setResultShareGrants(grants);
        setResultShareAliases(aliases);
      } catch (error) {
        setResultShareGrants([]);
        setResultShareAliases([]);
        setResultShareRegistryError(toApiErrorViewModel(error));
      } finally {
        setResultShareRegistryLoading(false);
      }
    },
    [toApiErrorViewModel],
  );

  const loadShareDrilldown = useCallback(
    async (
      client: GroupWorkspaceAdminApiClient,
      target: ShareDrilldownTarget,
      filters: ConversionFilterInput,
    ) => {
      setShareDrilldownTarget(target);
      setShareDrilldownLoading(true);
      setShareDrilldownError(null);
      try {
        if (target.kind === "grant") {
          const drilldown = await client.getResultShareGrantConversionDrilldown(
            target.id,
            filters,
          );
          setShareGrantDrilldown(drilldown);
          setShareAliasDrilldown(null);
          setShareGrantLookupId(target.id);
        } else {
          const drilldown = await client.getResultShareAliasConversionDrilldown(target.id, filters);
          setShareAliasDrilldown(drilldown);
          setShareGrantDrilldown(null);
          setShareAliasLookupId(target.id);
        }
      } catch (error) {
        setShareGrantDrilldown(null);
        setShareAliasDrilldown(null);
        setShareDrilldownError(toApiErrorViewModel(error));
      } finally {
        setShareDrilldownLoading(false);
      }
    },
    [toApiErrorViewModel],
  );

  const loadWorkspaceContext = useCallback(
    async (
      client: GroupWorkspaceAdminApiClient,
      workspaceId: string,
      filters: ConversionFilterInput,
    ) => {
      setLoadingMessage("Loading workspace detail and board...");
      setActionError(null);
      try {
        const [workspace, board, shareGrants] = await Promise.all([
          client.getWorkspace(workspaceId),
          client.getWorkspaceBoard(workspaceId),
          client.listResultShareGrants({
            workspaceId,
            shareKind: "workspace_board",
          }),
        ]);
        setSelectedWorkspaceId(workspaceId);
        setSelectedWorkspace(workspace);
        setSelectedBoard(board);
        setSelectedShareGrants(shareGrants);
        setUpdateInput({
          name: workspace.name,
          description: workspace.description ?? "",
          status: workspace.status,
        });
        setBoardCache((current) => ({
          ...current,
          [workspaceId]: board,
        }));
        await loadWorkspaceConversionPanels(client, workspaceId, filters);
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError, loadWorkspaceConversionPanels],
  );

  const connectWithToken = useCallback(
    async ({
      adminToken,
      apiBaseUrl,
      source,
    }: {
      adminToken: string;
      apiBaseUrl: string;
      source: "manual" | "query" | "fragment";
    }) => {
      const trimmedToken = adminToken.trim();
      const trimmedApiBaseUrl = apiBaseUrl.trim();
      if (!trimmedToken) {
        setConnectError({
          kind: "unauthorized",
          title: "Missing admin bearer token",
          message: "Paste an admin/operator bearer token from POST /auth/login.",
        });
        return;
      }
      if (!trimmedApiBaseUrl) {
        setConnectError({
          kind: "request_failed",
          title: "Missing API base URL",
          message: "Set an API base URL before opening the workspace shell.",
        });
        return;
      }

      setLoadingMessage("Connecting admin shell...");
      setConnectError(null);
      setActionError(null);
      setNoticeMessage(
        source === "query" || source === "fragment"
          ? "Admin bearer token was moved from the URL into in-memory state."
          : null,
      );

      const client = apiClientFactory({
        apiBaseUrl: trimmedApiBaseUrl,
        accessToken: trimmedToken,
      });

      try {
        const [workspaceList, userList, paperList] = await Promise.all([
          client.listWorkspaces(),
          client.listUsers(),
          client.listPapers(),
        ]);
        setSession({
          apiBaseUrl: trimmedApiBaseUrl,
          adminToken: trimmedToken,
          client,
        });
        setWorkspaces(workspaceList);
        setUsers(userList);
        setPapers(paperList);
        setAdminTokenInput("");
        await loadGlobalConversionPanels(client, globalConversionFilters);
        await loadResultShareRegistry(client, resultShareRegistryFilters);

        const initialWorkspaceId = workspaceList[0]?.id ?? null;
        if (initialWorkspaceId) {
          await loadWorkspaceContext(client, initialWorkspaceId, workspaceConversionFilters);
        } else {
          setSelectedWorkspaceId(null);
          setSelectedWorkspace(null);
          setSelectedBoard(null);
          setSelectedShareGrants([]);
          setWorkspaceConversionOverview(null);
          setWorkspaceConversionDrilldown(null);
        }
      } catch (error) {
        resetConnectedState();
        handleError(error, setConnectError);
        setAdminTokenInput(source === "manual" ? trimmedToken : "");
      } finally {
        setLoadingMessage(null);
      }
    },
    [
      apiClientFactory,
      globalConversionFilters,
      handleError,
      loadGlobalConversionPanels,
      loadResultShareRegistry,
      loadWorkspaceContext,
      resetConnectedState,
      resultShareRegistryFilters,
      workspaceConversionFilters,
    ],
  );

  useEffect(() => {
    if (locationConsumedRef.current || !resolvedLocation) {
      return;
    }
    locationConsumedRef.current = true;
    const extracted = extractAdminTokenFromLocation(resolvedLocation);
    if (!extracted.adminToken || extracted.source === "none") {
      return;
    }

    if (
      resolvedHistory &&
      (extracted.source === "query" || extracted.source === "fragment")
    ) {
      clearVisibleAdminTokenHints(resolvedLocation, resolvedHistory);
    }

    void connectWithToken({
      adminToken: extracted.adminToken,
      apiBaseUrl: apiBaseUrlInput,
      source: extracted.source,
    });
  }, [apiBaseUrlInput, connectWithToken, resolvedHistory, resolvedLocation]);

  const refreshWorkspaces = useCallback(async () => {
    if (!session) {
      return;
    }
    const latest = await session.client.listWorkspaces();
    setWorkspaces(latest);
    return latest;
  }, [session]);

  const refreshWorkspaceContext = useCallback(async () => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    await loadWorkspaceContext(session.client, selectedWorkspaceId, workspaceConversionFilters);
  }, [loadWorkspaceContext, selectedWorkspaceId, session, workspaceConversionFilters]);

  const availableUserOptions = useMemo(() => {
    const currentMemberIds = new Set((selectedBoard?.members ?? []).map((member) => member.user_id));
    return buildUserLookupOptions(users.filter((user) => !currentMemberIds.has(user.id)));
  }, [selectedBoard, users]);

  const availablePaperOptions = useMemo(() => {
    const currentPaperIds = new Set((selectedBoard?.papers ?? []).map((paper) => paper.paper_id));
    return buildPaperLookupOptions(papers.filter((paper) => !currentPaperIds.has(paper.id)));
  }, [papers, selectedBoard]);

  const workspaceListItems = useMemo(
    () => buildWorkspaceListItems(workspaces, boardCache),
    [boardCache, workspaces],
  );

  const boardViewModel = useMemo(
    () => (selectedBoard ? buildWorkspaceBoardViewModel(selectedBoard) : null),
    [selectedBoard],
  );
  const globalConversionViewModel = useMemo(
    () =>
      globalConversionOverview
        ? buildGlobalConversionOverviewViewModel(globalConversionOverview)
        : null,
    [globalConversionOverview],
  );
  const globalConversionDrilldownViewModel = useMemo(
    () =>
      globalConversionDrilldown
        ? buildGlobalConversionDrilldownViewModel(globalConversionDrilldown)
        : null,
    [globalConversionDrilldown],
  );
  const workspaceConversionViewModel = useMemo(
    () =>
      workspaceConversionOverview
        ? buildWorkspaceConversionOverviewViewModel(workspaceConversionOverview)
        : null,
    [workspaceConversionOverview],
  );
  const workspaceConversionDrilldownViewModel = useMemo(
    () =>
      workspaceConversionDrilldown
        ? buildWorkspaceConversionDrilldownViewModel(workspaceConversionDrilldown)
        : null,
    [workspaceConversionDrilldown],
  );
  const globalConversionFilterSummary = useMemo(
    () =>
      buildConversionFilterSummaryViewModel(
        globalConversionFilters,
        GLOBAL_CONVERSION_FILTER_SUPPORT,
      ),
    [globalConversionFilters],
  );
  const workspaceConversionFilterSummary = useMemo(
    () =>
      buildConversionFilterSummaryViewModel(
        workspaceConversionFilters,
        WORKSPACE_CONVERSION_FILTER_SUPPORT,
      ),
    [workspaceConversionFilters],
  );
  const shareDrilldownGrantViewModel = useMemo(
    () =>
      shareGrantDrilldown
        ? buildResultShareGrantDrilldownViewModel(shareGrantDrilldown)
        : null,
    [shareGrantDrilldown],
  );
  const shareDrilldownAliasViewModel = useMemo(
    () =>
      shareAliasDrilldown
        ? buildResultShareAliasDrilldownViewModel(shareAliasDrilldown)
        : null,
    [shareAliasDrilldown],
  );
  const shareDrilldownFilterSummary = useMemo(
    () =>
      buildConversionFilterSummaryViewModel(
        shareDrilldownFilters,
        PER_SHARE_DRILLDOWN_FILTER_SUPPORT,
      ),
    [shareDrilldownFilters],
  );
  const resultShareRegistryViewModel = useMemo(
    () =>
      buildResultShareRegistryViewModel(
        resultShareGrants,
        resultShareAliases,
        resultShareRegistryFilters,
        resultShareRegistrySorts,
      ),
    [resultShareAliases, resultShareGrants, resultShareRegistryFilters, resultShareRegistrySorts],
  );
  const resultShareRegistryFilterSummary = useMemo(
    () =>
      buildResultShareRegistryFilterSummaryViewModel(
        resultShareRegistryFilters,
        resultShareRegistrySorts,
      ),
    [resultShareRegistryFilters, resultShareRegistrySorts],
  );
  const resultShareRegistrySavedViewSummaries = useMemo(
    () =>
      buildResultShareRegistrySavedViewSummaries(
        resultShareRegistrySavedViews,
        resultShareRegistryPresetWorkspaceState,
      ),
    [resultShareRegistryPresetWorkspaceState, resultShareRegistrySavedViews],
  );
  const resultShareRegistryPresetLocalAuditSummary = useMemo<ResultShareRegistryPresetLocalAuditSummary>(
    () =>
      buildResultShareRegistryPresetAuditSummary(
        resultShareRegistryPresetLocalAuditEvents,
        {
          storageWarning: resultShareRegistryPresetLocalAuditStorageWarning,
        },
      ),
    [
      resultShareRegistryPresetLocalAuditEvents,
      resultShareRegistryPresetLocalAuditStorageWarning,
    ],
  );
  const resultShareRegistryPresetWorkspaceViewModel =
    useMemo<ResultShareRegistryPresetWorkspaceViewModel>(
      () =>
        buildResultShareRegistryPresetWorkspaceViewModel(
          resultShareRegistrySavedViewSummaries,
          resultShareRegistryPresetWorkspaceState,
          resultShareRegistryPresetLocalAuditSummary,
          resultShareRegistryPresetStorageDiagnostics,
          resultShareRegistryPresetLastGoodBackup,
          resultShareRegistryPresetWorkspaceLastGoodBackup,
        ),
      [
        resultShareRegistryPresetLastGoodBackup,
        resultShareRegistryPresetLocalAuditSummary,
        resultShareRegistryPresetStorageDiagnostics,
        resultShareRegistryPresetWorkspaceLastGoodBackup,
        resultShareRegistryPresetWorkspaceState,
        resultShareRegistrySavedViewSummaries,
      ],
    );
  const resultShareRegistryPresetWorkspaceHealthScore =
    useMemo<ResultShareRegistryPresetWorkspaceHealthScore>(
      () =>
        buildResultShareRegistryPresetWorkspaceHealthScore({
          store: resultShareRegistrySavedViews,
          integrityReport: resultShareRegistryPresetIntegrityReport,
          diagnostics: resultShareRegistryPresetStorageDiagnostics,
          lastGoodBackup: resultShareRegistryPresetLastGoodBackup,
          workspaceBackup: resultShareRegistryPresetWorkspaceLastGoodBackup,
          workspaceState: resultShareRegistryPresetWorkspaceState,
          auditSummary: resultShareRegistryPresetLocalAuditSummary,
          workspaceImportPreview: resultShareRegistryPresetWorkspaceImportPreview,
          checkedAt: resultShareRegistryPresetWorkspaceHealthCheckedAt,
        }),
      [
        resultShareRegistryPresetIntegrityReport,
        resultShareRegistryPresetLastGoodBackup,
        resultShareRegistryPresetLocalAuditSummary,
        resultShareRegistryPresetStorageDiagnostics,
        resultShareRegistryPresetWorkspaceHealthCheckedAt,
        resultShareRegistryPresetWorkspaceImportPreview,
        resultShareRegistryPresetWorkspaceLastGoodBackup,
        resultShareRegistryPresetWorkspaceState,
        resultShareRegistrySavedViews,
      ],
    );
  const activeRegistryPresetLabel = useMemo(() => {
    if (!activeRegistryPreset) {
      return null;
    }
    return `${activeRegistryPreset.source === "default_preset" ? "Default preset" : "Active preset"} · ${activeRegistryPreset.presetName}`;
  }, [activeRegistryPreset]);
  const shareDrilldownContextLabel = useMemo(() => {
    if (shareDrilldownContextSource.kind === "saved_view") {
      return `Saved view drilldown context · ${shareDrilldownContextSource.presetName ?? "Preset"}`;
    }
    if (shareDrilldownContextSource.kind === "default_preset") {
      return `Default preset drilldown context · ${shareDrilldownContextSource.presetName ?? "Preset"}`;
    }
    return "Manual / current per-share drilldown filters";
  }, [shareDrilldownContextSource]);
  const shareDrilldownCurrentTargetLabel = useMemo(() => {
    if (shareDrilldownGrantViewModel) {
      return `Grant · ${shareDrilldownGrantViewModel.shareGrant.title}`;
    }
    if (shareDrilldownAliasViewModel) {
      return `Alias · ${shareDrilldownAliasViewModel.alias.title}`;
    }
    if (shareDrilldownTarget) {
      return `${shareDrilldownTarget.kind === "grant" ? "Grant" : "Alias"} · ${shareDrilldownTarget.id}`;
    }
    return null;
  }, [shareDrilldownAliasViewModel, shareDrilldownGrantViewModel, shareDrilldownTarget]);

  const findSavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string): ResultShareRegistrySavedView | null => {
      const presets =
        scope === "grant_registry"
          ? resultShareRegistrySavedViews.grantPresets
          : resultShareRegistrySavedViews.aliasPresets;
      return presets.find((preset) => preset.id === presetId) ?? null;
    },
    [resultShareRegistrySavedViews],
  );

  const syncPresetReferencesWithStore = useCallback(
    (nextStore: ResultShareRegistrySavedViewStoreState) => {
      setActiveRegistryPreset((current) => {
        if (!current) {
          return null;
        }
        const preset = findSavedViewInStore(nextStore, current.presetId, current.scope);
        if (!preset) {
          return null;
        }
        return {
          ...current,
          presetName: preset.name,
          source:
            current.source === "default_preset" && nextStore.defaultPresetId !== preset.id
              ? "saved_view"
              : current.source,
        };
      });
      setShareDrilldownContextSource((current) => {
        if (current.kind === "manual") {
          return current;
        }
        const preset = findSavedViewInStore(nextStore, current.presetId);
        if (!preset?.drilldownContext) {
          return {
            kind: "manual",
            presetId: null,
            presetName: null,
          };
        }
        return {
          kind:
            current.kind === "default_preset" && nextStore.defaultPresetId === preset.id
              ? "default_preset"
              : "saved_view",
          presetId: preset.id,
          presetName: preset.name,
        };
      });
    },
    [],
  );

  const applyPresetStorageInspection = useCallback(
    (
      store: ResultShareRegistrySavedViewStoreState,
      report: ResultShareRegistryPresetIntegrityReport,
      diagnostics: ResultShareRegistryPresetStorageDiagnostics,
      lastGoodBackup: ResultShareRegistryPresetBackupSnapshot | null,
    ) => {
      setResultShareRegistrySavedViews(store);
      setResultShareRegistryPresetIntegrityReport(report);
      setResultShareRegistryPresetStorageDiagnostics(diagnostics);
      setResultShareRegistryPresetLastGoodBackup(lastGoodBackup);
      syncPresetReferencesWithStore(store);
    },
    [syncPresetReferencesWithStore],
  );

  const commitResultShareRegistrySavedViewStore = useCallback(
    (
      nextStore: ResultShareRegistrySavedViewStoreState,
      options?: {
        backup?: ResultShareRegistryPresetBackupSnapshot | null;
      },
    ) => {
      const storage = getLocalStorageSafe();
      if (storage) {
        persistResultShareRegistrySavedViewStore(storage, nextStore);
        if (Object.prototype.hasOwnProperty.call(options ?? {}, "backup")) {
          persistResultShareRegistryPresetBackup(storage, options?.backup ?? null);
        }
        const inspection = inspectResultShareRegistryPresetStorage(storage);
        const workspaceStateLoad = loadResultShareRegistryPresetWorkspaceState(storage);
        setResultShareRegistryPresetWorkspaceState(
          syncResultShareRegistryPresetWorkspaceStateWithStore(
            workspaceStateLoad.state,
            inspection.store,
          ),
        );
        setResultShareRegistryPresetWorkspaceStorageWarning(
          workspaceStateLoad.storageWarning,
        );
        applyPresetStorageInspection(
          inspection.store,
          inspection.report,
          inspection.diagnostics,
          inspection.lastGoodBackup,
        );
        return inspection;
      }

      const checkedAt = new Date().toISOString();
      const backup =
        Object.prototype.hasOwnProperty.call(options ?? {}, "backup")
          ? options?.backup ?? null
          : resultShareRegistryPresetLastGoodBackup;
      const fallback = buildFallbackPresetStorageDiagnostics(
        nextStore,
        backup,
        resultShareRegistryPresetWorkspaceState,
        resultShareRegistryPresetWorkspaceStorageWarning,
        checkedAt,
      );
      applyPresetStorageInspection(nextStore, fallback.report, fallback.diagnostics, backup);
      return {
        store: nextStore,
        report: fallback.report,
        diagnostics: fallback.diagnostics,
        lastGoodBackup: backup,
      };
    },
    [
      applyPresetStorageInspection,
      resultShareRegistryPresetLastGoodBackup,
      resultShareRegistryPresetWorkspaceState,
      resultShareRegistryPresetWorkspaceStorageWarning,
    ],
  );

  const refreshResultShareRegistryPresetDiagnostics = useCallback(() => {
    const storage = getLocalStorageSafe();
    if (storage) {
      const inspection = inspectResultShareRegistryPresetStorage(storage);
      const workspaceStateLoad = loadResultShareRegistryPresetWorkspaceState(storage);
      setResultShareRegistryPresetWorkspaceState(
        syncResultShareRegistryPresetWorkspaceStateWithStore(
          workspaceStateLoad.state,
          inspection.store,
        ),
      );
      setResultShareRegistryPresetWorkspaceStorageWarning(
        workspaceStateLoad.storageWarning,
      );
      applyPresetStorageInspection(
        inspection.store,
        inspection.report,
        inspection.diagnostics,
        inspection.lastGoodBackup,
      );
      return inspection;
    }
    const checkedAt = new Date().toISOString();
    const fallback = buildFallbackPresetStorageDiagnostics(
      resultShareRegistrySavedViews,
      resultShareRegistryPresetLastGoodBackup,
      resultShareRegistryPresetWorkspaceState,
      resultShareRegistryPresetWorkspaceStorageWarning,
      checkedAt,
    );
    applyPresetStorageInspection(
      resultShareRegistrySavedViews,
      fallback.report,
      fallback.diagnostics,
      resultShareRegistryPresetLastGoodBackup,
    );
    return {
      store: resultShareRegistrySavedViews,
      report: fallback.report,
      diagnostics: fallback.diagnostics,
      lastGoodBackup: resultShareRegistryPresetLastGoodBackup,
    };
  }, [
    applyPresetStorageInspection,
    resultShareRegistryPresetLastGoodBackup,
    resultShareRegistryPresetWorkspaceState,
    resultShareRegistryPresetWorkspaceStorageWarning,
    resultShareRegistrySavedViews,
  ]);

  const recordResultShareRegistryPresetAuditEvent = useCallback(
    (event: ResultShareRegistryPresetLocalAuditEvent) => {
      try {
        const nextAudit = appendResultShareRegistryPresetAuditEvent(
          getLocalStorageSafe(),
          event,
        );
        setResultShareRegistryPresetLocalAuditEvents(nextAudit.events);
        setResultShareRegistryPresetLocalAuditStorageWarning(nextAudit.storageWarning);
      } catch {
        // Local audit history must never block the original preset action.
      }
    },
    [],
  );

  const clearResultShareRegistryPresetLocalAudit = useCallback(() => {
    clearResultShareRegistryPresetAuditEvents(getLocalStorageSafe());
    setResultShareRegistryPresetLocalAuditEvents([]);
    setResultShareRegistryPresetLocalAuditStorageWarning(null);
  }, []);

  const handleRecalculateResultShareRegistryPresetWorkspaceHealth = useCallback(() => {
    setResultShareRegistryPresetWorkspaceHealthCheckedAt(new Date().toISOString());
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_health_checked",
        "success",
        "Recalculated the local preset workspace health score.",
        {
          scope: "storage",
        },
      ),
    );
    setNoticeMessage("Recalculated the local preset workspace health score.");
  }, [recordResultShareRegistryPresetAuditEvent]);

  const commitResultShareRegistryPresetWorkspaceState = useCallback(
    (
      nextState: ResultShareRegistryPresetWorkspaceState,
      options?: {
        backup?: ResultShareRegistryPresetWorkspaceBackupSnapshot | null;
      },
    ) => {
      const storage = getLocalStorageSafe();
      const syncedState = syncResultShareRegistryPresetWorkspaceStateWithStore(
        nextState,
        resultShareRegistrySavedViews,
      );
      const workspaceBackup =
        Object.prototype.hasOwnProperty.call(options ?? {}, "backup")
          ? options?.backup ?? null
          : resultShareRegistryPresetWorkspaceLastGoodBackup;
      if (storage) {
        const persisted = persistResultShareRegistryPresetWorkspaceState(storage, syncedState);
        if (Object.prototype.hasOwnProperty.call(options ?? {}, "backup")) {
          setResultShareRegistryPresetWorkspaceLastGoodBackup(
            persistResultShareRegistryPresetWorkspaceBackup(storage, options?.backup ?? null),
          );
        }
        setResultShareRegistryPresetWorkspaceState(persisted);
        setResultShareRegistryPresetWorkspaceStorageWarning(null);
        const inspection = inspectResultShareRegistryPresetStorage(storage);
        applyPresetStorageInspection(
          inspection.store,
          inspection.report,
          inspection.diagnostics,
          inspection.lastGoodBackup,
        );
        return persisted;
      }
      const checkedAt = new Date().toISOString();
      const fallback = buildFallbackPresetStorageDiagnostics(
        resultShareRegistrySavedViews,
        resultShareRegistryPresetLastGoodBackup,
        syncedState,
        null,
        checkedAt,
      );
      if (Object.prototype.hasOwnProperty.call(options ?? {}, "backup")) {
        setResultShareRegistryPresetWorkspaceLastGoodBackup(workspaceBackup);
      }
      setResultShareRegistryPresetWorkspaceState(syncedState);
      setResultShareRegistryPresetWorkspaceStorageWarning(null);
      applyPresetStorageInspection(
        resultShareRegistrySavedViews,
        fallback.report,
        fallback.diagnostics,
        resultShareRegistryPresetLastGoodBackup,
      );
      return syncedState;
    },
    [
      applyPresetStorageInspection,
      resultShareRegistryPresetWorkspaceLastGoodBackup,
      resultShareRegistryPresetLastGoodBackup,
      resultShareRegistrySavedViews,
    ],
  );

  const mutateResultShareRegistryPresetStorage = useCallback(
    (
      mutate: (storage: Storage) => void,
      options?: {
        backupReason?: string;
        fallbackStore?: ResultShareRegistrySavedViewStoreState;
      },
    ) => {
      const storage = getLocalStorageSafe();
      const backup =
        options?.backupReason
          ? createResultShareRegistryPresetBackup(
              resultShareRegistrySavedViews,
              options.backupReason,
            )
          : undefined;
      if (storage) {
        if (backup) {
          persistResultShareRegistryPresetBackup(storage, backup);
        }
        mutate(storage);
        const inspection = inspectResultShareRegistryPresetStorage(storage);
        const workspaceStateLoad = loadResultShareRegistryPresetWorkspaceState(storage);
        setResultShareRegistryPresetWorkspaceState(
          syncResultShareRegistryPresetWorkspaceStateWithStore(
            workspaceStateLoad.state,
            inspection.store,
          ),
        );
        setResultShareRegistryPresetWorkspaceStorageWarning(
          workspaceStateLoad.storageWarning,
        );
        applyPresetStorageInspection(
          inspection.store,
          inspection.report,
          inspection.diagnostics,
          inspection.lastGoodBackup,
        );
        return inspection;
      }
      return commitResultShareRegistrySavedViewStore(
        options?.fallbackStore ?? resultShareRegistrySavedViews,
        Object.prototype.hasOwnProperty.call(options ?? {}, "backupReason")
          ? { backup: backup ?? null }
          : undefined,
      );
    },
    [
      applyPresetStorageInspection,
      commitResultShareRegistrySavedViewStore,
      resultShareRegistrySavedViews,
    ],
  );

  const confirmPresetRecoveryAction = useCallback((message: string) => {
    if (typeof window === "undefined" || typeof window.confirm !== "function") {
      return true;
    }
    return window.confirm(message);
  }, []);

  const patchGlobalFilterDraft = useCallback((patch: Partial<ConversionFilterInput>) => {
    setGlobalConversionFilterDraft((current) =>
      normalizeConversionFilterInput({
        ...current,
        ...patch,
      }),
    );
  }, []);

  const patchWorkspaceFilterDraft = useCallback((patch: Partial<ConversionFilterInput>) => {
    setWorkspaceConversionFilterDraft((current) =>
      normalizeConversionFilterInput({
        ...current,
        ...patch,
      }),
    );
  }, []);

  const patchShareDrilldownFilterDraft = useCallback((patch: Partial<ConversionFilterInput>) => {
    setShareDrilldownContextSource({
      kind: "manual",
      presetId: null,
      presetName: null,
    });
    setShareDrilldownFilterDraft((current) =>
      normalizeConversionFilterInput({
        ...current,
        ...patch,
        shareKind: null,
      }),
    );
  }, []);

  const patchResultShareRegistryFilterDraft = useCallback(
    (patch: Partial<ResultShareRegistryFilterInput>) => {
      setActiveRegistryPreset(null);
      setResultShareRegistryFilterDraft((current) =>
        normalizeResultShareRegistryFilterInput({
          ...current,
          ...patch,
        }),
      );
    },
    [],
  );

  const patchResultShareRegistrySortDraft = useCallback(
    (patch: Partial<ResultShareRegistrySortInput>) => {
      setActiveRegistryPreset(null);
      setResultShareRegistrySortDraft((current) =>
        normalizeResultShareRegistrySortInput({
          ...current,
          ...patch,
        }),
      );
    },
    [],
  );

  const applyShareDrilldownContext = useCallback(
    (
      nextFilters: ConversionFilterInput,
      source: ShareDrilldownContextSourceState,
      options?: {
        reloadCurrentTarget?: boolean;
      },
    ) => {
      const normalizedFilters = normalizeConversionFilterInput({
        ...nextFilters,
        shareKind: null,
      });
      setShareDrilldownFilterDraft(normalizedFilters);
      setShareDrilldownFilters(normalizedFilters);
      setShareDrilldownContextSource(source);
      if (options?.reloadCurrentTarget !== false && session && shareDrilldownTarget) {
        void loadShareDrilldown(session.client, shareDrilldownTarget, normalizedFilters);
      }
    },
    [loadShareDrilldown, session, shareDrilldownTarget],
  );

  const handleOpenShell = useCallback(() => {
    void connectWithToken({
      adminToken: adminTokenInput,
      apiBaseUrl: apiBaseUrlInput,
      source: "manual",
    });
  }, [adminTokenInput, apiBaseUrlInput, connectWithToken]);

  const handleDisconnect = useCallback(() => {
    resetConnectedState();
    setAdminTokenInput("");
    setConnectError(null);
    setActionError(null);
    setNoticeMessage("Cleared the in-memory admin bearer token.");
  }, [resetConnectedState]);

  const runAction = useCallback(
    async (message: string, action: () => Promise<void>) => {
      setLoadingMessage(message);
      setActionError(null);
      try {
        await action();
      } catch (error) {
        handleError(error, setActionError);
      } finally {
        setLoadingMessage(null);
      }
    },
    [handleError],
  );

  const handleApplyGlobalFilters = useCallback(() => {
    if (!session) {
      return;
    }
    const nextFilters = normalizeConversionFilterInput(globalConversionFilterDraft);
    setGlobalConversionFilterDraft(nextFilters);
    setGlobalConversionFilters(nextFilters);
    void loadGlobalConversionPanels(session.client, nextFilters);
  }, [globalConversionFilterDraft, loadGlobalConversionPanels, session]);

  const handleResetGlobalFilters = useCallback(() => {
    if (!session) {
      return;
    }
    setGlobalConversionFilterDraft(DEFAULT_CONVERSION_FILTER_INPUT);
    setGlobalConversionFilters(DEFAULT_CONVERSION_FILTER_INPUT);
    void loadGlobalConversionPanels(session.client, DEFAULT_CONVERSION_FILTER_INPUT);
  }, [loadGlobalConversionPanels, session]);

  const handleApplyWorkspaceFilters = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    const nextFilters = normalizeConversionFilterInput(workspaceConversionFilterDraft);
    setWorkspaceConversionFilterDraft(nextFilters);
    setWorkspaceConversionFilters(nextFilters);
    void loadWorkspaceConversionPanels(session.client, selectedWorkspaceId, nextFilters);
  }, [
    loadWorkspaceConversionPanels,
    selectedWorkspaceId,
    session,
    workspaceConversionFilterDraft,
  ]);

  const handleResetWorkspaceFilters = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    setWorkspaceConversionFilterDraft(DEFAULT_CONVERSION_FILTER_INPUT);
    setWorkspaceConversionFilters(DEFAULT_CONVERSION_FILTER_INPUT);
    void loadWorkspaceConversionPanels(
      session.client,
      selectedWorkspaceId,
      DEFAULT_CONVERSION_FILTER_INPUT,
    );
  }, [loadWorkspaceConversionPanels, selectedWorkspaceId, session]);

  const handleOpenShareGrantDrilldown = useCallback(
    (grantId?: string) => {
      if (!session) {
        return;
      }
      const resolvedGrantId = (grantId ?? shareGrantLookupId).trim();
      if (!resolvedGrantId) {
        return;
      }
      const nextFilters = normalizeConversionFilterInput({
        ...shareDrilldownFilterDraft,
        shareKind: null,
      });
      setShareDrilldownFilterDraft(nextFilters);
      setShareDrilldownFilters(nextFilters);
      setShareGrantLookupId(resolvedGrantId);
      void loadShareDrilldown(
        session.client,
        { kind: "grant", id: resolvedGrantId },
        nextFilters,
      );
    },
    [loadShareDrilldown, session, shareDrilldownFilterDraft, shareGrantLookupId],
  );

  const handleOpenShareAliasDrilldown = useCallback(
    (aliasId?: string) => {
      if (!session) {
        return;
      }
      const resolvedAliasId = (aliasId ?? shareAliasLookupId).trim();
      if (!resolvedAliasId) {
        return;
      }
      const nextFilters = normalizeConversionFilterInput({
        ...shareDrilldownFilterDraft,
        shareKind: null,
      });
      setShareDrilldownFilterDraft(nextFilters);
      setShareDrilldownFilters(nextFilters);
      setShareAliasLookupId(resolvedAliasId);
      void loadShareDrilldown(
        session.client,
        { kind: "alias", id: resolvedAliasId },
        nextFilters,
      );
    },
    [loadShareDrilldown, session, shareAliasLookupId, shareDrilldownFilterDraft],
  );

  const handleApplyShareDrilldownFilters = useCallback(() => {
    if (!session || !shareDrilldownTarget) {
      return;
    }
    const nextFilters = normalizeConversionFilterInput({
      ...shareDrilldownFilterDraft,
      shareKind: null,
    });
    setShareDrilldownFilterDraft(nextFilters);
    setShareDrilldownFilters(nextFilters);
    void loadShareDrilldown(session.client, shareDrilldownTarget, nextFilters);
  }, [loadShareDrilldown, session, shareDrilldownFilterDraft, shareDrilldownTarget]);

  const handleResetShareDrilldownFilters = useCallback(() => {
    applyShareDrilldownContext(
      DEFAULT_CONVERSION_FILTER_INPUT,
      {
        kind: "manual",
        presetId: null,
        presetName: null,
      },
      {
        reloadCurrentTarget: true,
      },
    );
  }, [applyShareDrilldownContext]);

  const handleApplyResultShareRegistryFilters = useCallback(() => {
    if (!session) {
      return;
    }
    const nextFilters = normalizeResultShareRegistryFilterInput(resultShareRegistryFilterDraft);
    const nextSorts = normalizeResultShareRegistrySortInput(resultShareRegistrySortDraft);
    setResultShareRegistryFilterDraft(nextFilters);
    setResultShareRegistryFilters(nextFilters);
    setResultShareRegistrySortDraft(nextSorts);
    setResultShareRegistrySorts(nextSorts);
    void loadResultShareRegistry(session.client, nextFilters);
  }, [loadResultShareRegistry, resultShareRegistryFilterDraft, resultShareRegistrySortDraft, session]);

  const handleResetResultShareRegistryFilters = useCallback(() => {
    if (!session) {
      return;
    }
    setActiveRegistryPreset(null);
    setResultShareRegistryFilterDraft(DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT);
    setResultShareRegistryFilters(DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT);
    setResultShareRegistrySortDraft(DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT);
    setResultShareRegistrySorts(DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT);
    void loadResultShareRegistry(session.client, DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT);
  }, [loadResultShareRegistry, session]);

  const handleFilterAliasesForGrant = useCallback(
    (grantId: string, shareKind: ResultShareGrantRead["share_kind"]) => {
      if (!session) {
        return;
      }
      setActiveRegistryPreset(null);
      const nextFilters = normalizeResultShareRegistryFilterInput({
        ...resultShareRegistryFilterDraft,
        shareKind,
        aliasStatus: null,
        resultShareGrantId: grantId,
      });
      setResultShareRegistryFilterDraft(nextFilters);
      setResultShareRegistryFilters(nextFilters);
      void loadResultShareRegistry(session.client, nextFilters);
    },
    [loadResultShareRegistry, resultShareRegistryFilterDraft, session],
  );

  const handleSaveRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope) => {
      const name = scope === "grant_registry" ? grantSavedViewName : aliasSavedViewName;
      const draft = buildResultShareRegistrySavedViewDraft(
        scope,
        name,
        resultShareRegistryFilterDraft,
        resultShareRegistrySortDraft,
        {
          includeDrilldownContext:
            scope === "grant_registry"
              ? grantSavedViewIncludesDrilldown
              : aliasSavedViewIncludesDrilldown,
          drilldownFilters: shareDrilldownFilterDraft,
        },
      );
      if (!draft) {
        setNoticeMessage("Enter a local preset name before saving the current registry view.");
        return;
      }
      const preset = createResultShareRegistrySavedView(draft);
      commitResultShareRegistrySavedViewStore(
        saveResultShareRegistrySavedView(resultShareRegistrySavedViews, preset),
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_saved",
          "success",
          `Saved local ${scope === "grant_registry" ? "grant" : "alias"} preset ${preset.name}.`,
          {
            scope,
            presetId: preset.id,
            presetName: preset.name,
          },
        ),
      );
      if (scope === "grant_registry") {
        setGrantSavedViewName("");
      } else {
        setAliasSavedViewName("");
      }
      setNoticeMessage(`Saved local ${scope === "grant_registry" ? "grant" : "alias"} registry view.`);
    },
    [
      aliasSavedViewName,
      aliasSavedViewIncludesDrilldown,
      grantSavedViewIncludesDrilldown,
      grantSavedViewName,
      commitResultShareRegistrySavedViewStore,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryFilterDraft,
      resultShareRegistrySortDraft,
      resultShareRegistrySavedViews,
      shareDrilldownFilterDraft,
    ],
  );

  const handleOverwriteRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string) => {
      const existing = findSavedView(scope, presetId);
      if (!existing) {
        return;
      }
      const nextName =
        (scope === "grant_registry" ? grantSavedViewName : aliasSavedViewName).trim() ||
        existing.name;
      const draft = buildResultShareRegistrySavedViewDraft(
        scope,
        nextName,
        resultShareRegistryFilterDraft,
        resultShareRegistrySortDraft,
        {
          includeDrilldownContext:
            scope === "grant_registry"
              ? grantSavedViewIncludesDrilldown
              : aliasSavedViewIncludesDrilldown,
          drilldownFilters: shareDrilldownFilterDraft,
        },
      );
      if (!draft) {
        return;
      }
      commitResultShareRegistrySavedViewStore(
        overwriteResultShareRegistrySavedView(
          resultShareRegistrySavedViews,
          presetId,
          draft,
        ),
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_overwritten",
          "success",
          `Overwrote local preset ${existing.name}.`,
          {
            scope,
            presetId,
            presetName: draft.name,
          },
        ),
      );
      if (scope === "grant_registry") {
        setGrantSavedViewName("");
      } else {
        setAliasSavedViewName("");
      }
      setNoticeMessage(`Overwrote local preset ${existing.name}.`);
    },
    [
      aliasSavedViewName,
      aliasSavedViewIncludesDrilldown,
      commitResultShareRegistrySavedViewStore,
      findSavedView,
      grantSavedViewIncludesDrilldown,
      grantSavedViewName,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryFilterDraft,
      resultShareRegistrySortDraft,
      resultShareRegistrySavedViews,
      shareDrilldownFilterDraft,
    ],
  );

  const handleApplyRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string, mode: ResultShareRegistrySavedViewApplyMode) => {
      const preset = findSavedView(scope, presetId);
      if (!preset) {
        return;
      }
      const applied = applyResultShareRegistrySavedView(
        resultShareRegistryFilterDraft,
        resultShareRegistrySortDraft,
        shareDrilldownFilterDraft,
        preset,
        mode,
      );
      setResultShareRegistryFilterDraft(applied.filters);
      setResultShareRegistryFilters(applied.filters);
      setResultShareRegistrySortDraft(applied.sorts);
      setResultShareRegistrySorts(applied.sorts);
      setActiveRegistryPreset(buildActiveRegistryPresetState(preset, "saved_view"));
      commitResultShareRegistryPresetWorkspaceState(
        setResultShareRegistryPresetWorkspaceLastActive(
          resultShareRegistryPresetWorkspaceState,
          scope,
          preset.id,
        ),
      );
      if (applied.didApplyDrilldownContext) {
        applyShareDrilldownContext(
          applied.drilldownFilters,
          {
            kind: "saved_view",
            presetId: preset.id,
            presetName: preset.name,
          },
          {
            reloadCurrentTarget: true,
          },
        );
      }
      if (session) {
        void loadResultShareRegistry(session.client, applied.filters);
      }
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_applied",
          applied.didApplyDrilldownContext ? "warning" : "success",
          applied.didApplyDrilldownContext
            ? `Applied local preset ${preset.name} with linked drilldown context.`
            : `Applied local preset ${preset.name}.`,
          {
            scope,
            presetId: preset.id,
            presetName: preset.name,
            safeDetails: applied.didApplyDrilldownContext
              ? "registry_and_drilldown"
              : "registry_only",
          },
        ),
      );
      setNoticeMessage(
        applied.didApplyDrilldownContext
          ? `Applied local preset ${preset.name} with linked drilldown filters.`
          : `Applied local preset ${preset.name}.`,
      );
    },
    [
      applyShareDrilldownContext,
      commitResultShareRegistryPresetWorkspaceState,
      findSavedView,
      loadResultShareRegistry,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryFilterDraft,
      resultShareRegistryPresetWorkspaceState,
      resultShareRegistrySortDraft,
      session,
      shareDrilldownFilterDraft,
    ],
  );

  const handleDeleteRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string) => {
      const preset = findSavedView(scope, presetId);
      commitResultShareRegistrySavedViewStore(
        deleteResultShareRegistrySavedView(
          resultShareRegistrySavedViews,
          scope,
          presetId,
        ),
      );
      if (preset) {
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "preset_deleted",
            "success",
            `Deleted local preset ${preset.name}.`,
            {
              scope,
              presetId: preset.id,
              presetName: preset.name,
            },
          ),
        );
        setNoticeMessage(`Deleted local preset ${preset.name}.`);
      }
    },
    [
      commitResultShareRegistrySavedViewStore,
      findSavedView,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistrySavedViews,
    ],
  );

  const handleSetDefaultRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string) => {
      const preset = findSavedView(scope, presetId);
      commitResultShareRegistrySavedViewStore(
        setResultShareRegistryDefaultPresetId(resultShareRegistrySavedViews, presetId),
      );
      setActiveRegistryPreset((current) =>
        current?.presetId === presetId && preset
          ? buildActiveRegistryPresetState(preset, "default_preset")
          : current,
      );
      setShareDrilldownContextSource((current) =>
        current.presetId === presetId && current.kind !== "manual" && preset?.drilldownContext
          ? {
              kind: "default_preset",
              presetId: preset.id,
              presetName: preset.name,
            }
          : current,
      );
      if (preset) {
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "default_set",
            "success",
            `Marked ${preset.name} as the default local registry view.`,
            {
              scope,
              presetId: preset.id,
              presetName: preset.name,
            },
          ),
        );
        setNoticeMessage(`Marked ${preset.name} as the default local registry view.`);
      }
    },
    [
      commitResultShareRegistrySavedViewStore,
      findSavedView,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistrySavedViews,
    ],
  );

  const handleClearDefaultRegistrySavedView = useCallback(() => {
    const clearedPreset = findSavedViewInStore(
      resultShareRegistrySavedViews,
      resultShareRegistrySavedViews.defaultPresetId,
    );
    commitResultShareRegistrySavedViewStore(
      setResultShareRegistryDefaultPresetId(resultShareRegistrySavedViews, null),
    );
    setActiveRegistryPreset((current) =>
      current?.source === "default_preset"
        ? {
            ...current,
            source: "saved_view",
          }
        : current,
    );
    setShareDrilldownContextSource((current) =>
      current.kind === "default_preset"
        ? {
            ...current,
            kind: "saved_view",
          }
        : current,
    );
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "default_cleared",
        "success",
        "Cleared the default local registry view.",
        {
          scope: clearedPreset?.scope ?? null,
          presetId: clearedPreset?.id ?? null,
          presetName: clearedPreset?.name ?? null,
        },
      ),
    );
    setNoticeMessage("Cleared the default local registry view.");
  }, [
    commitResultShareRegistrySavedViewStore,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistrySavedViews,
  ]);

  const handleRestoreDefaultRegistrySavedView = useCallback(() => {
    const defaultPreset = defaultRegistrySavedViewState.defaultPreset;
    if (!defaultPreset) {
      return;
    }
    const applyMode: ResultShareRegistrySavedViewApplyMode = defaultPreset.drilldownContext
      ? "registry_and_drilldown"
      : "registry_only";
    const applied = applyResultShareRegistrySavedView(
      resultShareRegistryFilterDraft,
      resultShareRegistrySortDraft,
      shareDrilldownFilterDraft,
      defaultPreset,
      applyMode,
    );
    setResultShareRegistryFilterDraft(applied.filters);
    setResultShareRegistryFilters(applied.filters);
    setResultShareRegistrySortDraft(applied.sorts);
    setResultShareRegistrySorts(applied.sorts);
    setActiveRegistryPreset(buildActiveRegistryPresetState(defaultPreset, "default_preset"));
    commitResultShareRegistryPresetWorkspaceState(
      setResultShareRegistryPresetWorkspaceLastActive(
        resultShareRegistryPresetWorkspaceState,
        defaultPreset.scope,
        defaultPreset.id,
      ),
    );
    if (applied.didApplyDrilldownContext) {
      applyShareDrilldownContext(
        applied.drilldownFilters,
        {
          kind: "default_preset",
          presetId: defaultPreset.id,
          presetName: defaultPreset.name,
        },
        {
          reloadCurrentTarget: true,
        },
      );
    }
    if (session) {
      void loadResultShareRegistry(session.client, applied.filters);
    }
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_applied",
        applied.didApplyDrilldownContext ? "warning" : "success",
        applied.didApplyDrilldownContext
          ? `Restored default local preset ${defaultPreset.name} with linked drilldown context.`
          : `Restored default local preset ${defaultPreset.name}.`,
        {
          scope: defaultPreset.scope,
          presetId: defaultPreset.id,
          presetName: defaultPreset.name,
          safeDetails: "default_preset",
        },
      ),
    );
    setNoticeMessage(
      applied.didApplyDrilldownContext
        ? `Restored default local registry view ${defaultPreset.name} with linked drilldown filters.`
        : `Restored default local registry view ${defaultPreset.name}.`,
    );
  }, [
    applyShareDrilldownContext,
    commitResultShareRegistryPresetWorkspaceState,
    defaultRegistrySavedViewState.defaultPreset,
    loadResultShareRegistry,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryFilterDraft,
    resultShareRegistryPresetWorkspaceState,
    resultShareRegistrySortDraft,
    session,
    shareDrilldownFilterDraft,
  ]);

  const handlePinRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string) => {
      const preset = findSavedView(scope, presetId);
      if (!preset) {
        return;
      }
      commitResultShareRegistryPresetWorkspaceState(
        pinResultShareRegistryPresetWorkspacePreset(
          resultShareRegistryPresetWorkspaceState,
          scope,
          presetId,
        ),
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_pinned",
          "success",
          `Pinned local preset ${preset.name} in the preset workspace.`,
          {
            scope,
            presetId: preset.id,
            presetName: preset.name,
          },
        ),
      );
      setNoticeMessage(`Pinned local preset ${preset.name}.`);
    },
    [
      commitResultShareRegistryPresetWorkspaceState,
      findSavedView,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryPresetWorkspaceState,
    ],
  );

  const handleUnpinRegistrySavedView = useCallback(
    (scope: ResultShareRegistrySavedViewScope, presetId: string) => {
      const preset = findSavedView(scope, presetId);
      commitResultShareRegistryPresetWorkspaceState(
        unpinResultShareRegistryPresetWorkspacePreset(
          resultShareRegistryPresetWorkspaceState,
          scope,
          presetId,
        ),
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_unpinned",
          "success",
          preset
            ? `Unpinned local preset ${preset.name} from the preset workspace.`
            : "Removed a local preset pin from the preset workspace.",
          {
            scope,
            presetId,
            presetName: preset?.name ?? null,
          },
        ),
      );
      setNoticeMessage(
        preset
          ? `Unpinned local preset ${preset.name}.`
          : "Removed a local preset pin.",
      );
    },
    [
      commitResultShareRegistryPresetWorkspaceState,
      findSavedView,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryPresetWorkspaceState,
    ],
  );

  const handleMovePinnedRegistrySavedView = useCallback(
    (
      scope: ResultShareRegistrySavedViewScope,
      presetId: string,
      direction: "up" | "down",
    ) => {
      commitResultShareRegistryPresetWorkspaceState(
        movePinnedResultShareRegistryPresetWorkspacePreset(
          resultShareRegistryPresetWorkspaceState,
          scope,
          presetId,
          direction,
        ),
      );
    },
    [
      commitResultShareRegistryPresetWorkspaceState,
      resultShareRegistryPresetWorkspaceState,
    ],
  );

  const handleClearAllRegistryPresetWorkspacePins = useCallback(() => {
    if (
      !confirmPresetRecoveryAction(
        "Clear all pinned presets from the local preset workspace? Saved presets will remain available.",
      )
    ) {
      return;
    }
    commitResultShareRegistryPresetWorkspaceState(
      clearAllResultShareRegistryPresetWorkspacePins(
        resultShareRegistryPresetWorkspaceState,
      ),
    );
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_reset",
        "success",
        "Cleared all local preset workspace pins.",
        {
          scope: "storage",
          safeDetails: "clear_all_pins",
        },
      ),
    );
    setNoticeMessage("Cleared all local preset workspace pins.");
  }, [
    commitResultShareRegistryPresetWorkspaceState,
    confirmPresetRecoveryAction,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryPresetWorkspaceState,
  ]);

  const handleResetRegistryPresetWorkspace = useCallback(() => {
    if (
      !confirmPresetRecoveryAction(
        "Reset the local preset workspace organization? Saved presets, imports, backups, and audit history will remain intact.",
      )
    ) {
      return;
    }
    commitResultShareRegistryPresetWorkspaceState(
      resetResultShareRegistryPresetWorkspaceState(),
    );
    setResultShareRegistryPresetWorkspaceStorageWarning(null);
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_reset",
        "success",
        "Reset local preset workspace organization to defaults.",
        {
          scope: "storage",
        },
      ),
    );
    setNoticeMessage("Reset the local preset workspace organization.");
  }, [
    commitResultShareRegistryPresetWorkspaceState,
    confirmPresetRecoveryAction,
    recordResultShareRegistryPresetAuditEvent,
  ]);

  const handleCleanStaleRegistryPresetWorkspacePins = useCallback(() => {
    const cleaned = cleanStaleResultShareRegistryPresetWorkspacePins(
      resultShareRegistryPresetWorkspaceState,
      resultShareRegistrySavedViews,
    );
    commitResultShareRegistryPresetWorkspaceState(cleaned.state);
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "stale_pins_cleaned",
        cleaned.removedGrantPinIds.length + cleaned.removedAliasPinIds.length > 0
          ? "warning"
          : "success",
        cleaned.removedGrantPinIds.length + cleaned.removedAliasPinIds.length > 0
          ? "Cleaned stale preset workspace pins."
          : "Checked preset workspace pins and found no stale entries.",
        {
          scope: "storage",
          safeDetails: `${cleaned.removedGrantPinIds.length} grant, ${cleaned.removedAliasPinIds.length} alias`,
        },
      ),
    );
    setNoticeMessage(
      cleaned.removedGrantPinIds.length + cleaned.removedAliasPinIds.length > 0
        ? "Cleaned stale preset workspace pins."
        : "No stale preset workspace pins were found.",
    );
  }, [
    commitResultShareRegistryPresetWorkspaceState,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryPresetWorkspaceState,
    resultShareRegistrySavedViews,
  ]);

  const handleExportResultShareRegistryPresets = useCallback(() => {
    const payload = buildResultShareRegistryPresetExport(resultShareRegistrySavedViews);
    const content = JSON.stringify(payload, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const safeTimestamp = payload.exportedAt.replace(/[:.]/g, "-");
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `result-share-registry-presets-${safeTimestamp}.json`;
    link.click();
    URL.revokeObjectURL(downloadUrl);
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "export_created",
        "success",
        "Exported local preset JSON.",
        {
          scope: "storage",
          safeDetails: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        },
      ),
    );
    setNoticeMessage(
      `Exported local preset JSON (${RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION}).`,
    );
  }, [
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistrySavedViews,
  ]);

  const handleImportResultShareRegistryPresetFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        setResultShareRegistryPresetImportPreview(null);
        return;
      }
      try {
        const preview = parseResultShareRegistryPresetImport(await readLocalFileText(file));
        setResultShareRegistryPresetImportPreview(preview);
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            preview.canApply ? "import_dry_run" : "validation_failed",
            preview.errors.length > 0 ? "failed" : preview.warnings.length > 0 ? "warning" : "success",
            preview.canApply
              ? `Validated ${preview.validPresetCount} preset(s) for local import dry-run.`
              : "Import dry-run validation found errors.",
            {
              scope: "storage",
              safeDetails: preview.schemaVersion,
            },
          ),
        );
        setNoticeMessage(
          preview.canApply
            ? `Validated ${preview.validPresetCount} preset(s) for local import dry-run preview.`
            : "Import preview found validation errors. Existing local presets were not changed.",
        );
      } catch (error) {
        setResultShareRegistryPresetImportPreview({
          schemaVersion: null,
          validPresetCount: 0,
          invalidPresetCount: 0,
          grantPresetCount: 0,
          aliasPresetCount: 0,
          warnings: [],
          errors: [
            error instanceof Error ? error.message : "Failed to read local preset JSON file.",
          ],
          canApply: false,
          importedScopes: {
            grantRegistry: false,
            aliasRegistry: false,
          },
          presets: {
            grantRegistry: [],
            aliasRegistry: [],
          },
        });
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "validation_failed",
            "failed",
            "Failed to read local preset JSON file for validation-only preview.",
            {
              scope: "storage",
            },
          ),
        );
        setNoticeMessage("Failed to read local preset JSON file.");
      }
    },
    [recordResultShareRegistryPresetAuditEvent],
  );

  const handleApplyResultShareRegistryPresetImport = useCallback(() => {
    if (!resultShareRegistryPresetImportPreview?.canApply) {
      return;
    }
    const backup = createResultShareRegistryPresetBackup(
      resultShareRegistrySavedViews,
      `import_${resultShareRegistryPresetImportMode}`,
    );
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "backup_created",
        "success",
        `Created last-good backup before ${resultShareRegistryPresetImportMode} import.`,
        {
          scope: "storage",
          safeDetails: backup.reason,
        },
      ),
    );
    const importResult = applyResultShareRegistryPresetImport(
      resultShareRegistrySavedViews,
      resultShareRegistryPresetImportPreview,
      resultShareRegistryPresetImportMode,
    );
    commitResultShareRegistrySavedViewStore(importResult.store, {
      backup,
    });
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        resultShareRegistryPresetImportMode === "merge" ? "import_merge" : "import_replace",
        importResult.defaultPresetCleared ? "warning" : "success",
        `Applied local preset ${resultShareRegistryPresetImportMode} import.`,
        {
          scope: "storage",
          safeDetails: importResult.defaultPresetCleared
            ? "default_preset_cleared"
            : null,
        },
      ),
    );
    setResultShareRegistryPresetImportPreview(null);
    setResultShareRegistryPresetImportMode("merge");
    setNoticeMessage(
      [
        `Imported ${importResult.importedGrantCount} grant preset(s) and ${importResult.importedAliasCount} alias preset(s) via ${resultShareRegistryPresetImportMode}.`,
        importResult.defaultPresetCleared
          ? "The default preset marker was cleared because its preset no longer exists."
          : null,
      ]
        .filter(Boolean)
        .join(" "),
    );
  }, [
    resultShareRegistryPresetImportMode,
    resultShareRegistryPresetImportPreview,
    resultShareRegistrySavedViews,
    commitResultShareRegistrySavedViewStore,
    recordResultShareRegistryPresetAuditEvent,
  ]);

  const handleClearResultShareRegistryPresetImportPreview = useCallback(() => {
    setResultShareRegistryPresetImportPreview(null);
    setResultShareRegistryPresetImportMode("merge");
  }, []);

  const handleExportResultShareRegistryPresetWorkspace = useCallback(() => {
    const payload = buildResultShareRegistryPresetWorkspaceExport(
      resultShareRegistryPresetWorkspaceState,
    );
    const content = JSON.stringify(payload, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const safeTimestamp = payload.exportedAt.replace(/[:.]/g, "-");
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `result-share-registry-preset-workspace-${safeTimestamp}.json`;
    link.click();
    URL.revokeObjectURL(downloadUrl);
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_export_created",
        "success",
        "Exported local preset workspace organization JSON.",
        {
          scope: "storage",
          safeDetails: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
        },
      ),
    );
    setNoticeMessage(
      `Exported local preset workspace organization JSON (${RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION}).`,
    );
  }, [
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryPresetWorkspaceState,
  ]);

  const handleImportResultShareRegistryPresetWorkspaceFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        setResultShareRegistryPresetWorkspaceImportPreview(null);
        return;
      }
      try {
        const preview = parseResultShareRegistryPresetWorkspaceImport(
          await readLocalFileText(file),
          resultShareRegistrySavedViews,
        );
        setResultShareRegistryPresetWorkspaceImportPreview(preview);
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            preview.canApply
              ? "preset_workspace_import_dry_run"
              : "preset_workspace_import_validation_failed",
            preview.errors.length > 0
              ? "failed"
              : preview.warnings.length > 0
                ? "warning"
                : "success",
            preview.canApply
              ? "Validated local preset workspace import in dry-run mode."
              : "Preset workspace import validation found errors.",
            {
              scope: "storage",
              safeDetails: preview.schemaVersion,
            },
          ),
        );
        setNoticeMessage(
          preview.canApply
            ? "Validated local preset workspace organization import in dry-run mode."
            : "Workspace import preview found validation errors. Existing local workspace state was not changed.",
        );
      } catch (error) {
        setResultShareRegistryPresetWorkspaceImportPreview({
          schemaVersion: null,
          valid: false,
          canApply: false,
          warnings: [],
          errors: [
            error instanceof Error
              ? error.message
              : "Failed to read local preset workspace JSON file.",
          ],
          pinnedGrantPresetCount: 0,
          pinnedAliasPresetCount: 0,
          stalePinnedGrantPresetIds: [],
          stalePinnedAliasPresetIds: [],
          lastActivePresetExists: false,
          workspaceState: null,
        });
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "preset_workspace_import_validation_failed",
            "failed",
            "Failed to read local preset workspace JSON file for validation-only preview.",
            {
              scope: "storage",
            },
          ),
        );
        setNoticeMessage("Failed to read local preset workspace JSON file.");
      }
    },
    [recordResultShareRegistryPresetAuditEvent, resultShareRegistrySavedViews],
  );

  const handleApplyResultShareRegistryPresetWorkspaceImport = useCallback(() => {
    if (!resultShareRegistryPresetWorkspaceImportPreview?.canApply) {
      return;
    }
    const backup = createResultShareRegistryPresetWorkspaceBackup(
      resultShareRegistryPresetWorkspaceState,
      `workspace_import_${resultShareRegistryPresetWorkspaceImportMode}`,
    );
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_backup_created",
        "success",
        `Created workspace backup before ${resultShareRegistryPresetWorkspaceImportMode} import.`,
        {
          scope: "storage",
          safeDetails: backup.reason,
        },
      ),
    );
    const importResult = applyResultShareRegistryPresetWorkspaceImport(
      resultShareRegistryPresetWorkspaceState,
      resultShareRegistryPresetWorkspaceImportPreview,
      resultShareRegistryPresetWorkspaceImportMode,
      resultShareRegistrySavedViews,
    );
    commitResultShareRegistryPresetWorkspaceState(importResult.workspaceState, {
      backup,
    });
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        resultShareRegistryPresetWorkspaceImportMode === "merge"
          ? "preset_workspace_import_merge"
          : "preset_workspace_import_replace",
        importResult.lastActivePresetCleared ||
          importResult.stalePinnedGrantPresetIds.length > 0 ||
          importResult.stalePinnedAliasPresetIds.length > 0
          ? "warning"
          : "success",
        `Applied local preset workspace ${resultShareRegistryPresetWorkspaceImportMode} import.`,
        {
          scope: "storage",
          safeDetails: [
            importResult.lastActivePresetCleared ? "last_active_cleared" : null,
            importResult.stalePinnedGrantPresetIds.length > 0
              ? `stale_grant_pins:${importResult.stalePinnedGrantPresetIds.length}`
              : null,
            importResult.stalePinnedAliasPresetIds.length > 0
              ? `stale_alias_pins:${importResult.stalePinnedAliasPresetIds.length}`
              : null,
          ]
            .filter(Boolean)
            .join(", ") || null,
        },
      ),
    );
    setResultShareRegistryPresetWorkspaceImportPreview(null);
    setResultShareRegistryPresetWorkspaceImportMode("merge");
    setNoticeMessage(
      [
        `Applied local preset workspace ${resultShareRegistryPresetWorkspaceImportMode} import.`,
        importResult.lastActivePresetCleared
          ? "The imported last-active preset marker was cleared because it does not exist locally."
          : null,
        importResult.stalePinnedGrantPresetIds.length > 0 ||
        importResult.stalePinnedAliasPresetIds.length > 0
          ? "Imported workspace state includes stale pins. Use the existing stale-pin cleanup action if you want to remove them."
          : null,
      ]
        .filter(Boolean)
        .join(" "),
    );
  }, [
    commitResultShareRegistryPresetWorkspaceState,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryPresetWorkspaceImportMode,
    resultShareRegistryPresetWorkspaceImportPreview,
    resultShareRegistryPresetWorkspaceState,
    resultShareRegistrySavedViews,
  ]);

  const handleClearResultShareRegistryPresetWorkspaceImportPreview = useCallback(() => {
    setResultShareRegistryPresetWorkspaceImportPreview(null);
    setResultShareRegistryPresetWorkspaceImportMode("merge");
  }, []);

  const handleRestoreResultShareRegistryPresetWorkspaceBackup = useCallback(() => {
    if (!resultShareRegistryPresetWorkspaceLastGoodBackup) {
      return;
    }
    if (
      !confirmPresetRecoveryAction(
        "Restore the last-good local preset workspace backup? This only changes browser-local workspace organization state and does not change saved preset definitions.",
      )
    ) {
      return;
    }
    const restoredState = restoreResultShareRegistryPresetWorkspaceBackup(
      resultShareRegistryPresetWorkspaceLastGoodBackup,
    );
    if (!restoredState) {
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "preset_workspace_import_validation_failed",
          "failed",
          "Failed to validate the stored preset workspace backup before restore.",
          {
            scope: "storage",
          },
        ),
      );
      setNoticeMessage("Stored preset workspace backup could not be restored.");
      return;
    }
    commitResultShareRegistryPresetWorkspaceState(restoredState);
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "preset_workspace_backup_restored",
        "success",
        "Restored the last-good local preset workspace backup.",
        {
          scope: "storage",
          safeDetails: resultShareRegistryPresetWorkspaceLastGoodBackup.reason,
        },
      ),
    );
    setNoticeMessage("Restored the last-good local preset workspace backup.");
  }, [
    commitResultShareRegistryPresetWorkspaceState,
    confirmPresetRecoveryAction,
    recordResultShareRegistryPresetAuditEvent,
    resultShareRegistryPresetWorkspaceLastGoodBackup,
  ]);

  const handleValidateResultShareRegistryPresetStorage = useCallback(() => {
    const inspection = refreshResultShareRegistryPresetDiagnostics();
    recordResultShareRegistryPresetAuditEvent(
      createPresetAuditEvent(
        "integrity_checked",
        inspection.report.errorCount > 0
          ? "failed"
          : inspection.report.warningCount > 0
            ? "warning"
            : "success",
        inspection.report.errorCount > 0 || inspection.report.warningCount > 0
          ? "Local preset integrity check found issues."
          : "Local preset integrity check passed.",
        {
          scope: "storage",
          safeDetails: `${inspection.report.errorCount}e/${inspection.report.warningCount}w`,
        },
      ),
    );
    setNoticeMessage(
      inspection.report.errorCount > 0 || inspection.report.warningCount > 0
        ? `Preset integrity check found ${inspection.report.errorCount} error(s) and ${inspection.report.warningCount} warning(s).`
        : "Preset integrity check passed for current local storage.",
    );
  }, [
    recordResultShareRegistryPresetAuditEvent,
    refreshResultShareRegistryPresetDiagnostics,
  ]);

  const handleRunResultShareRegistryPresetRecoveryAction = useCallback(
    (action: ResultShareRegistryPresetRecoveryAction) => {
      const messages: Record<ResultShareRegistryPresetRecoveryAction, string> = {
        discard_invalid_grant_presets:
          "Discard invalid grant presets from local storage? This only affects browser-local preset data.",
        discard_invalid_alias_presets:
          "Discard invalid alias presets from local storage? This only affects browser-local preset data.",
        clear_dangling_default_preset:
          "Clear the dangling default preset marker from local storage?",
        reset_grant_scope:
          "Reset all grant registry presets in local storage?",
        reset_alias_scope:
          "Reset all alias registry presets in local storage?",
        reset_all_presets:
          "Reset all share registry presets in local storage?",
        restore_last_good_backup:
          "Restore the last-good local backup snapshot for share registry presets?",
      };
      if (!confirmPresetRecoveryAction(messages[action])) {
        return;
      }

      if (action === "restore_last_good_backup") {
        if (!resultShareRegistryPresetLastGoodBackup) {
          recordResultShareRegistryPresetAuditEvent(
            createPresetAuditEvent(
              "recovery_failed",
              "failed",
              "Restore last-good backup was requested, but no backup was available.",
              {
                scope: "storage",
              },
            ),
          );
        }
        const restored = mutateResultShareRegistryPresetStorage(
          (safeStorage) => {
            if (!resultShareRegistryPresetLastGoodBackup) {
              return;
            }
            persistResultShareRegistrySavedViewStore(safeStorage, {
              grantPresets: resultShareRegistryPresetLastGoodBackup.grantRegistry,
              aliasPresets: resultShareRegistryPresetLastGoodBackup.aliasRegistry,
              defaultPresetId: resultShareRegistryPresetLastGoodBackup.defaultPresetId,
            });
          },
          {
            fallbackStore: resultShareRegistryPresetLastGoodBackup
              ? {
                  grantPresets: resultShareRegistryPresetLastGoodBackup.grantRegistry,
                  aliasPresets: resultShareRegistryPresetLastGoodBackup.aliasRegistry,
                  defaultPresetId: resultShareRegistryPresetLastGoodBackup.defaultPresetId,
                }
              : resultShareRegistrySavedViews,
          },
        );
        if (restored.lastGoodBackup) {
          recordResultShareRegistryPresetAuditEvent(
            createPresetAuditEvent(
              "backup_restored",
              "success",
              "Restored the last-good local preset backup.",
              {
                scope: "storage",
                safeDetails: restored.lastGoodBackup.createdAt,
              },
            ),
          );
        }
        setNoticeMessage(
          restored.lastGoodBackup
            ? "Restored the last-good local preset backup."
            : "No restorable local backup snapshot was available.",
        );
        return;
      }

      if (action === "discard_invalid_grant_presets") {
        mutateResultShareRegistryPresetStorage(
          (safeStorage) => {
            safeStorage.setItem(
              RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
              JSON.stringify(resultShareRegistrySavedViews.grantPresets),
            );
          },
          {
            backupReason: action,
          },
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "backup_created",
            "success",
            "Created last-good backup before discarding invalid grant presets.",
            {
              scope: "storage",
              safeDetails: action,
            },
          ),
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "invalid_presets_discarded",
            "warning",
            "Discarded invalid grant presets from local storage.",
            {
              scope: "grant_registry",
            },
          ),
        );
        setNoticeMessage("Discarded invalid local grant presets and refreshed diagnostics.");
        return;
      }

      if (action === "discard_invalid_alias_presets") {
        mutateResultShareRegistryPresetStorage(
          (safeStorage) => {
            safeStorage.setItem(
              RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
              JSON.stringify(resultShareRegistrySavedViews.aliasPresets),
            );
          },
          {
            backupReason: action,
          },
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "backup_created",
            "success",
            "Created last-good backup before discarding invalid alias presets.",
            {
              scope: "storage",
              safeDetails: action,
            },
          ),
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "invalid_presets_discarded",
            "warning",
            "Discarded invalid alias presets from local storage.",
            {
              scope: "alias_registry",
            },
          ),
        );
        setNoticeMessage("Discarded invalid local alias presets and refreshed diagnostics.");
        return;
      }

      if (action === "clear_dangling_default_preset") {
        mutateResultShareRegistryPresetStorage((safeStorage) => {
          safeStorage.removeItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY);
        });
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "dangling_default_cleared",
            "warning",
            "Cleared a dangling default preset marker.",
            {
              scope: "storage",
            },
          ),
        );
        setNoticeMessage("Cleared the dangling default preset marker.");
        return;
      }

      if (action === "reset_grant_scope") {
        mutateResultShareRegistryPresetStorage(
          (safeStorage) => {
            safeStorage.setItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY, JSON.stringify([]));
            if (
              resultShareRegistrySavedViews.defaultPresetId &&
              resultShareRegistrySavedViews.grantPresets.some(
                (preset) => preset.id === resultShareRegistrySavedViews.defaultPresetId,
              )
            ) {
              safeStorage.removeItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY);
            }
          },
          {
            backupReason: action,
            fallbackStore: {
              ...resultShareRegistrySavedViews,
              grantPresets: [],
              defaultPresetId:
                resultShareRegistrySavedViews.defaultPresetId &&
                resultShareRegistrySavedViews.grantPresets.some(
                  (preset) => preset.id === resultShareRegistrySavedViews.defaultPresetId,
                )
                  ? null
                  : resultShareRegistrySavedViews.defaultPresetId,
            },
          },
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "backup_created",
            "success",
            "Created last-good backup before resetting grant preset scope.",
            {
              scope: "storage",
              safeDetails: action,
            },
          ),
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "scope_reset",
            "warning",
            "Reset local grant preset scope.",
            {
              scope: "grant_registry",
            },
          ),
        );
        setNoticeMessage("Reset local grant preset storage and refreshed diagnostics.");
        return;
      }

      if (action === "reset_alias_scope") {
        mutateResultShareRegistryPresetStorage(
          (safeStorage) => {
            safeStorage.setItem(RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY, JSON.stringify([]));
            if (
              resultShareRegistrySavedViews.defaultPresetId &&
              resultShareRegistrySavedViews.aliasPresets.some(
                (preset) => preset.id === resultShareRegistrySavedViews.defaultPresetId,
              )
            ) {
              safeStorage.removeItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY);
            }
          },
          {
            backupReason: action,
            fallbackStore: {
              ...resultShareRegistrySavedViews,
              aliasPresets: [],
              defaultPresetId:
                resultShareRegistrySavedViews.defaultPresetId &&
                resultShareRegistrySavedViews.aliasPresets.some(
                  (preset) => preset.id === resultShareRegistrySavedViews.defaultPresetId,
                )
                  ? null
                  : resultShareRegistrySavedViews.defaultPresetId,
            },
          },
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "backup_created",
            "success",
            "Created last-good backup before resetting alias preset scope.",
            {
              scope: "storage",
              safeDetails: action,
            },
          ),
        );
        recordResultShareRegistryPresetAuditEvent(
          createPresetAuditEvent(
            "scope_reset",
            "warning",
            "Reset local alias preset scope.",
            {
              scope: "alias_registry",
            },
          ),
        );
        setNoticeMessage("Reset local alias preset storage and refreshed diagnostics.");
        return;
      }

      mutateResultShareRegistryPresetStorage(
        (safeStorage) => {
          safeStorage.removeItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY);
          safeStorage.removeItem(RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY);
          safeStorage.removeItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY);
        },
        {
          backupReason: action,
          fallbackStore: {
            grantPresets: [],
            aliasPresets: [],
            defaultPresetId: null,
          },
        },
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "backup_created",
          "success",
          "Created last-good backup before resetting all registry presets.",
          {
            scope: "storage",
            safeDetails: action,
          },
        ),
      );
      recordResultShareRegistryPresetAuditEvent(
        createPresetAuditEvent(
          "all_presets_reset",
          "warning",
          "Reset all local share registry presets.",
          {
            scope: "storage",
          },
        ),
      );
      setNoticeMessage("Reset all local share registry presets and refreshed diagnostics.");
    },
    [
      confirmPresetRecoveryAction,
      mutateResultShareRegistryPresetStorage,
      recordResultShareRegistryPresetAuditEvent,
      resultShareRegistryPresetLastGoodBackup,
      resultShareRegistrySavedViews,
    ],
  );

  const handleClearResultShareRegistryPresetLocalAudit = useCallback(() => {
    if (
      !confirmPresetRecoveryAction(
        "Clear local preset activity history from this browser?",
      )
    ) {
      return;
    }
    clearResultShareRegistryPresetLocalAudit();
    setNoticeMessage("Cleared local preset activity history.");
  }, [clearResultShareRegistryPresetLocalAudit, confirmPresetRecoveryAction]);

  const handleClearShareDrilldown = useCallback(() => {
    setShareDrilldownTarget(null);
    setShareGrantDrilldown(null);
    setShareAliasDrilldown(null);
    setShareDrilldownError(null);
  }, []);

  const handleCreateWorkspace = useCallback(() => {
    if (!session) {
      return;
    }
    void runAction("Creating workspace...", async () => {
      const created = await session.client.createWorkspace(createInput);
      const latest = (await refreshWorkspaces()) ?? [];
      setCreateInput({ slug: "", name: "", description: "" });
      setNoticeMessage(`Created workspace ${created.name}.`);
      const selected = latest.find((workspace) => workspace.id === created.id)?.id ?? created.id;
      await loadWorkspaceContext(session.client, selected, workspaceConversionFilters);
    });
  }, [
    createInput,
    loadWorkspaceContext,
    refreshWorkspaces,
    runAction,
    session,
    workspaceConversionFilters,
  ]);

  const handleSaveWorkspace = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    void runAction("Saving workspace...", async () => {
      await session.client.updateWorkspace(selectedWorkspaceId, {
        name: updateInput.name,
        description: updateInput.description,
        status: updateInput.status,
      });
      await refreshWorkspaces();
      await refreshWorkspaceContext();
      setNoticeMessage("Saved workspace summary.");
    });
  }, [refreshWorkspaceContext, refreshWorkspaces, runAction, selectedWorkspaceId, session, updateInput]);

  const handleAddMember = useCallback(() => {
    if (!session || !selectedWorkspaceId || !memberInput.user_id) {
      return;
    }
    void runAction("Adding workspace member...", async () => {
      await session.client.addWorkspaceMember(selectedWorkspaceId, memberInput);
      setMemberInput({ user_id: "", role: "viewer" });
      await refreshWorkspaceContext();
      setNoticeMessage("Added workspace member.");
    });
  }, [memberInput, refreshWorkspaceContext, runAction, selectedWorkspaceId, session]);

  const handleRemoveMember = useCallback(
    (memberId: string) => {
      if (!session || !selectedWorkspaceId) {
        return;
      }
      void runAction("Removing workspace member...", async () => {
        await session.client.removeWorkspaceMember(selectedWorkspaceId, memberId);
        await refreshWorkspaceContext();
        setNoticeMessage("Removed workspace member.");
      });
    },
    [refreshWorkspaceContext, runAction, selectedWorkspaceId, session],
  );

  const handleAddPaper = useCallback(() => {
    if (!session || !selectedWorkspaceId || !paperInput.paper_id) {
      return;
    }
    void runAction("Adding workspace paper...", async () => {
      await session.client.addWorkspacePaper(selectedWorkspaceId, paperInput);
      setPaperInput({ paper_id: "" });
      await refreshWorkspaceContext();
      setNoticeMessage("Added paper to workspace.");
    });
  }, [paperInput, refreshWorkspaceContext, runAction, selectedWorkspaceId, session]);

  const handleRemovePaper = useCallback(
    (paperId: string) => {
      if (!session || !selectedWorkspaceId) {
        return;
      }
      void runAction("Removing workspace paper...", async () => {
        await session.client.removeWorkspacePaper(selectedWorkspaceId, paperId);
        await refreshWorkspaceContext();
        setNoticeMessage("Removed paper from workspace.");
      });
    },
    [refreshWorkspaceContext, runAction, selectedWorkspaceId, session],
  );

  const handleCreateShareGrant = useCallback(() => {
    if (!session || !selectedWorkspaceId) {
      return;
    }
    void runAction("Issuing workspace_board share grant...", async () => {
      const issued = await session.client.createWorkspaceBoardShareGrant(selectedWorkspaceId, {
        display_label: shareInput.display_label.trim(),
        expires_at: shareInput.expires_at ? new Date(shareInput.expires_at).toISOString() : null,
      });
      setOneTimeGrant(buildShareGrantIssueViewModel(issued));
      setShareInput({ display_label: "", expires_at: null });
      await refreshWorkspaceContext();
      await loadResultShareRegistry(session.client, resultShareRegistryFilters);
      setNoticeMessage("Issued workspace_board share grant.");
    });
  }, [
    loadResultShareRegistry,
    refreshWorkspaceContext,
    resultShareRegistryFilters,
    runAction,
    selectedWorkspaceId,
    session,
    shareInput,
  ]);

  const handleRevokeShareGrant = useCallback(
    (grantId: string) => {
      if (!session) {
        return;
      }
      void runAction("Revoking share grant...", async () => {
        await session.client.revokeResultShareGrant(grantId);
        await refreshWorkspaceContext();
        await loadResultShareRegistry(session.client, resultShareRegistryFilters);
        setNoticeMessage("Revoked workspace_board share grant.");
      });
    },
    [loadResultShareRegistry, refreshWorkspaceContext, resultShareRegistryFilters, runAction, session],
  );

  if (!session) {
    return (
      <TokenEntryView
        apiBaseUrl={apiBaseUrlInput}
        adminToken={adminTokenInput}
        loading={loadingMessage !== null}
        errorTitle={connectError?.title ?? null}
        errorMessage={connectError?.message ?? null}
        noticeMessage={noticeMessage}
        onApiBaseUrlChange={setApiBaseUrlInput}
        onAdminTokenChange={setAdminTokenInput}
        onSubmit={handleOpenShell}
      />
    );
  }

  return (
    <main className="admin-shell-root">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Internal Workspace Admin</p>
          <h1>Group workspaces and workspace-board shares</h1>
          <p className="lede">
            This internal shell manages structured group workspaces only. It does not expose
            source files, local attachments, or local note contents.
          </p>
        </div>
        <div className="hero-actions">
          <div className="hero-chip">
            <span>API base</span>
            <strong>{session.apiBaseUrl}</strong>
          </div>
          <div className="hero-chip">
            <span>Workspaces</span>
            <strong>{workspaces.length}</strong>
          </div>
          <button type="button" className="button-secondary" onClick={handleDisconnect}>
            Disconnect
          </button>
        </div>
      </section>

      {noticeMessage ? <div className="inline-banner info">{noticeMessage}</div> : null}
      {actionError ? (
        <div className="inline-banner error" role="alert">
          <strong>{actionError.title}</strong>
          <span>{actionError.message}</span>
        </div>
      ) : null}
      {loadingMessage ? <div className="inline-banner info">{loadingMessage}</div> : null}

      <ConversionFilterBar
        eyebrow="Global filters"
        title="Global conversion filters"
        description="Read-only time-window and dimension filters for the global overview and drilldown panels. Recent-row limit applies to drilldown sections only."
        filters={globalConversionFilterDraft}
        support={GLOBAL_CONVERSION_FILTER_SUPPORT}
        summary={globalConversionFilterSummary}
        disabled={globalConversionLoading || globalConversionDrilldownLoading}
        onChange={patchGlobalFilterDraft}
        onApply={handleApplyGlobalFilters}
        onReset={handleResetGlobalFilters}
      />

      <ConversionOverviewPanel
        eyebrow="Conversion dashboard"
        title="Global conversion overview"
        description="Read-only aggregate signals across public share views, handoff redirects, invite claims, and result collect records."
        summaryMetrics={globalConversionViewModel?.summaryMetrics ?? []}
        sections={globalConversionViewModel?.sections ?? []}
        attributionScope={globalConversionViewModel?.attributionScope ?? null}
        windowStart={globalConversionViewModel?.windowStart ?? null}
        windowEnd={globalConversionViewModel?.windowEnd ?? null}
        lastActivityAt={globalConversionViewModel?.lastActivityAt ?? null}
        loading={globalConversionLoading}
        error={globalConversionError}
        empty={globalConversionViewModel?.empty ?? !globalConversionLoading}
        emptyMessage="No share, invite, or collect activity has been recorded in this analytics window."
      />

      <ConversionDrilldownPanel
        eyebrow="Conversion drilldown"
        title="Global conversion drilldown"
        description="Read-only daily buckets, recent activity, top workspaces, and top result-share grants across the existing admin-safe drilldown reserve."
        summaryMetrics={globalConversionDrilldownViewModel?.summaryMetrics ?? []}
        windowStart={globalConversionDrilldownViewModel?.windowStart ?? null}
        windowEnd={globalConversionDrilldownViewModel?.windowEnd ?? null}
        lastActivityAt={globalConversionDrilldownViewModel?.lastActivityAt ?? null}
        dailyBuckets={globalConversionDrilldownViewModel?.dailyBuckets ?? []}
        topWorkspaces={globalConversionDrilldownViewModel?.topWorkspaces ?? []}
        topResultShareGrants={globalConversionDrilldownViewModel?.topResultShareGrants ?? []}
        recentShareEvents={globalConversionDrilldownViewModel?.recentShareEvents ?? []}
        recentInviteClaims={globalConversionDrilldownViewModel?.recentInviteClaims ?? []}
        recentCollectRecords={globalConversionDrilldownViewModel?.recentCollectRecords ?? []}
        attributionScope={globalConversionDrilldownViewModel?.attributionScope ?? null}
        notes={globalConversionDrilldownViewModel?.notes ?? []}
        loading={globalConversionDrilldownLoading}
        error={globalConversionDrilldownError}
        empty={globalConversionDrilldownViewModel?.empty ?? !globalConversionDrilldownLoading}
        emptyMessage="No global drilldown activity has been recorded in this analytics window."
      />

      <ResultShareRegistryPanel
        filters={resultShareRegistryFilterDraft}
        sorts={resultShareRegistrySortDraft}
        filterSummary={resultShareRegistryFilterSummary}
        presetTransfer={{
          importMode: resultShareRegistryPresetImportMode,
          preview: resultShareRegistryPresetImportPreview,
        }}
        presetSafety={{
          integrityReport: resultShareRegistryPresetIntegrityReport,
          diagnostics: resultShareRegistryPresetStorageDiagnostics,
          lastGoodBackup: resultShareRegistryPresetLastGoodBackup,
        }}
        presetAudit={{
          summary: resultShareRegistryPresetLocalAuditSummary,
        }}
        savedViewDrafts={{
          grantName: grantSavedViewName,
          aliasName: aliasSavedViewName,
          grantIncludeDrilldown: grantSavedViewIncludesDrilldown,
          aliasIncludeDrilldown: aliasSavedViewIncludesDrilldown,
        }}
        savedViews={resultShareRegistrySavedViewSummaries}
        presetWorkspace={{
          viewModel: resultShareRegistryPresetWorkspaceViewModel,
          healthScore: resultShareRegistryPresetWorkspaceHealthScore,
          transfer: {
            importMode: resultShareRegistryPresetWorkspaceImportMode,
            preview: resultShareRegistryPresetWorkspaceImportPreview,
            lastGoodBackup: resultShareRegistryPresetWorkspaceLastGoodBackup,
          },
        }}
        activePresetLabel={activeRegistryPresetLabel}
        activeDrilldownContextLabel={shareDrilldownContextLabel}
        registry={
          resultShareRegistryLoading &&
          resultShareGrants.length === 0 &&
          resultShareAliases.length === 0
            ? null
            : resultShareRegistryViewModel
        }
        currentTargetLabel={shareDrilldownCurrentTargetLabel}
        loading={resultShareRegistryLoading}
        error={resultShareRegistryError}
        onFilterChange={patchResultShareRegistryFilterDraft}
        onSortChange={patchResultShareRegistrySortDraft}
        onSavedViewDraftChange={(scope, name) => {
          if (scope === "grant_registry") {
            setGrantSavedViewName(name);
          } else {
            setAliasSavedViewName(name);
          }
        }}
        onSavedViewIncludeDrilldownChange={(scope, include) => {
          if (scope === "grant_registry") {
            setGrantSavedViewIncludesDrilldown(include);
          } else {
            setAliasSavedViewIncludesDrilldown(include);
          }
        }}
        onApplyFilters={handleApplyResultShareRegistryFilters}
        onResetFilters={handleResetResultShareRegistryFilters}
        onSaveSavedView={handleSaveRegistrySavedView}
        onApplySavedView={handleApplyRegistrySavedView}
        onOverwriteSavedView={handleOverwriteRegistrySavedView}
        onDeleteSavedView={handleDeleteRegistrySavedView}
        onSetDefaultSavedView={handleSetDefaultRegistrySavedView}
        onClearDefaultSavedView={handleClearDefaultRegistrySavedView}
        onRestoreDefaultSavedView={handleRestoreDefaultRegistrySavedView}
        onResetDrilldownContext={handleResetShareDrilldownFilters}
        onPresetImportModeChange={setResultShareRegistryPresetImportMode}
        onImportPresetFile={handleImportResultShareRegistryPresetFile}
        onApplyPresetImport={handleApplyResultShareRegistryPresetImport}
        onClearPresetImportPreview={handleClearResultShareRegistryPresetImportPreview}
        onExportPresets={handleExportResultShareRegistryPresets}
        onValidatePresetStorage={handleValidateResultShareRegistryPresetStorage}
        onRunPresetRecoveryAction={handleRunResultShareRegistryPresetRecoveryAction}
        onClearPresetAudit={handleClearResultShareRegistryPresetLocalAudit}
        onPresetWorkspaceImportModeChange={setResultShareRegistryPresetWorkspaceImportMode}
        onImportPresetWorkspaceFile={handleImportResultShareRegistryPresetWorkspaceFile}
        onApplyPresetWorkspaceImport={handleApplyResultShareRegistryPresetWorkspaceImport}
        onClearPresetWorkspaceImportPreview={handleClearResultShareRegistryPresetWorkspaceImportPreview}
        onExportPresetWorkspace={handleExportResultShareRegistryPresetWorkspace}
        onRestorePresetWorkspaceBackup={handleRestoreResultShareRegistryPresetWorkspaceBackup}
        onRecalculatePresetWorkspaceHealth={handleRecalculateResultShareRegistryPresetWorkspaceHealth}
        onPinSavedView={handlePinRegistrySavedView}
        onUnpinSavedView={handleUnpinRegistrySavedView}
        onMovePinnedSavedView={handleMovePinnedRegistrySavedView}
        onClearWorkspacePins={handleClearAllRegistryPresetWorkspacePins}
        onResetWorkspace={handleResetRegistryPresetWorkspace}
        onCleanStaleWorkspacePins={handleCleanStaleRegistryPresetWorkspacePins}
        onOpenGrantDrilldown={handleOpenShareGrantDrilldown}
        onOpenAliasDrilldown={handleOpenShareAliasDrilldown}
        onFilterAliasesForGrant={handleFilterAliasesForGrant}
      />

      <section className="admin-shell-grid">
        <WorkspaceListPanel
          items={workspaceListItems}
          selectedWorkspaceId={selectedWorkspaceId}
          createInput={createInput}
          loading={loadingMessage !== null}
          onSelect={(workspaceId) => {
            if (!session) {
              return;
            }
            void loadWorkspaceContext(session.client, workspaceId, workspaceConversionFilters);
          }}
          onCreateInputChange={(patch) =>
            setCreateInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onCreate={handleCreateWorkspace}
        />

        <WorkspaceDetailView
          workspace={selectedWorkspace}
          board={boardViewModel}
          updateInput={updateInput}
          memberInput={memberInput}
          paperInput={paperInput}
          shareInput={shareInput}
          userOptions={availableUserOptions}
          paperOptions={availablePaperOptions}
          shareGrants={selectedShareGrants}
          conversionFilters={workspaceConversionFilterDraft}
          conversionFilterSummary={workspaceConversionFilterSummary}
          shareDrilldownGrantLookupId={shareGrantLookupId}
          shareDrilldownAliasLookupId={shareAliasLookupId}
          shareDrilldownCurrentTargetLabel={shareDrilldownCurrentTargetLabel}
          shareDrilldownContextLabel={shareDrilldownContextLabel}
          shareDrilldownFilters={shareDrilldownFilterDraft}
          shareDrilldownFilterSummary={shareDrilldownFilterSummary}
          shareDrilldownFilterSupport={PER_SHARE_DRILLDOWN_FILTER_SUPPORT}
          shareDrilldownFilterDisabled={shareDrilldownLoading}
          conversionFilterDisabled={
            workspaceConversionLoading || workspaceConversionDrilldownLoading
          }
          conversionOverview={workspaceConversionViewModel}
          conversionError={workspaceConversionError}
          conversionLoading={workspaceConversionLoading}
          conversionDrilldown={workspaceConversionDrilldownViewModel}
          conversionDrilldownError={workspaceConversionDrilldownError}
          conversionDrilldownLoading={workspaceConversionDrilldownLoading}
          shareGrantDrilldown={shareDrilldownGrantViewModel}
          shareAliasDrilldown={shareDrilldownAliasViewModel}
          shareDrilldownError={shareDrilldownError}
          shareDrilldownLoading={shareDrilldownLoading}
          actionLoading={loadingMessage !== null}
          onConversionFilterChange={patchWorkspaceFilterDraft}
          onApplyConversionFilters={handleApplyWorkspaceFilters}
          onResetConversionFilters={handleResetWorkspaceFilters}
          onShareDrilldownGrantLookupIdChange={setShareGrantLookupId}
          onShareDrilldownAliasLookupIdChange={setShareAliasLookupId}
          onShareDrilldownFilterChange={patchShareDrilldownFilterDraft}
          onApplyShareDrilldownFilters={handleApplyShareDrilldownFilters}
          onResetShareDrilldownFilters={handleResetShareDrilldownFilters}
          oneTimeGrant={oneTimeGrant}
          onUpdateInputChange={(patch) =>
            setUpdateInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onMemberInputChange={(patch) =>
            setMemberInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onPaperInputChange={(patch) =>
            setPaperInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onShareInputChange={(patch) =>
            setShareInput((current) => ({
              ...current,
              ...patch,
            }))
          }
          onOpenShareGrantDrilldown={handleOpenShareGrantDrilldown}
          onOpenShareAliasDrilldown={handleOpenShareAliasDrilldown}
          onClearShareDrilldown={handleClearShareDrilldown}
          onSaveWorkspace={handleSaveWorkspace}
          onAddMember={handleAddMember}
          onRemoveMember={handleRemoveMember}
          onAddPaper={handleAddPaper}
          onRemovePaper={handleRemovePaper}
          onCreateShareGrant={handleCreateShareGrant}
          onRevokeShareGrant={handleRevokeShareGrant}
          onDismissOneTimeGrant={() => setOneTimeGrant(null)}
        />
      </section>
    </main>
  );
}

export default App;
