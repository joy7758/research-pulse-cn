import {
  clearHandoffTokenFromVisibleUrl,
  extractHandoffTokenFromFragment,
} from "./token";

describe("handoff token fragment helpers", () => {
  it("extracts a handoff token and preserves the remaining fragment", () => {
    expect(extractHandoffTokenFromFragment("#handoff_token=abc123&mode=preview")).toEqual({
      handoffToken: "abc123",
      nextFragment: "#mode=preview",
    });
  });

  it("clears the visible URL without keeping the token in browser storage helpers", () => {
    const replaceState = vi.fn();

    const token = clearHandoffTokenFromVisibleUrl(
      {
        pathname: "/shell",
        search: "?dev=1",
        hash: "#handoff_token=from-mini&mode=editor",
      } as Pick<Location, "pathname" | "search" | "hash">,
      { replaceState } as Pick<History, "replaceState">,
    );

    expect(token).toBe("from-mini");
    expect(replaceState).toHaveBeenCalledWith(
      null,
      "",
      "/shell?dev=1#mode=editor",
    );
  });
});
