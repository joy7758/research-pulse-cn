import { DEFAULT_CONVERSION_FILTER_INPUT } from "./conversionFilters";
import {
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
} from "./resultShareRegistryFilters";
import {
  applyResultShareRegistryPresetRecoveryAction,
  applyResultShareRegistryPresetImport,
  applyResultShareRegistrySavedView,
  appendResultShareRegistryPresetAuditEvent,
  buildPresetWorkspaceHealthThresholdPreview,
  buildResultShareRegistryPresetAuditSummary,
  buildResultShareRegistryPresetExport,
  buildResultShareRegistryPresetWorkspaceHealthScore,
  buildResultShareRegistryPresetWorkspaceExport,
  buildResultShareRegistryPresetWorkspaceViewModel,
  buildInitialResultShareRegistrySavedViewState,
  buildResultShareRegistrySavedViewSummaries,
  buildResultShareRegistrySavedViewDraft,
  cleanStaleResultShareRegistryPresetWorkspacePins,
  clearAllResultShareRegistryPresetWorkspacePins,
  clearResultShareRegistryPresetAuditEvents,
  createPresetAuditEvent,
  createResultShareRegistryPresetBackup,
  createResultShareRegistryPresetWorkspaceBackup,
  createResultShareRegistrySavedView,
  deleteResultShareRegistrySavedView,
  getDefaultPresetWorkspaceHealthThresholdPreferences,
  inspectResultShareRegistryPresetStorage,
  loadResultShareRegistryPresetAuditEvents,
  loadPresetWorkspaceHealthThresholdPreferences,
  loadResultShareRegistryPresetWorkspaceBackup,
  loadResultShareRegistryPresetWorkspaceState,
  movePinnedResultShareRegistryPresetWorkspacePreset,
  loadResultShareRegistrySavedViewStore,
  overwriteResultShareRegistrySavedView,
  parseResultShareRegistryPresetImport,
  parseResultShareRegistryPresetWorkspaceImport,
  applyResultShareRegistryPresetWorkspaceImport,
  persistResultShareRegistryPresetWorkspaceState,
  persistResultShareRegistryPresetWorkspaceBackup,
  persistResultShareRegistrySavedViewStore,
  persistResultShareRegistryPresetBackup,
  pinResultShareRegistryPresetWorkspacePreset,
  redactUnsafeImportIssueDetails,
  resetResultShareRegistryPresetWorkspaceState,
  restoreResultShareRegistryPresetBackup,
  restoreResultShareRegistryPresetWorkspaceBackup,
  RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
  RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
  RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION,
  RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY,
  resetPresetWorkspaceHealthThresholdPreferences,
  saveResultShareRegistryPresetAuditEvents,
  saveResultShareRegistrySavedView,
  setResultShareRegistryPresetWorkspaceLastActive,
  setResultShareRegistryDefaultPresetId,
  syncResultShareRegistryPresetWorkspaceStateWithStore,
  unpinResultShareRegistryPresetWorkspacePreset,
  validatePresetWorkspaceHealthThresholdPreferences,
  persistPresetWorkspaceHealthThresholdPreferences,
} from "./resultShareRegistrySavedViews";
import type { ResultShareRegistryPresetLocalAuditLoadResult } from "./types";

function createMemoryStorage(): Storage {
  let store: Record<string, string> = {};
  return {
    get length() {
      return Object.keys(store).length;
    },
    clear() {
      store = {};
    },
    getItem(key: string) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null;
    },
    key(index: number) {
      return Object.keys(store)[index] ?? null;
    },
    removeItem(key: string) {
      delete store[key];
    },
    setItem(key: string, value: string) {
      store[key] = value;
    },
  };
}

describe("result share registry saved views", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      value: createMemoryStorage(),
      configurable: true,
    });
  });

  it("builds scope-separated saved view drafts from current registry state", () => {
    const grantDraft = buildResultShareRegistrySavedViewDraft(
      "grant_registry",
      " Active board grants ",
      {
        shareKind: "workspace_board",
        grantStatus: "active",
        aliasStatus: "revoked",
        workspaceId: " workspace-1 ",
        resultShareGrantId: "grant-9",
      },
      {
        grants: {
          field: "createdAt",
          direction: "asc",
        },
        aliases: {
          field: "status",
          direction: "desc",
        },
      },
    );
    const aliasDraft = buildResultShareRegistrySavedViewDraft(
      "alias_registry",
      "Alias follow-up",
      {
        shareKind: "digest_issue",
        grantStatus: "revoked",
        aliasStatus: "active",
        workspaceId: "workspace-9",
        resultShareGrantId: " grant-1 ",
      },
      {
        grants: {
          field: "createdAt",
          direction: "asc",
        },
        aliases: {
          field: "status",
          direction: "desc",
        },
      },
    );

    expect(grantDraft).toEqual({
      name: "Active board grants",
      scope: "grant_registry",
      filters: {
        ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
        shareKind: "workspace_board",
        grantStatus: "active",
        workspaceId: "workspace-1",
      },
      sort: {
        field: "createdAt",
        direction: "asc",
      },
      drilldownContext: null,
    });
    expect(aliasDraft).toEqual({
      name: "Alias follow-up",
      scope: "alias_registry",
      filters: {
        ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
        shareKind: "digest_issue",
        aliasStatus: "active",
        resultShareGrantId: "grant-1",
      },
      sort: {
        field: "status",
        direction: "desc",
      },
      drilldownContext: null,
    });
  });

  it("serializes and restores safe drilldown context when requested", () => {
    const draft = buildResultShareRegistrySavedViewDraft(
      "grant_registry",
      "Board review with drilldown",
      {
        ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
        shareKind: "workspace_board",
        workspaceId: "workspace-1",
      },
      DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      {
        includeDrilldownContext: true,
        drilldownFilters: {
          ...DEFAULT_CONVERSION_FILTER_INPUT,
          dateFrom: "2026-04-01",
          dateTo: "2026-04-18",
          accessMode: "alias",
          eventType: "content_view",
          outcome: "resolved",
          limit: 10,
        },
      },
    );
    expect(draft).not.toBeNull();
    expect(draft?.drilldownContext).toEqual({
      dateFrom: "2026-04-01",
      dateTo: "2026-04-18",
      accessMode: "alias",
      eventType: "content_view",
      outcome: "resolved",
      limit: 10,
    });

    const preset = createResultShareRegistrySavedView(draft!, {
      id: "preset-drilldown",
      now: "2026-04-18T08:00:00Z",
    });
    persistResultShareRegistrySavedViewStore(window.localStorage, {
      grantPresets: [preset],
      aliasPresets: [],
      defaultPresetId: null,
    });
    const loaded = loadResultShareRegistrySavedViewStore(window.localStorage);

    expect(loaded.grantPresets[0].drilldownContext).toEqual({
      dateFrom: "2026-04-01",
      dateTo: "2026-04-18",
      accessMode: "alias",
      eventType: "content_view",
      outcome: "resolved",
      limit: 10,
    });
  });

  it("loads legacy saved views that have no drilldown context", () => {
    window.localStorage.setItem(
      "resultShareRegistryGrantPresets",
      JSON.stringify([
        {
          id: "legacy-grant",
          name: "Legacy grant preset",
          scope: "grant_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: "active",
            aliasStatus: null,
            workspaceId: "workspace-1",
            resultShareGrantId: null,
          },
          sort: {
            field: "createdAt",
            direction: "asc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem("resultShareRegistryAliasPresets", JSON.stringify([]));

    const loaded = loadResultShareRegistrySavedViewStore(window.localStorage);
    expect(loaded.grantPresets).toHaveLength(1);
    expect(loaded.grantPresets[0].drilldownContext).toBeNull();
  });

  it("saves, overwrites, deletes, and serializes local presets", () => {
    const draft = buildResultShareRegistrySavedViewDraft(
      "grant_registry",
      "Board grants",
      {
        ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
        shareKind: "workspace_board",
        workspaceId: "workspace-1",
      },
      DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
    );
    expect(draft).not.toBeNull();

    const preset = createResultShareRegistrySavedView(draft!, {
      id: "preset-1",
      now: "2026-04-18T08:00:00Z",
    });
    const saved = saveResultShareRegistrySavedView(
      {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      preset,
    );

    persistResultShareRegistrySavedViewStore(window.localStorage, saved);
    const loaded = loadResultShareRegistrySavedViewStore(window.localStorage);
    expect(loaded.grantPresets).toHaveLength(1);
    expect(loaded.grantPresets[0]).toMatchObject({
      id: "preset-1",
      name: "Board grants",
      filters: expect.objectContaining({
        workspaceId: "workspace-1",
      }),
    });

    const overwritten = overwriteResultShareRegistrySavedView(
      loaded,
      "preset-1",
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Board grants updated",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          workspaceId: "workspace-2",
        },
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
          grants: {
            field: "createdAt",
            direction: "asc",
          },
        },
      )!,
      {
        now: "2026-04-18T09:00:00Z",
      },
    );
    expect(overwritten.grantPresets[0]).toMatchObject({
      name: "Board grants updated",
      updatedAt: "2026-04-18T09:00:00Z",
      filters: expect.objectContaining({
        workspaceId: "workspace-2",
      }),
      sort: {
        field: "createdAt",
        direction: "asc",
      },
    });

    const deleted = deleteResultShareRegistrySavedView(
      overwritten,
      "grant_registry",
      "preset-1",
    );
    expect(deleted.grantPresets).toHaveLength(0);
  });

  it("applies a scope-specific preset without polluting the other registry scope", () => {
    const preset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant review",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
          grants: {
            field: "createdAt",
            direction: "asc",
          },
        },
      )!,
      {
        id: "grant-preset",
        now: "2026-04-18T08:00:00Z",
      },
    );

    const applied = applyResultShareRegistrySavedView(
      {
        shareKind: "paper_snapshot",
        grantStatus: "revoked",
        aliasStatus: "active",
        workspaceId: "workspace-9",
        resultShareGrantId: "grant-9",
      },
      {
        grants: {
          field: "status",
          direction: "desc",
        },
        aliases: {
          field: "expiresAt",
          direction: "asc",
        },
      },
      {
        ...DEFAULT_CONVERSION_FILTER_INPUT,
        accessMode: "share_token",
        limit: 50,
      },
      preset,
      "registry_only",
    );

    expect(applied.filters).toEqual({
      shareKind: "workspace_board",
      grantStatus: "active",
      aliasStatus: "active",
      workspaceId: "workspace-1",
      resultShareGrantId: "grant-9",
    });
    expect(applied.sorts).toEqual({
      grants: {
        field: "createdAt",
        direction: "asc",
      },
      aliases: {
        field: "expiresAt",
        direction: "asc",
      },
    });
    expect(applied.drilldownFilters).toEqual({
      ...DEFAULT_CONVERSION_FILTER_INPUT,
      accessMode: "share_token",
      limit: 50,
    });
    expect(applied.didApplyDrilldownContext).toBe(false);
  });

  it("applies linked drilldown context only when explicitly requested", () => {
    const preset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias follow-up",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
        {
          includeDrilldownContext: true,
          drilldownFilters: {
            ...DEFAULT_CONVERSION_FILTER_INPUT,
            dateFrom: "2026-04-01",
            eventType: "redirect",
            limit: 10,
          },
        },
      )!,
      {
        id: "alias-preset",
        now: "2026-04-18T08:00:00Z",
      },
    );

    const registryOnly = applyResultShareRegistrySavedView(
      DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
      DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      {
        ...DEFAULT_CONVERSION_FILTER_INPUT,
        accessMode: "alias",
        limit: 50,
      },
      preset,
      "registry_only",
    );
    expect(registryOnly.drilldownFilters).toEqual({
      ...DEFAULT_CONVERSION_FILTER_INPUT,
      accessMode: "alias",
      limit: 50,
    });
    expect(registryOnly.didApplyDrilldownContext).toBe(false);

    const registryAndDrilldown = applyResultShareRegistrySavedView(
      DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
      DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      {
        ...DEFAULT_CONVERSION_FILTER_INPUT,
        accessMode: "alias",
        limit: 50,
      },
      preset,
      "registry_and_drilldown",
    );
    expect(registryAndDrilldown.drilldownFilters).toEqual({
      ...DEFAULT_CONVERSION_FILTER_INPUT,
      dateFrom: "2026-04-01",
      accessMode: null,
      eventType: "redirect",
      limit: 10,
    });
    expect(registryAndDrilldown.didApplyDrilldownContext).toBe(true);
  });

  it("restores the default preset into the initial registry state", () => {
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias follow-up",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
          aliases: {
            field: "status",
            direction: "desc",
          },
        },
      )!,
      {
        id: "alias-default",
        now: "2026-04-18T10:00:00Z",
      },
    );
    const store = setResultShareRegistryDefaultPresetId(
      saveResultShareRegistrySavedView(
        {
          grantPresets: [],
          aliasPresets: [],
          defaultPresetId: null,
        },
        aliasPreset,
      ),
      "alias-default",
    );

    const initialState = buildInitialResultShareRegistrySavedViewState(store);

    expect(initialState.defaultPreset?.id).toBe("alias-default");
    expect(initialState.filters).toEqual({
      ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
      shareKind: "workspace_board",
      aliasStatus: "active",
      resultShareGrantId: "grant-1",
    });
    expect(initialState.sorts).toEqual({
      grants: DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.grants,
      aliases: {
        field: "status",
        direction: "desc",
      },
    });
    expect(initialState.drilldownFilters).toEqual(DEFAULT_CONVERSION_FILTER_INPUT);
  });

  it("restores default preset drilldown context into the initial shell state", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant default with drilldown",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
        {
          includeDrilldownContext: true,
          drilldownFilters: {
            ...DEFAULT_CONVERSION_FILTER_INPUT,
            dateFrom: "2026-04-05",
            outcome: "resolved",
            limit: 10,
          },
        },
      )!,
      {
        id: "grant-default",
        now: "2026-04-18T10:00:00Z",
      },
    );
    const store = setResultShareRegistryDefaultPresetId(
      saveResultShareRegistrySavedView(
        {
          grantPresets: [],
          aliasPresets: [],
          defaultPresetId: null,
        },
        grantPreset,
      ),
      "grant-default",
    );

    const initialState = buildInitialResultShareRegistrySavedViewState(store);
    expect(initialState.defaultPreset?.id).toBe("grant-default");
    expect(initialState.drilldownFilters).toEqual({
      ...DEFAULT_CONVERSION_FILTER_INPUT,
      dateFrom: "2026-04-05",
      outcome: "resolved",
      limit: 10,
    });
  });

  it("exports only safe preset fields in the v1 JSON model", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant export",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
        {
          includeDrilldownContext: true,
          drilldownFilters: {
            ...DEFAULT_CONVERSION_FILTER_INPUT,
            dateFrom: "2026-04-01",
            eventType: "content_view",
            limit: 10,
          },
        },
      )!,
      {
        id: "grant-export",
        now: "2026-04-18T08:00:00Z",
      },
    );

    const payload = buildResultShareRegistryPresetExport(
      {
        grantPresets: [grantPreset],
        aliasPresets: [],
        defaultPresetId: "grant-export",
      },
      {
        now: "2026-04-18T09:00:00Z",
      },
    );

    expect(payload).toEqual({
      schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
      exportedAt: "2026-04-18T09:00:00Z",
      app: "research-pulse-cn",
      source: "group-workspace-admin-web",
      presets: {
        grantRegistry: [
          {
            id: "grant-export",
            name: "Grant export",
            scope: "grant_registry",
            filters: {
              ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
              shareKind: "workspace_board",
              grantStatus: "active",
              workspaceId: "workspace-1",
            },
            sort: {
              field: "lastUsedAt",
              direction: "desc",
            },
            drilldownContext: {
              dateFrom: "2026-04-01",
              dateTo: null,
              accessMode: null,
              eventType: "content_view",
              outcome: null,
              limit: 10,
            },
            createdAt: "2026-04-18T08:00:00Z",
            updatedAt: "2026-04-18T08:00:00Z",
          },
        ],
        aliasRegistry: [],
      },
    });
    expect(JSON.stringify(payload)).not.toContain("sourceFile");
    expect(JSON.stringify(payload)).not.toContain("rawShareToken");
  });

  it("accepts a valid v1 preset export payload", () => {
    const payload = buildResultShareRegistryPresetExport(
      {
        grantPresets: [],
        aliasPresets: [
          createResultShareRegistrySavedView(
            buildResultShareRegistrySavedViewDraft(
              "alias_registry",
              "Alias import",
              {
                ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
                shareKind: "workspace_board",
                aliasStatus: "active",
                resultShareGrantId: "grant-1",
              },
              DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
              {
                includeDrilldownContext: true,
                drilldownFilters: {
                  ...DEFAULT_CONVERSION_FILTER_INPUT,
                  dateFrom: "2026-04-05",
                  outcome: "resolved",
                  limit: 20,
                },
              },
            )!,
            {
              id: "alias-import",
              now: "2026-04-18T08:00:00Z",
            },
          ),
        ],
        defaultPresetId: null,
      },
      {
        now: "2026-04-18T10:00:00Z",
      },
    );

    const preview = parseResultShareRegistryPresetImport(JSON.stringify(payload));

    expect(preview.canApply).toBe(true);
    expect(preview.validPresetCount).toBe(1);
    expect(preview.invalidPresetCount).toBe(0);
    expect(preview.aliasPresetCount).toBe(1);
    expect(preview.presets.aliasRegistry[0]).toMatchObject({
      id: "alias-import",
      drilldownContext: {
        dateFrom: "2026-04-05",
        outcome: "resolved",
        limit: 20,
      },
    });
  });

  it("accepts older imports that omit drilldown context", () => {
    const preview = parseResultShareRegistryPresetImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-18T10:00:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        presets: {
          grantRegistry: [
            {
              id: "legacy-grant",
              name: "Legacy grant",
              scope: "grant_registry",
              filters: {
                shareKind: "workspace_board",
                grantStatus: "active",
                aliasStatus: null,
                workspaceId: "workspace-1",
                resultShareGrantId: null,
              },
              sort: {
                field: "createdAt",
                direction: "asc",
              },
              createdAt: "2026-04-18T08:00:00Z",
              updatedAt: "2026-04-18T08:00:00Z",
            },
          ],
          aliasRegistry: [],
        },
      }),
    );

    expect(preview.canApply).toBe(true);
    expect(preview.grantPresetCount).toBe(1);
    expect(preview.presets.grantRegistry[0].drilldownContext).toBeNull();
  });

  it("rejects unsafe import fields without mutating local storage state", () => {
    persistResultShareRegistrySavedViewStore(window.localStorage, {
      grantPresets: [],
      aliasPresets: [],
      defaultPresetId: null,
    });
    const before = window.localStorage.getItem("resultShareRegistryGrantPresets");

    const preview = parseResultShareRegistryPresetImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-18T10:00:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        secret: "blocked",
        presets: {
          grantRegistry: [
            {
              id: "unsafe-grant",
              name: "Unsafe grant",
              scope: "grant_registry",
              filters: {
                shareKind: "workspace_board",
                grantStatus: "active",
                aliasStatus: null,
                workspaceId: "workspace-1",
                resultShareGrantId: null,
              },
              sort: {
                field: "createdAt",
                direction: "asc",
              },
              sourceFile: "/tmp/preset.json",
              createdAt: "2026-04-18T08:00:00Z",
              updatedAt: "2026-04-18T08:00:00Z",
            },
          ],
          aliasRegistry: [],
        },
      }),
    );

    expect(preview.canApply).toBe(false);
    expect(preview.errors.join(" ")).toMatch(/unsafe field/i);
    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).toBe(before);
  });

  it("merges valid imports without losing existing presets and resolves id collisions", () => {
    const existingPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Board grant",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-duplicate",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const preview = parseResultShareRegistryPresetImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-18T10:00:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        presets: {
          grantRegistry: [
            {
              id: "grant-duplicate",
              name: "Board grant",
              scope: "grant_registry",
              filters: {
                shareKind: "digest_issue",
                grantStatus: "revoked",
                aliasStatus: null,
                workspaceId: null,
                resultShareGrantId: null,
              },
              sort: {
                field: "createdAt",
                direction: "asc",
              },
              createdAt: "2026-04-18T09:00:00Z",
              updatedAt: "2026-04-18T09:00:00Z",
            },
          ],
          aliasRegistry: [],
        },
      }),
    );

    const result = applyResultShareRegistryPresetImport(
      {
        grantPresets: [existingPreset],
        aliasPresets: [],
        defaultPresetId: null,
      },
      preview,
      "merge",
    );

    expect(result.store.grantPresets).toHaveLength(2);
    expect(result.store.grantPresets[0].id).toBe("grant-duplicate");
    expect(result.store.grantPresets[1].id).not.toBe("grant-duplicate");
    expect(result.store.grantPresets[1].name).toContain("Imported copy");
  });

  it("replaces only imported scopes and clears the default marker when its preset disappears", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant default",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-default",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias keep",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "alias-keep",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const preview = parseResultShareRegistryPresetImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-18T10:00:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        presets: {
          grantRegistry: [
            {
              id: "grant-imported",
              name: "Imported grant",
              scope: "grant_registry",
              filters: {
                shareKind: "digest_issue",
                grantStatus: "revoked",
                aliasStatus: null,
                workspaceId: null,
                resultShareGrantId: null,
              },
              sort: {
                field: "status",
                direction: "desc",
              },
              createdAt: "2026-04-18T09:00:00Z",
              updatedAt: "2026-04-18T09:00:00Z",
            },
          ],
        },
      }),
    );

    const result = applyResultShareRegistryPresetImport(
      {
        grantPresets: [grantPreset],
        aliasPresets: [aliasPreset],
        defaultPresetId: "grant-default",
      },
      preview,
      "replace",
    );

    expect(result.store.grantPresets).toHaveLength(1);
    expect(result.store.grantPresets[0].id).toBe("grant-imported");
    expect(result.store.aliasPresets).toHaveLength(1);
    expect(result.store.aliasPresets[0].id).toBe("alias-keep");
    expect(result.store.defaultPresetId).toBeNull();
    expect(result.defaultPresetCleared).toBe(true);
  });

  it("builds an integrity report for valid local preset storage", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant valid",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-valid",
        now: "2026-04-18T08:00:00Z",
      },
    );
    persistResultShareRegistrySavedViewStore(window.localStorage, {
      grantPresets: [grantPreset],
      aliasPresets: [],
      defaultPresetId: "grant-valid",
    });

    const inspection = inspectResultShareRegistryPresetStorage(window.localStorage, {
      now: "2026-04-18T09:00:00Z",
    });

    expect(inspection.report.errorCount).toBe(0);
    expect(inspection.report.warningCount).toBe(0);
    expect(inspection.report.validPresetCount).toBe(1);
    expect(inspection.diagnostics.defaultPresetIdPresent).toBe(true);
  });

  it("detects invalid JSON and non-array storage keys safely", () => {
    window.localStorage.setItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY, "{not-json");
    window.localStorage.setItem(
      RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
      JSON.stringify({ bad: true }),
    );

    const inspection = inspectResultShareRegistryPresetStorage(window.localStorage);

    expect(inspection.report.errorCount).toBeGreaterThanOrEqual(2);
    expect(inspection.report.issues.map((issue) => issue.code)).toContain("invalid_json");
    expect(inspection.report.issues.map((issue) => issue.code)).toContain(
      "storage_key_not_array",
    );
    expect(inspection.store.grantPresets).toEqual([]);
    expect(inspection.store.aliasPresets).toEqual([]);
  });

  it("redacts unsafe field names and detects duplicate preset ids with dangling defaults", () => {
    window.localStorage.setItem(
      RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
      JSON.stringify([
        {
          id: "duplicate-id",
          name: "Grant one",
          scope: "grant_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: "active",
            aliasStatus: null,
            workspaceId: "workspace-1",
            resultShareGrantId: null,
          },
          sort: {
            field: "createdAt",
            direction: "asc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem(
      RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
      JSON.stringify([
        {
          id: "duplicate-id",
          name: "Alias duplicate",
          scope: "alias_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: null,
            aliasStatus: "active",
            workspaceId: null,
            resultShareGrantId: "grant-1",
          },
          sort: {
            field: "status",
            direction: "desc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
          sourceFile: "/tmp/unsafe.json",
        },
      ]),
    );
    window.localStorage.setItem(RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY, "missing-id");

    const inspection = inspectResultShareRegistryPresetStorage(window.localStorage);

    expect(redactUnsafeImportIssueDetails("sourceFile")).toBe("[redacted]");
    expect(inspection.report.issues.map((issue) => issue.code)).toContain(
      "unsafe_field_detected",
    );
    expect(inspection.report.issues.map((issue) => issue.code)).toContain(
      "dangling_default_preset",
    );
    expect(inspection.store.defaultPresetId).toBeNull();
    expect(inspection.store.grantPresets).toHaveLength(1);
    expect(inspection.store.aliasPresets).toHaveLength(0);
  });

  it("creates and restores a last-good backup snapshot", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant backup",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-backup",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const backup = createResultShareRegistryPresetBackup(
      {
        grantPresets: [grantPreset],
        aliasPresets: [],
        defaultPresetId: "grant-backup",
      },
      "before_replace",
      {
        now: "2026-04-18T09:00:00Z",
      },
    );
    persistResultShareRegistryPresetBackup(window.localStorage, backup);

    const loadedBackup = inspectResultShareRegistryPresetStorage(window.localStorage).lastGoodBackup;
    const restored = restoreResultShareRegistryPresetBackup(loadedBackup);

    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY)).not.toBeNull();
    expect(restored).toEqual({
      grantPresets: [grantPreset],
      aliasPresets: [],
      defaultPresetId: "grant-backup",
    });
  });

  it("supports scope reset and backup restore recovery actions", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant reset",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-reset",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias reset",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "alias-reset",
        now: "2026-04-18T08:00:00Z",
      },
    );
    const store = {
      grantPresets: [grantPreset],
      aliasPresets: [aliasPreset],
      defaultPresetId: "grant-reset",
    };
    const backup = createResultShareRegistryPresetBackup(store, "before_reset");
    const report = inspectResultShareRegistryPresetStorage(window.localStorage).report;

    const resetGrant = applyResultShareRegistryPresetRecoveryAction(
      store,
      report,
      "reset_grant_scope",
      backup,
    );
    expect(resetGrant.store.grantPresets).toEqual([]);
    expect(resetGrant.store.aliasPresets).toEqual([aliasPreset]);
    expect(resetGrant.store.defaultPresetId).toBeNull();

    const restored = applyResultShareRegistryPresetRecoveryAction(
      resetGrant.store,
      report,
      "restore_last_good_backup",
      backup,
    );
    expect(restored.restoredBackup).toBe(true);
    expect(restored.store).toEqual(store);
  });

  it("keeps dry-run import validation from mutating local storage", () => {
    const beforeGrant = window.localStorage.getItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY);
    const beforeAlias = window.localStorage.getItem(RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY);

    const preview = parseResultShareRegistryPresetImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-18T10:00:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        presets: {
          grantRegistry: [
            {
              id: "grant-dry-run",
              name: "Grant dry run",
              scope: "grant_registry",
              filters: {
                shareKind: "workspace_board",
                grantStatus: "active",
                aliasStatus: null,
                workspaceId: "workspace-1",
                resultShareGrantId: null,
              },
              sort: {
                field: "createdAt",
                direction: "asc",
              },
              createdAt: "2026-04-18T08:00:00Z",
              updatedAt: "2026-04-18T08:00:00Z",
            },
          ],
        },
      }),
    );

    expect(preview.canApply).toBe(true);
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY)).toBe(beforeGrant);
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY)).toBe(beforeAlias);
  });

  it("appends audit events with a deterministic max history cap", () => {
    let auditState: ResultShareRegistryPresetLocalAuditLoadResult = {
      events: [],
      storageWarning: null,
    };
    for (let index = 0; index < 110; index += 1) {
      auditState = appendResultShareRegistryPresetAuditEvent(
        window.localStorage,
        createPresetAuditEvent(
          "preset_saved",
          "success",
          `Saved preset ${index}`,
          {
            scope: "grant_registry",
            presetId: `preset-${index}`,
            presetName: `Preset ${index}`,
            occurredAt: `2026-04-18T08:${String(index % 60).padStart(2, "0")}:00Z`,
            id: `event-${index}`,
          },
        ),
      );
    }

    expect(auditState.events).toHaveLength(100);
    expect(auditState.events[0].id).toBe("event-109");
    expect(auditState.events[99].id).toBe("event-10");
  });

  it("builds audit summary counts by action type, scope, and status", () => {
    const events = [
      createPresetAuditEvent("preset_saved", "success", "Saved grant preset.", {
        scope: "grant_registry",
        occurredAt: "2026-04-18T10:00:00Z",
        id: "audit-1",
      }),
      createPresetAuditEvent("import_merge", "warning", "Merged preset import.", {
        scope: "storage",
        occurredAt: "2026-04-18T10:01:00Z",
        id: "audit-2",
      }),
      createPresetAuditEvent("backup_restored", "failed", "Restore failed.", {
        scope: "storage",
        occurredAt: "2026-04-18T10:02:00Z",
        id: "audit-3",
      }),
    ];

    const summary = buildResultShareRegistryPresetAuditSummary(events, {
      storageWarning: "Audit storage warning.",
    });

    expect(summary.totalEvents).toBe(3);
    expect(summary.successCount).toBe(1);
    expect(summary.warningCount).toBe(1);
    expect(summary.failedCount).toBe(1);
    expect(summary.byActionType.preset_saved).toBe(1);
    expect(summary.byActionType.import_merge).toBe(1);
    expect(summary.byActionType.backup_restored).toBe(1);
    expect(summary.byScope.grant_registry).toBe(1);
    expect(summary.byScope.storage).toBe(2);
    expect(summary.importRelatedCount).toBe(1);
    expect(summary.backupRelatedCount).toBe(1);
    expect(summary.recoveryRelatedCount).toBe(1);
    expect(summary.storageWarning).toBe("Audit storage warning.");
  });

  it("keeps corrupted audit localStorage isolated from preset storage", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant intact",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-intact",
        now: "2026-04-18T08:00:00Z",
      },
    );
    persistResultShareRegistrySavedViewStore(window.localStorage, {
      grantPresets: [grantPreset],
      aliasPresets: [],
      defaultPresetId: null,
    });
    window.localStorage.setItem(RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY, "{not-json");

    const presetStore = loadResultShareRegistrySavedViewStore(window.localStorage);
    const auditState = loadResultShareRegistryPresetAuditEvents(window.localStorage);

    expect(presetStore.grantPresets).toHaveLength(1);
    expect(presetStore.grantPresets[0].name).toBe("Grant intact");
    expect(auditState.events).toEqual([]);
    expect(auditState.storageWarning).toMatch(/not valid JSON/i);
  });

  it("saves and clears safe local audit history", () => {
    const events = saveResultShareRegistryPresetAuditEvents(window.localStorage, [
      createPresetAuditEvent("export_created", "success", "Exported presets.", {
        scope: "storage",
        id: "audit-export",
        occurredAt: "2026-04-18T10:05:00Z",
      }),
    ]);
    expect(events).toHaveLength(1);
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY)).toContain(
      "audit-export",
    );

    clearResultShareRegistryPresetAuditEvents(window.localStorage);
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY)).toBeNull();
  });

  it("serializes and restores local preset workspace state safely", () => {
    const persisted = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-a", "grant-b"],
      pinnedAliasPresetIds: ["alias-a"],
      lastActivePresetScope: "grant_registry",
      lastActivePresetId: "grant-a",
      collapsedSections: null,
      updatedAt: "2026-04-19T02:00:00Z",
    });

    expect(persisted.pinnedGrantPresetIds).toEqual(["grant-a", "grant-b"]);
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY)).toContain(
      "grant-a",
    );

    const loaded = loadResultShareRegistryPresetWorkspaceState(window.localStorage);
    expect(loaded.keyPresent).toBe(true);
    expect(loaded.storageWarning).toBeNull();
    expect(loaded.state.lastActivePresetScope).toBe("grant_registry");
    expect(loaded.state.lastActivePresetId).toBe("grant-a");
  });

  it("falls back safely when workspace state is corrupted", () => {
    window.localStorage.setItem(RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY, "{oops");

    const loaded = loadResultShareRegistryPresetWorkspaceState(window.localStorage);

    expect(loaded.keyPresent).toBe(true);
    expect(loaded.state.pinnedGrantPresetIds).toEqual([]);
    expect(loaded.state.pinnedAliasPresetIds).toEqual([]);
    expect(loaded.storageWarning).toMatch(/not valid JSON/i);
  });

  it("exports and parses safe preset workspace state JSON", () => {
    const workspaceState = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-a"],
      pinnedAliasPresetIds: ["alias-a"],
      lastActivePresetScope: "grant_registry",
      lastActivePresetId: "grant-a",
      collapsedSections: {
        pinnedGrantPresets: true,
        pinnedAliasPresets: false,
        recentGrantPresets: true,
        recentAliasPresets: false,
        recentActivity: false,
        storageHealth: true,
      },
      updatedAt: "2026-04-19T03:00:00Z",
    });
    const payload = buildResultShareRegistryPresetWorkspaceExport(workspaceState, {
      now: "2026-04-19T03:01:00Z",
    });

    expect(payload).toEqual({
      schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
      exportedAt: "2026-04-19T03:01:00Z",
      app: "research-pulse-cn",
      source: "group-workspace-admin-web",
      workspaceState,
    });
    expect(JSON.stringify(payload)).not.toContain("token");
    expect(JSON.stringify(payload)).not.toContain("rawAlias");

    const preview = parseResultShareRegistryPresetWorkspaceImport(
      JSON.stringify(payload),
      {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
    );

    expect(preview.canApply).toBe(true);
    expect(preview.valid).toBe(true);
    expect(preview.workspaceState?.pinnedGrantPresetIds).toEqual(["grant-a"]);
    expect(preview.workspaceState?.pinnedAliasPresetIds).toEqual(["alias-a"]);
  });

  it("tolerates missing optional workspace import fields and reports stale pins safely", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant workspace",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-existing",
        now: "2026-04-19T03:02:00Z",
      },
    );

    const preview = parseResultShareRegistryPresetWorkspaceImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-19T03:03:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        workspaceState: {
          pinnedGrantPresetIds: ["grant-existing", "grant-missing"],
          lastActivePresetScope: "grant_registry",
          lastActivePresetId: "grant-missing",
        },
      }),
      {
        grantPresets: [grantPreset],
        aliasPresets: [],
        defaultPresetId: null,
      },
    );

    expect(preview.canApply).toBe(true);
    expect(preview.workspaceState?.pinnedAliasPresetIds).toEqual([]);
    expect(preview.workspaceState?.collapsedSections).toBeNull();
    expect(preview.stalePinnedGrantPresetIds).toEqual(["grant-missing"]);
    expect(preview.lastActivePresetExists).toBe(false);
    expect(preview.warnings.some((warning) => warning.includes("stale grant pin"))).toBe(true);
  });

  it("rejects unsafe workspace import fields before mutating storage", () => {
    const preview = parseResultShareRegistryPresetWorkspaceImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-19T03:03:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        workspaceState: {
          pinnedGrantPresetIds: ["grant-a"],
          rawShareToken: "secret-value",
          updatedAt: "2026-04-19T03:03:00Z",
        },
      }),
      {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
    );

    expect(preview.canApply).toBe(false);
    expect(preview.errors[0]).toMatch(/unsafe field/i);
    expect(preview.errors[0]).not.toContain("secret-value");
    expect(window.localStorage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_STATE_STORAGE_KEY)).toBeNull();
  });

  it("merges and replaces workspace organization state without touching saved presets", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant one",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-one",
        now: "2026-04-19T03:04:00Z",
      },
    );
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias one",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          resultShareGrantId: "grant-one",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "alias-one",
        now: "2026-04-19T03:05:00Z",
      },
    );
    const store = {
      grantPresets: [grantPreset],
      aliasPresets: [aliasPreset],
      defaultPresetId: null,
    };
    const currentState = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-one"],
      pinnedAliasPresetIds: [],
      lastActivePresetScope: "grant_registry",
      lastActivePresetId: "grant-one",
      collapsedSections: null,
      updatedAt: "2026-04-19T03:06:00Z",
    });

    const mergePreview = parseResultShareRegistryPresetWorkspaceImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-19T03:07:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        workspaceState: {
          pinnedGrantPresetIds: ["grant-one"],
          pinnedAliasPresetIds: ["alias-one", "alias-missing"],
          lastActivePresetScope: "alias_registry",
          lastActivePresetId: "alias-one",
          collapsedSections: {
            storageHealth: true,
          },
        },
      }),
      store,
    );
    const merged = applyResultShareRegistryPresetWorkspaceImport(
      currentState,
      mergePreview,
      "merge",
      store,
      {
        now: "2026-04-19T03:08:00Z",
      },
    );
    expect(merged.workspaceState.pinnedGrantPresetIds).toEqual(["grant-one"]);
    expect(merged.workspaceState.pinnedAliasPresetIds).toEqual(["alias-one", "alias-missing"]);
    expect(merged.workspaceState.lastActivePresetId).toBe("alias-one");
    expect(merged.stalePinnedAliasPresetIds).toEqual(["alias-missing"]);

    const replacePreview = parseResultShareRegistryPresetWorkspaceImport(
      JSON.stringify({
        schemaVersion: RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_EXPORT_SCHEMA_VERSION,
        exportedAt: "2026-04-19T03:09:00Z",
        app: "research-pulse-cn",
        source: "group-workspace-admin-web",
        workspaceState: {
          pinnedGrantPresetIds: [],
          pinnedAliasPresetIds: ["alias-one"],
          lastActivePresetScope: "grant_registry",
          lastActivePresetId: "grant-missing",
          updatedAt: "2026-04-19T03:09:00Z",
        },
      }),
      store,
    );
    const replaced = applyResultShareRegistryPresetWorkspaceImport(
      currentState,
      replacePreview,
      "replace",
      store,
      {
        now: "2026-04-19T03:10:00Z",
      },
    );
    expect(replaced.workspaceState.pinnedGrantPresetIds).toEqual([]);
    expect(replaced.workspaceState.pinnedAliasPresetIds).toEqual(["alias-one"]);
    expect(replaced.workspaceState.lastActivePresetId).toBeNull();
    expect(replaced.lastActivePresetCleared).toBe(true);
    expect(store.grantPresets[0].name).toBe("Grant one");
    expect(store.aliasPresets[0].name).toBe("Alias one");
  });

  it("creates and restores a workspace-state last-good backup snapshot", () => {
    const workspaceState = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-a"],
      pinnedAliasPresetIds: ["alias-a"],
      lastActivePresetScope: "alias_registry",
      lastActivePresetId: "alias-a",
      collapsedSections: null,
      updatedAt: "2026-04-19T03:11:00Z",
    });
    const backup = createResultShareRegistryPresetWorkspaceBackup(
      workspaceState,
      "workspace_import_replace",
      {
        now: "2026-04-19T03:12:00Z",
      },
    );

    expect(backup.schemaVersion).toBe(
      RESULT_SHARE_REGISTRY_PRESET_WORKSPACE_BACKUP_SCHEMA_VERSION,
    );

    persistResultShareRegistryPresetWorkspaceBackup(window.localStorage, backup);
    expect(
      window.localStorage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_LAST_GOOD_BACKUP_STORAGE_KEY),
    ).toContain("workspace_import_replace");

    const loadedBackup = loadResultShareRegistryPresetWorkspaceBackup(window.localStorage);
    expect(loadedBackup?.reason).toBe("workspace_import_replace");
    expect(restoreResultShareRegistryPresetWorkspaceBackup(loadedBackup)?.pinnedGrantPresetIds).toEqual([
      "grant-a",
    ]);
  });

  it("pins, unpins, moves, and cleans stale workspace preset ids without touching saved presets", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Pinned grant",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          grantStatus: "active",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-preset",
        now: "2026-04-19T02:01:00Z",
      },
    );
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Pinned alias",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "alias-preset",
        now: "2026-04-19T02:02:00Z",
      },
    );
    const store = {
      grantPresets: [grantPreset],
      aliasPresets: [aliasPreset],
      defaultPresetId: null,
    };

    let workspaceState = resetResultShareRegistryPresetWorkspaceState({
      now: "2026-04-19T02:03:00Z",
    });
    workspaceState = pinResultShareRegistryPresetWorkspacePreset(
      workspaceState,
      "grant_registry",
      "grant-preset",
    );
    workspaceState = pinResultShareRegistryPresetWorkspacePreset(
      workspaceState,
      "grant_registry",
      "grant-stale",
    );
    workspaceState = pinResultShareRegistryPresetWorkspacePreset(
      workspaceState,
      "alias_registry",
      "alias-preset",
    );
    workspaceState = setResultShareRegistryPresetWorkspaceLastActive(
      workspaceState,
      "grant_registry",
      "grant-preset",
    );
    workspaceState = movePinnedResultShareRegistryPresetWorkspacePreset(
      workspaceState,
      "grant_registry",
      "grant-stale",
      "up",
    );

    expect(workspaceState.pinnedGrantPresetIds[0]).toBe("grant-stale");

    const cleaned = cleanStaleResultShareRegistryPresetWorkspacePins(workspaceState, store);
    expect(cleaned.removedGrantPinIds).toEqual(["grant-stale"]);
    expect(cleaned.state.pinnedGrantPresetIds).toEqual(["grant-preset"]);
    expect(cleaned.state.pinnedAliasPresetIds).toEqual(["alias-preset"]);

    const unpinned = unpinResultShareRegistryPresetWorkspacePreset(
      cleaned.state,
      "alias_registry",
      "alias-preset",
    );
    expect(unpinned.pinnedAliasPresetIds).toEqual([]);

    const cleared = clearAllResultShareRegistryPresetWorkspacePins(unpinned);
    expect(cleared.pinnedGrantPresetIds).toEqual([]);

    const synced = syncResultShareRegistryPresetWorkspaceStateWithStore(
      {
        ...workspaceState,
        lastActivePresetScope: "grant_registry",
        lastActivePresetId: "missing-preset",
      },
      store,
    );
    expect(synced.lastActivePresetId).toBeNull();
    expect(synced.lastActivePresetScope).toBeNull();
  });

  it("builds a preset workspace overview from saved views, diagnostics, backup, and audit state", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Grant workspace preset",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
        {
          includeDrilldownContext: true,
          drilldownFilters: {
            ...DEFAULT_CONVERSION_FILTER_INPUT,
            eventType: "content_view",
            limit: 10,
          },
        },
      )!,
      {
        id: "grant-workspace",
        now: "2026-04-19T02:05:00Z",
      },
    );
    const aliasPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "alias_registry",
        "Alias workspace preset",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          shareKind: "workspace_board",
          aliasStatus: "active",
          resultShareGrantId: "grant-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "alias-workspace",
        now: "2026-04-19T02:06:00Z",
      },
    );
    const store = {
      grantPresets: [grantPreset],
      aliasPresets: [aliasPreset],
      defaultPresetId: "grant-workspace",
    };
    const workspaceState = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-workspace", "missing-grant"],
      pinnedAliasPresetIds: ["alias-workspace"],
      lastActivePresetScope: "grant_registry",
      lastActivePresetId: "grant-workspace",
      collapsedSections: null,
      updatedAt: "2026-04-19T02:07:00Z",
    });
    const summaries = buildResultShareRegistrySavedViewSummaries(store, workspaceState);
    const auditSummary = buildResultShareRegistryPresetAuditSummary([
      createPresetAuditEvent("preset_pinned", "success", "Pinned preset.", {
        scope: "grant_registry",
        id: "audit-pinned",
        occurredAt: "2026-04-19T02:08:00Z",
      }),
      createPresetAuditEvent("backup_created", "warning", "Created backup.", {
        scope: "storage",
        id: "audit-backup",
        occurredAt: "2026-04-19T02:09:00Z",
      }),
    ]);
    const diagnostics = inspectResultShareRegistryPresetStorage(window.localStorage, {
      now: "2026-04-19T02:10:00Z",
    }).diagnostics;
    const backup = createResultShareRegistryPresetBackup(store, "workspace_test", {
      now: "2026-04-19T02:11:00Z",
    });
    const workspaceBackup = createResultShareRegistryPresetWorkspaceBackup(
      workspaceState,
      "workspace_import_merge",
      {
        now: "2026-04-19T02:12:00Z",
      },
    );

    const workspaceViewModel = buildResultShareRegistryPresetWorkspaceViewModel(
      summaries,
      workspaceState,
      auditSummary,
      diagnostics,
      backup,
      workspaceBackup,
    );

    expect(workspaceViewModel.pinnedGrantPresets).toHaveLength(1);
    expect(workspaceViewModel.pinnedGrantPresets[0].name).toBe("Grant workspace preset");
    expect(workspaceViewModel.staleGrantPinIds).toEqual(["missing-grant"]);
    expect(workspaceViewModel.pinnedAliasPresets[0].name).toBe("Alias workspace preset");
    expect(workspaceViewModel.lastActivePresetLabel).toContain("Grant preset");
    expect(workspaceViewModel.storageHealth.lastBackupLabel).toContain("workspace_test");
    expect(workspaceViewModel.storageHealth.workspaceBackupLabel).toContain(
      "workspace_import_merge",
    );
    expect(workspaceViewModel.recentActivity).toHaveLength(2);
    expect(
      workspaceViewModel.overviewSummary.some((item) => item.label === "Pinned grants" && item.value === 1),
    ).toBe(true);
  });

  it("builds a healthy workspace score for clean local preset state", () => {
    const grantPreset = createResultShareRegistrySavedView(
      buildResultShareRegistrySavedViewDraft(
        "grant_registry",
        "Healthy grant preset",
        {
          ...DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
          workspaceId: "workspace-1",
        },
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      )!,
      {
        id: "grant-healthy",
        now: "2026-04-19T04:00:00Z",
      },
    );
    const store = {
      grantPresets: [grantPreset],
      aliasPresets: [],
      defaultPresetId: null,
    };
    persistResultShareRegistrySavedViewStore(window.localStorage, store);
    const workspaceState = persistResultShareRegistryPresetWorkspaceState(window.localStorage, {
      pinnedGrantPresetIds: ["grant-healthy"],
      pinnedAliasPresetIds: [],
      lastActivePresetScope: "grant_registry",
      lastActivePresetId: "grant-healthy",
      collapsedSections: null,
      updatedAt: "2026-04-19T04:01:00Z",
    });
    const inspection = inspectResultShareRegistryPresetStorage(window.localStorage, {
      now: "2026-04-19T04:02:00Z",
    });
    const presetBackup = createResultShareRegistryPresetBackup(store, "healthy_test", {
      now: "2026-04-19T04:03:00Z",
    });
    const workspaceBackup = createResultShareRegistryPresetWorkspaceBackup(
      workspaceState,
      "workspace_healthy_test",
      {
        now: "2026-04-19T04:04:00Z",
      },
    );

    const health = buildResultShareRegistryPresetWorkspaceHealthScore({
      store,
      integrityReport: inspection.report,
      diagnostics: inspection.diagnostics,
      lastGoodBackup: presetBackup,
      workspaceBackup,
      workspaceState,
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      checkedAt: "2026-04-19T04:05:00Z",
    });

    expect(health.score).toBe(100);
    expect(health.status).toBe("healthy");
    expect(health.findings).toEqual([]);
    expect(health.recommendations).toEqual([]);
  });

  it("applies deterministic penalties and findings for invalid storage, stale pins, audit issues, and import errors", () => {
    const report = {
      checkedAt: "2026-04-19T04:06:00Z",
      grantPresetCount: 0,
      aliasPresetCount: 0,
      validPresetCount: 0,
      invalidPresetCount: 1,
      warningCount: 1,
      errorCount: 3,
      issues: [
        {
          severity: "error" as const,
          scope: "storage" as const,
          presetId: null,
          presetName: null,
          code: "invalid_json" as const,
          message: "invalid json",
          safeDetails: "resultShareRegistryGrantPresets",
        },
        {
          severity: "error" as const,
          scope: "grant_registry" as const,
          presetId: "preset-unsafe",
          presetName: "Unsafe preset",
          code: "unsafe_field_detected" as const,
          message: "unsafe",
          safeDetails: "[redacted]",
        },
        {
          severity: "warning" as const,
          scope: "storage" as const,
          presetId: null,
          presetName: null,
          code: "dangling_default_preset" as const,
          message: "dangling",
          safeDetails: "dangling-id",
        },
        {
          severity: "warning" as const,
          scope: "grant_registry" as const,
          presetId: "preset-drilldown",
          presetName: "Broken drilldown",
          code: "invalid_drilldown_context" as const,
          message: "invalid drilldown",
          safeDetails: null,
        },
      ],
      canAutoRepair: true,
      canResetGrantScope: true,
      canResetAliasScope: true,
      notes: [],
    };
    const diagnostics = {
      checkedAt: "2026-04-19T04:06:00Z",
      storageKeysPresent: {
        grantPresets: true,
        aliasPresets: false,
        defaultPresetId: true,
        lastGoodBackup: false,
        workspaceState: true,
      },
      grantPresetCount: 0,
      aliasPresetCount: 0,
      validPresetCount: 0,
      invalidPresetCount: 1,
      defaultPresetIdPresent: true,
      lastBackupPresent: false,
      workspaceStatePresent: true,
      workspaceStateWarning: "Local preset workspace state is not valid JSON and fell back to defaults.",
      latestValidationAt: "2026-04-19T04:06:00Z",
      warningCount: 1,
      errorCount: 3,
      notes: [],
    };
    const workspaceState = {
      pinnedGrantPresetIds: ["missing-grant-1", "missing-grant-2"],
      pinnedAliasPresetIds: ["missing-alias-1"],
      lastActivePresetScope: "grant_registry" as const,
      lastActivePresetId: "missing-grant-1",
      collapsedSections: null,
      updatedAt: "2026-04-19T04:07:00Z",
    };
    const auditSummary = buildResultShareRegistryPresetAuditSummary([
      createPresetAuditEvent(
        "validation_failed",
        "failed",
        "Import validation failed.",
        {
          scope: "storage",
          occurredAt: "2026-04-19T04:08:00Z",
        },
      ),
      createPresetAuditEvent(
        "recovery_failed",
        "failed",
        "Recovery failed.",
        {
          scope: "storage",
          occurredAt: "2026-04-19T04:09:00Z",
        },
      ),
    ], {
      storageWarning: "Local preset audit storage is not valid JSON.",
    });

    const health = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: report,
      diagnostics,
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState,
      auditSummary,
      workspaceImportPreview: {
        schemaVersion: "result-share-registry-preset-workspace.v1",
        valid: false,
        canApply: false,
        warnings: [],
        errors: ["blocking error"],
        pinnedGrantPresetCount: 2,
        pinnedAliasPresetCount: 1,
        stalePinnedGrantPresetIds: ["missing-grant-1", "missing-grant-2"],
        stalePinnedAliasPresetIds: ["missing-alias-1"],
        lastActivePresetExists: false,
        workspaceState,
      },
      checkedAt: "2026-04-19T04:10:00Z",
    });

    expect(health.score).toBe(0);
    expect(health.status).toBe("critical");
    expect(health.findings.map((finding) => finding.code)).toEqual(
      expect.arrayContaining([
        "storage_invalid_json",
        "unsafe_field_detected",
        "dangling_default_preset",
        "stale_pinned_presets",
        "missing_last_good_backup",
        "corrupted_audit_history",
        "recent_failed_import",
        "recent_failed_recovery",
        "no_saved_presets",
        "invalid_drilldown_context",
        "import_preview_has_errors",
      ]),
    );
    expect(JSON.stringify(health)).not.toContain("missing-grant-1");
    expect(JSON.stringify(health)).not.toContain("secret-token");
  });

  it("keeps no-presets and no-pins findings low severity and recommends backup/pinning deterministically", () => {
    const health = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: {
        checkedAt: "2026-04-19T04:11:00Z",
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        warningCount: 0,
        errorCount: 0,
        issues: [],
        canAutoRepair: false,
        canResetGrantScope: false,
        canResetAliasScope: false,
        notes: [],
      },
      diagnostics: {
        checkedAt: "2026-04-19T04:11:00Z",
        storageKeysPresent: {
          grantPresets: false,
          aliasPresets: false,
          defaultPresetId: false,
          lastGoodBackup: false,
          workspaceState: false,
        },
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        defaultPresetIdPresent: false,
        lastBackupPresent: false,
        workspaceStatePresent: false,
        workspaceStateWarning: null,
        latestValidationAt: null,
        warningCount: 0,
        errorCount: 0,
        notes: [],
      },
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState: resetResultShareRegistryPresetWorkspaceState({
        now: "2026-04-19T04:12:00Z",
      }),
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      checkedAt: "2026-04-19T04:13:00Z",
    });

    expect(
      health.findings.every((finding) =>
        finding.severity === "info" || finding.severity === "warning",
      ),
    ).toBe(true);
    expect(health.recommendations.map((item) => item.kind)).toEqual(["create_backup"]);
  });

  it("preserves default status mapping and allows valid local thresholds to reclassify the same raw score", () => {
    const defaults = getDefaultPresetWorkspaceHealthThresholdPreferences({
      now: "2026-04-19T04:14:00Z",
    });
    const validation = validatePresetWorkspaceHealthThresholdPreferences({
      statusThresholds: {
        healthyMin: "80",
        attentionMin: "60",
        riskMin: "30",
        criticalMin: "0",
      },
      findingPenaltyOverrides: {},
      recommendationVisibility: defaults.recommendationVisibility,
    });

    expect(validation.valid).toBe(true);
    expect(validation.normalizedPreferences).not.toBeNull();

    const defaultHealth = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: {
        checkedAt: "2026-04-19T04:14:00Z",
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        warningCount: 0,
        errorCount: 0,
        issues: [],
        canAutoRepair: false,
        canResetGrantScope: false,
        canResetAliasScope: false,
        notes: [],
      },
      diagnostics: {
        checkedAt: "2026-04-19T04:14:00Z",
        storageKeysPresent: {
          grantPresets: true,
          aliasPresets: false,
          defaultPresetId: false,
          lastGoodBackup: false,
          workspaceState: true,
        },
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        defaultPresetIdPresent: false,
        lastBackupPresent: false,
        workspaceStatePresent: true,
        workspaceStateWarning: null,
        latestValidationAt: "2026-04-19T04:14:00Z",
        warningCount: 0,
        errorCount: 0,
        notes: [],
      },
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState: {
        pinnedGrantPresetIds: [],
        pinnedAliasPresetIds: [],
        lastActivePresetScope: null,
        lastActivePresetId: null,
        collapsedSections: null,
        updatedAt: "2026-04-19T04:14:00Z",
      },
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      checkedAt: "2026-04-19T04:14:00Z",
    });
    const customHealth = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: {
        checkedAt: "2026-04-19T04:14:00Z",
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        warningCount: 0,
        errorCount: 0,
        issues: [],
        canAutoRepair: false,
        canResetGrantScope: false,
        canResetAliasScope: false,
        notes: [],
      },
      diagnostics: {
        checkedAt: "2026-04-19T04:14:00Z",
        storageKeysPresent: {
          grantPresets: true,
          aliasPresets: false,
          defaultPresetId: false,
          lastGoodBackup: false,
          workspaceState: true,
        },
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        defaultPresetIdPresent: false,
        lastBackupPresent: false,
        workspaceStatePresent: true,
        workspaceStateWarning: null,
        latestValidationAt: "2026-04-19T04:14:00Z",
        warningCount: 0,
        errorCount: 0,
        notes: [],
      },
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState: {
        pinnedGrantPresetIds: [],
        pinnedAliasPresetIds: [],
        lastActivePresetScope: null,
        lastActivePresetId: null,
        collapsedSections: null,
        updatedAt: "2026-04-19T04:14:00Z",
      },
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      thresholdPreferences: validation.normalizedPreferences ?? undefined,
      thresholdPreferenceSource: "local",
      checkedAt: "2026-04-19T04:14:00Z",
    });

    expect(defaultHealth.score).toBe(85);
    expect(defaultHealth.score).toBe(customHealth.score);
    expect(defaultHealth.status).toBe("attention");
    expect(customHealth.status).toBe("healthy");
    expect(customHealth.thresholdPreferenceSource).toBe("local");
  });

  it("rejects invalid threshold ordering and out-of-range values", () => {
    const invalidOrder = validatePresetWorkspaceHealthThresholdPreferences({
      statusThresholds: {
        healthyMin: "70",
        attentionMin: "80",
        riskMin: "40",
        criticalMin: "0",
      },
      findingPenaltyOverrides: {},
      recommendationVisibility: {
        showInfo: true,
        showWarnings: true,
        showErrors: true,
        showCritical: true,
      },
    });
    const outOfRange = validatePresetWorkspaceHealthThresholdPreferences({
      statusThresholds: {
        healthyMin: "120",
        attentionMin: "70",
        riskMin: "40",
        criticalMin: "0",
      },
      findingPenaltyOverrides: {},
      recommendationVisibility: {
        showInfo: true,
        showWarnings: true,
        showErrors: true,
        showCritical: true,
      },
    });

    expect(invalidOrder.valid).toBe(false);
    expect(invalidOrder.errors.join(" ")).toMatch(/healthyMin > attentionMin > riskMin > criticalMin/i);
    expect(outOfRange.valid).toBe(false);
    expect(outOfRange.errors.join(" ")).toMatch(/within 0..100/i);
  });

  it("falls back to defaults when threshold preference storage is corrupted and resets only that key", () => {
    const storage = createMemoryStorage();
    storage.setItem(
      RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY,
      "{not-json",
    );
    storage.setItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY, "[]");

    const loaded = loadPresetWorkspaceHealthThresholdPreferences(storage);
    expect(loaded.source).toBe("default");
    expect(loaded.storageWarning).toMatch(/fell back to defaults/i);
    expect(loaded.preferences.statusThresholds.healthyMin).toBe(90);

    const persisted = persistPresetWorkspaceHealthThresholdPreferences(
      storage,
      getDefaultPresetWorkspaceHealthThresholdPreferences({
        now: "2026-04-19T04:15:00Z",
      }),
    );
    expect(persisted.statusThresholds.attentionMin).toBe(70);

    const reset = resetPresetWorkspaceHealthThresholdPreferences(storage);
    expect(reset.statusThresholds.riskMin).toBe(40);
    expect(storage.getItem(RESULT_SHARE_REGISTRY_WORKSPACE_HEALTH_THRESHOLD_PREFERENCES_STORAGE_KEY)).toBeNull();
    expect(storage.getItem(RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY)).toBe("[]");
  });

  it("builds a deterministic threshold preview for before and after status impact", () => {
    const currentHealth = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: {
        checkedAt: "2026-04-19T04:16:00Z",
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        warningCount: 0,
        errorCount: 0,
        issues: [],
        canAutoRepair: false,
        canResetGrantScope: false,
        canResetAliasScope: false,
        notes: [],
      },
      diagnostics: {
        checkedAt: "2026-04-19T04:16:00Z",
        storageKeysPresent: {
          grantPresets: true,
          aliasPresets: false,
          defaultPresetId: false,
          lastGoodBackup: false,
          workspaceState: true,
        },
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        defaultPresetIdPresent: false,
        lastBackupPresent: false,
        workspaceStatePresent: true,
        workspaceStateWarning: null,
        latestValidationAt: "2026-04-19T04:16:00Z",
        warningCount: 0,
        errorCount: 0,
        notes: [],
      },
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState: resetResultShareRegistryPresetWorkspaceState({
        now: "2026-04-19T04:16:00Z",
      }),
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      checkedAt: "2026-04-19T04:16:00Z",
    });
    const validation = validatePresetWorkspaceHealthThresholdPreferences({
      statusThresholds: {
        healthyMin: "80",
        attentionMin: "60",
        riskMin: "30",
        criticalMin: "0",
      },
      findingPenaltyOverrides: {},
      recommendationVisibility: {
        showInfo: true,
        showWarnings: true,
        showErrors: true,
        showCritical: true,
      },
    });
    const draftHealth = buildResultShareRegistryPresetWorkspaceHealthScore({
      store: {
        grantPresets: [],
        aliasPresets: [],
        defaultPresetId: null,
      },
      integrityReport: {
        checkedAt: "2026-04-19T04:16:00Z",
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        warningCount: 0,
        errorCount: 0,
        issues: [],
        canAutoRepair: false,
        canResetGrantScope: false,
        canResetAliasScope: false,
        notes: [],
      },
      diagnostics: {
        checkedAt: "2026-04-19T04:16:00Z",
        storageKeysPresent: {
          grantPresets: true,
          aliasPresets: false,
          defaultPresetId: false,
          lastGoodBackup: false,
          workspaceState: true,
        },
        grantPresetCount: 0,
        aliasPresetCount: 0,
        validPresetCount: 0,
        invalidPresetCount: 0,
        defaultPresetIdPresent: false,
        lastBackupPresent: false,
        workspaceStatePresent: true,
        workspaceStateWarning: null,
        latestValidationAt: "2026-04-19T04:16:00Z",
        warningCount: 0,
        errorCount: 0,
        notes: [],
      },
      lastGoodBackup: null,
      workspaceBackup: null,
      workspaceState: resetResultShareRegistryPresetWorkspaceState({
        now: "2026-04-19T04:16:00Z",
      }),
      auditSummary: buildResultShareRegistryPresetAuditSummary([]),
      workspaceImportPreview: null,
      thresholdPreferences: validation.normalizedPreferences ?? undefined,
      thresholdPreferenceSource: "local",
      checkedAt: "2026-04-19T04:16:00Z",
    });
    const preview = buildPresetWorkspaceHealthThresholdPreview({
      currentScore: currentHealth,
      draftScore: draftHealth,
    });

    expect(preview.currentScore).toBe(85);
    expect(preview.currentStatus).toBe("attention");
    expect(preview.draftStatus).toBe("healthy");
    expect(preview.statusChanged).toBe(true);
    expect(preview.summary).toMatch(/to healthy/i);
  });
});
