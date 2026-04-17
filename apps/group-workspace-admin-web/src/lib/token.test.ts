import {
  clearVisibleAdminTokenHints,
  extractAdminTokenFromFragment,
  extractAdminTokenFromLocation,
  extractAdminTokenFromSearch,
} from "./token";

describe("group workspace admin token helpers", () => {
  it("extracts a token from the query string", () => {
    expect(extractAdminTokenFromSearch("?admin_bearer=query-token&mode=dev")).toEqual({
      adminToken: "query-token",
      nextSearch: "?mode=dev",
    });
  });

  it("extracts a token from the hash fragment", () => {
    expect(extractAdminTokenFromFragment("#admin_bearer=fragment-token&view=list")).toEqual({
      adminToken: "fragment-token",
      nextFragment: "#view=list",
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
        hash: "#admin_bearer=fragment-token&mode=dev",
      },
      historyLike,
    );
    expect(result.adminToken).toBe("fragment-token");
    expect(historyLike.replaceState).toHaveBeenCalledWith(null, "", "/#mode=dev");
  });
});
