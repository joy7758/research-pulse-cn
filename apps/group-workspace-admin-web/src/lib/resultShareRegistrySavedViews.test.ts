import { DEFAULT_CONVERSION_FILTER_INPUT } from "./conversionFilters";
import {
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
} from "./resultShareRegistryFilters";
import {
  applyResultShareRegistryPresetImport,
  applyResultShareRegistrySavedView,
  buildResultShareRegistryPresetExport,
  buildInitialResultShareRegistrySavedViewState,
  buildResultShareRegistrySavedViewDraft,
  createResultShareRegistrySavedView,
  deleteResultShareRegistrySavedView,
  loadResultShareRegistrySavedViewStore,
  overwriteResultShareRegistrySavedView,
  parseResultShareRegistryPresetImport,
  persistResultShareRegistrySavedViewStore,
  RESULT_SHARE_REGISTRY_PRESET_EXPORT_SCHEMA_VERSION,
  saveResultShareRegistrySavedView,
  setResultShareRegistryDefaultPresetId,
} from "./resultShareRegistrySavedViews";

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
});
