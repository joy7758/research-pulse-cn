import {
  clearVisibleShareAndSelfServiceTokenHints,
  clearVisibleShareTokenHints,
  extractShareTokenFromFragment,
  extractShareTokenFromLocation,
  extractShareTokenFromPath,
  extractShareTokenFromSearch,
  extractShareTokensFromLocation,
} from "./token";

describe("result share token helpers", () => {
  it("extracts a share token from /share/<token> pathnames", () => {
    expect(extractShareTokenFromPath("/share/token-123")).toBe("token-123");
    expect(extractShareTokenFromPath("/")).toBeNull();
  });

  it("extracts and clears query tokens while preserving unrelated params", () => {
    expect(extractShareTokenFromSearch("?share_token=query-token&mode=public")).toEqual({
      shareToken: "query-token",
      nextSearch: "?mode=public",
    });
  });

  it("extracts and clears fragment tokens while preserving unrelated keys", () => {
    expect(extractShareTokenFromFragment("#share_token=fragment-token&view=compact")).toEqual({
      shareToken: "fragment-token",
      nextFragment: "#view=compact",
    });
  });

  it("prefers path tokens over query and fragment fallbacks", () => {
    expect(
      extractShareTokenFromLocation({
        pathname: "/share/path-token",
        search: "?share_token=query-token",
        hash: "#share_token=fragment-token",
      }),
    ).toMatchObject({
      shareToken: "path-token",
      source: "path",
    });
  });

  it("clears visible query or fragment hints without persisting tokens", () => {
    const replaceState = vi.fn();

    const extracted = clearVisibleShareTokenHints(
      {
        pathname: "/share",
        search: "?share_token=query-token&debug=1",
        hash: "#share_token=fragment-token&tab=digest",
      } as Pick<Location, "pathname" | "search" | "hash">,
      { replaceState } as Pick<History, "replaceState">,
    );

    expect(extracted).toMatchObject({
      shareToken: "query-token",
      source: "query",
      cleanedSearch: "?debug=1",
      cleanedHash: "#tab=digest",
    });
    expect(replaceState).toHaveBeenCalledWith(
      null,
      "",
      "/share?debug=1#tab=digest",
    );
  });

  it("extracts a self-service token from query or fragment without persisting it", () => {
    expect(
      extractShareTokensFromLocation({
        pathname: "/share/path-token",
        search: "?self_service_token=query-self-token",
        hash: "#debug=1",
      }),
    ).toMatchObject({
      shareToken: "path-token",
      shareSource: "path",
      selfServiceToken: "query-self-token",
      selfServiceSource: "query",
    });
  });

  it("clears share and self-service token hints together", () => {
    const replaceState = vi.fn();

    const extracted = clearVisibleShareAndSelfServiceTokenHints(
      {
        pathname: "/share",
        search: "?share_token=query-token&self_service_token=self-token&debug=1",
        hash: "#tab=digest",
      } as Pick<Location, "pathname" | "search" | "hash">,
      { replaceState } as Pick<History, "replaceState">,
    );

    expect(extracted).toMatchObject({
      shareToken: "query-token",
      shareSource: "query",
      selfServiceToken: "self-token",
      selfServiceSource: "query",
      cleanedSearch: "?debug=1",
      cleanedHash: "#tab=digest",
    });
    expect(replaceState).toHaveBeenCalledWith(null, "", "/share?debug=1#tab=digest");
  });
});
