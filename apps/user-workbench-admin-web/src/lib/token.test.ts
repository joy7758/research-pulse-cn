import {
  clearVisibleAdminTokenHints,
  extractAdminTokenFromFragment,
  extractAdminTokenFromLocation,
  extractAdminTokenFromSearch,
} from "./token";

describe("user workbench admin token helpers", () => {
  it("extracts a token from the query string", () => {
    expect(extractAdminTokenFromSearch("?admin_bearer=query-token&view=users")).toEqual({
      adminToken: "query-token",
      nextSearch: "?view=users",
    });
  });

  it("extracts a token from the hash fragment", () => {
    expect(extractAdminTokenFromFragment("#admin_bearer=fragment-token&paper_id=paper-1")).toEqual({
      adminToken: "fragment-token",
      nextFragment: "#paper_id=paper-1",
    });
  });

  it("extracts from location and prefers query over fragment", () => {
    expect(
      extractAdminTokenFromLocation({
        search: "?admin_bearer=query-token",
        hash: "#admin_bearer=fragment-token",
      }),
    ).toEqual({
      adminToken: "query-token",
      source: "query",
      cleanedSearch: "",
      cleanedHash: "",
    });
  });

  it("clears a visible token hint from the browser URL", () => {
    const historyLike = {
      replaceState: vi.fn(),
    };
    const result = clearVisibleAdminTokenHints(
      {
        pathname: "/",
        search: "",
        hash: "#admin_bearer=fragment-token&view=watch-profiles",
      },
      historyLike,
    );
    expect(result.adminToken).toBe("fragment-token");
    expect(historyLike.replaceState).toHaveBeenCalledWith(null, "", "/#view=watch-profiles");
  });
});
