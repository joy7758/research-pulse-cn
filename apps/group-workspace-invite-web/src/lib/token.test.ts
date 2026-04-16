import {
  clearVisibleInviteTokenHints,
  extractInviteTokenFromPath,
  extractInviteTokensFromLocation,
} from "./token";

describe("group workspace invite token helpers", () => {
  it("extracts an invite token from /invite/<token> pathnames", () => {
    expect(extractInviteTokenFromPath("/invite/token-123")).toBe("token-123");
    expect(extractInviteTokenFromPath("/")).toBeNull();
  });

  it("extracts and clears query invite and self-service tokens while preserving unrelated params", () => {
    expect(
      extractInviteTokensFromLocation({
        pathname: "/",
        search: "?invite_token=invite-1&self_service_token=grant-1&mode=public",
        hash: "",
      }),
    ).toMatchObject({
      inviteToken: "invite-1",
      inviteSource: "query",
      selfServiceToken: "grant-1",
      selfServiceSource: "query",
      cleanedSearch: "?mode=public",
      cleanedHash: "",
    });
  });

  it("extracts fragment fallback tokens and preserves unrelated hash params", () => {
    expect(
      extractInviteTokensFromLocation({
        pathname: "/",
        search: "?mode=local",
        hash: "#invite_token=invite-2&self_service_token=grant-2&tab=preview",
      }),
    ).toMatchObject({
      inviteToken: "invite-2",
      inviteSource: "fragment",
      selfServiceToken: "grant-2",
      selfServiceSource: "fragment",
      cleanedSearch: "?mode=local",
      cleanedHash: "#tab=preview",
    });
  });

  it("prefers path invite tokens while still extracting self-service hints from query or fragment", () => {
    expect(
      extractInviteTokensFromLocation({
        pathname: "/invite/path-token",
        search: "?self_service_token=query-grant",
        hash: "#self_service_token=fragment-grant",
      }),
    ).toMatchObject({
      inviteToken: "path-token",
      inviteSource: "path",
      selfServiceToken: "query-grant",
      selfServiceSource: "query",
    });
  });

  it("clears visible query or fragment hints without persisting tokens", () => {
    const replaceState = vi.fn();

    const extracted = clearVisibleInviteTokenHints(
      {
        pathname: "/invite",
        search: "?invite_token=query-invite&debug=1",
        hash: "#self_service_token=fragment-grant&tab=claim",
      } as Pick<Location, "pathname" | "search" | "hash">,
      { replaceState } as Pick<History, "replaceState">,
    );

    expect(extracted).toMatchObject({
      inviteToken: "query-invite",
      inviteSource: "query",
      selfServiceToken: "fragment-grant",
      selfServiceSource: "fragment",
      cleanedSearch: "?debug=1",
      cleanedHash: "#tab=claim",
    });
    expect(replaceState).toHaveBeenCalledWith(null, "", "/invite?debug=1#tab=claim");
  });
});
