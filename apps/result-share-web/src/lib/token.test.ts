import {
  extractShareAccessFromLocation,
  extractShareAliasFromFragment,
  extractShareAliasFromPath,
  extractShareAliasFromSearch,
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

  it("extracts a share alias from /share-alias/<alias> pathnames", () => {
    expect(extractShareAliasFromPath("/share-alias/alias-123")).toBe("alias-123");
    expect(extractShareAliasFromPath("/share/token-123")).toBeNull();
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

  it("extracts and clears alias query and fragment hints", () => {
    expect(extractShareAliasFromSearch("?share_alias=query-alias&mode=public")).toEqual({
      shareAlias: "query-alias",
      nextSearch: "?mode=public",
    });
    expect(extractShareAliasFromFragment("#share_alias=fragment-alias&view=compact")).toEqual({
      shareAlias: "fragment-alias",
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

  it("extracts alias access from path query and fragment without persisting it", () => {
    expect(
      extractShareAccessFromLocation({
        pathname: "/share-alias/path-alias",
        search: "?self_service_token=query-self-token",
        hash: "#debug=1",
      }),
    ).toMatchObject({
      shareValue: "path-alias",
      shareMode: "alias",
      shareSource: "path",
      selfServiceToken: "query-self-token",
      selfServiceSource: "query",
    });
  });

  it("clears visible alias and self-service token hints together", () => {
    const replaceState = vi.fn();

    clearVisibleShareAndSelfServiceTokenHints(
      {
        pathname: "/share-alias",
        search: "?share_alias=query-alias&self_service_token=self-token&debug=1",
        hash: "#tab=digest",
      } as Pick<Location, "pathname" | "search" | "hash">,
      { replaceState } as Pick<History, "replaceState">,
    );

    expect(replaceState).toHaveBeenCalledWith(
      null,
      "",
      "/share-alias?debug=1#tab=digest",
    );
  });
});
