import { createGroupWorkspaceAdminApiClient } from "./apiClient";
import type { ConversionFilterInput } from "./types";

const baseFilters: ConversionFilterInput = {
  dateFrom: "2026-04-01",
  dateTo: "2026-04-17",
  shareKind: "workspace_board",
  accessMode: "alias",
  eventType: "content_view",
  outcome: "resolved",
  limit: 50,
};

function buildFetchMock() {
  return vi.fn().mockResolvedValue(
    new Response("{}", {
      status: 200,
      headers: {
        "content-type": "application/json",
      },
    }),
  );
}

describe("group workspace admin api client conversion filter queries", () => {
  it("shapes global overview filter queries", async () => {
    const fetchImpl = buildFetchMock();
    const client = createGroupWorkspaceAdminApiClient({
      apiBaseUrl: "http://127.0.0.1:8000",
      accessToken: "token",
      fetchImpl,
    });

    await client.getConversionOverview(baseFilters);

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/group-workspace-conversion-overview?date_from=2026-04-01T00%3A00%3A00.000Z&date_to=2026-04-17T23%3A59%3A59.999Z&share_kind=workspace_board&access_mode=alias&event_type=content_view&outcome=resolved",
      expect.objectContaining({
        method: "GET",
      }),
    );
  });

  it("shapes global drilldown filter queries including limit", async () => {
    const fetchImpl = buildFetchMock();
    const client = createGroupWorkspaceAdminApiClient({
      apiBaseUrl: "http://127.0.0.1:8000",
      accessToken: "token",
      fetchImpl,
    });

    await client.getConversionDrilldown(baseFilters);

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/group-workspace-conversion-drilldown?date_from=2026-04-01T00%3A00%3A00.000Z&date_to=2026-04-17T23%3A59%3A59.999Z&share_kind=workspace_board&access_mode=alias&event_type=content_view&outcome=resolved&limit=50",
      expect.objectContaining({
        method: "GET",
      }),
    );
  });

  it("shapes workspace overview filter queries", async () => {
    const fetchImpl = buildFetchMock();
    const client = createGroupWorkspaceAdminApiClient({
      apiBaseUrl: "http://127.0.0.1:8000",
      accessToken: "token",
      fetchImpl,
    });

    await client.getWorkspaceConversionOverview("workspace-1", baseFilters);

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/group-workspaces/workspace-1/conversion-overview?date_from=2026-04-01T00%3A00%3A00.000Z&date_to=2026-04-17T23%3A59%3A59.999Z&share_kind=workspace_board&access_mode=alias&event_type=content_view&outcome=resolved",
      expect.objectContaining({
        method: "GET",
      }),
    );
  });

  it("shapes workspace drilldown filter queries including limit", async () => {
    const fetchImpl = buildFetchMock();
    const client = createGroupWorkspaceAdminApiClient({
      apiBaseUrl: "http://127.0.0.1:8000",
      accessToken: "token",
      fetchImpl,
    });

    await client.getWorkspaceConversionDrilldown("workspace-1", baseFilters);

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/group-workspaces/workspace-1/conversion-drilldown?date_from=2026-04-01T00%3A00%3A00.000Z&date_to=2026-04-17T23%3A59%3A59.999Z&share_kind=workspace_board&access_mode=alias&event_type=content_view&outcome=resolved&limit=50",
      expect.objectContaining({
        method: "GET",
      }),
    );
  });
});
