import {
  buildResultShareRegistryFilterSummaryViewModel,
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
  formatResultShareRegistrySectionSortLabel,
  normalizeResultShareRegistryFilterInput,
  normalizeResultShareRegistrySortInput,
  parseResultShareRegistrySectionSortInput,
  serializeResultShareRegistrySectionSortInput,
} from "./resultShareRegistryFilters";

describe("result share registry filters", () => {
  it("normalizes registry filter inputs", () => {
    expect(
      normalizeResultShareRegistryFilterInput({
        shareKind: "workspace_board",
        grantStatus: "active",
        aliasStatus: "revoked",
        workspaceId: " workspace-1 ",
        resultShareGrantId: " grant-1 ",
      }),
    ).toEqual({
      shareKind: "workspace_board",
      grantStatus: "active",
      aliasStatus: "revoked",
      workspaceId: "workspace-1",
      resultShareGrantId: "grant-1",
    });
  });

  it("builds registry filter summary chips and notes", () => {
    expect(
      buildResultShareRegistryFilterSummaryViewModel({
        shareKind: "workspace_board",
        grantStatus: "active",
        aliasStatus: null,
        workspaceId: "workspace-1",
        resultShareGrantId: null,
      }, DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT),
    ).toMatchObject({
      hasActiveFilters: true,
      chips: expect.arrayContaining([
        expect.objectContaining({ label: "Share kind", value: "Workspace board" }),
        expect.objectContaining({ label: "Grant status", value: "Active grants" }),
        expect.objectContaining({ label: "Grant workspace", value: "workspace-1" }),
        expect.objectContaining({ label: "Grant sort", value: "Last used, newest first" }),
      ]),
      scopeNotes: expect.arrayContaining([
        "Workspace ID narrows the share-grant registry only.",
      ]),
    });
  });

  it("normalizes, serializes, and labels registry sort inputs", () => {
    const normalized = normalizeResultShareRegistrySortInput({
      grants: {
        field: "createdAt",
        direction: "asc",
      },
    });

    expect(normalized).toEqual({
      grants: {
        field: "createdAt",
        direction: "asc",
      },
      aliases: DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT.aliases,
    });
    expect(
      serializeResultShareRegistrySectionSortInput({
        field: "createdAt",
        direction: "asc",
      }),
    ).toBe("createdAt_asc");
    expect(parseResultShareRegistrySectionSortInput("status_desc")).toEqual({
      field: "status",
      direction: "desc",
    });
    expect(
      formatResultShareRegistrySectionSortLabel({
        field: "expiresAt",
        direction: "asc",
      }),
    ).toBe("Expires, soonest first");
  });

  it("keeps the default registry filter state inactive", () => {
    expect(
      buildResultShareRegistryFilterSummaryViewModel(
        DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
        DEFAULT_RESULT_SHARE_REGISTRY_SORT_INPUT,
      ),
    ).toMatchObject({
      hasActiveFilters: false,
      chips: expect.arrayContaining([
        expect.objectContaining({ label: "Grant sort" }),
        expect.objectContaining({ label: "Alias sort" }),
      ]),
    });
  });
});
