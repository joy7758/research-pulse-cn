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
  buildResultShareRegistryPresetAuditSummary,
  buildResultShareRegistryPresetExport,
  buildInitialResultShareRegistrySavedViewState,
  buildResultShareRegistrySavedViewDraft,
  clearResultShareRegistryPresetAuditEvents,
  createPresetAuditEvent,
  createResultShareRegistryPresetBackup,
  createResultShareRegistrySavedView,
  deleteResultShareRegistrySavedView,
  inspectResultShareRegistryPresetStorage,
  loadResultShareRegistryPresetAuditEvents,
  loadResultShareRegistrySavedViewStore,
  overwriteResultShareRegistrySavedView,
  parseResultShareRegistryPresetImport,
  persistResultShareRegistrySavedViewStore,
  persistResultShareRegistryPresetBackup,
  redactUnsafeImportIssueDetails,
  restoreResultShareRegistryPresetBackup,
  RESULT_SHARE_REGISTRY_ALIAS_PRESETS_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_DEFAULT_PRESET_ID_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_GRANT_PRESETS_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_LAST_GOOD_BACKUP_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_LOCAL_AUDIT_STORAGE_KEY,
  RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
  saveResultShareRegistryPresetAuditEvents,
  saveResultShareRegistrySavedView,
  setResultShareRegistryDefaultPresetId,
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
});
