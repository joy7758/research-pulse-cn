import {
  buildResultShareRegistryFilterSummaryViewModel,
  DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT,
  normalizeResultShareRegistryFilterInput,
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
      }),
    ).toMatchObject({
      hasActiveFilters: true,
      chips: expect.arrayContaining([
        expect.objectContaining({ label: "Share kind", value: "Workspace board" }),
        expect.objectContaining({ label: "Grant status", value: "Active grants" }),
        expect.objectContaining({ label: "Workspace", value: "workspace-1" }),
      ]),
      scopeNotes: expect.arrayContaining([
        "Workspace ID narrows the share-grant registry only.",
      ]),
    });
  });

  it("keeps the default registry filter state inactive", () => {
    expect(buildResultShareRegistryFilterSummaryViewModel(DEFAULT_RESULT_SHARE_REGISTRY_FILTER_INPUT)).toMatchObject({
      hasActiveFilters: false,
      chips: [],
    });
  });
});
