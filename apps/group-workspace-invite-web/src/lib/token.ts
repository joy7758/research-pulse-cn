const INVITE_TOKEN_QUERY_KEY = "invite_token";
const SELF_SERVICE_TOKEN_QUERY_KEY = "self_service_token";

export type TokenSource = "path" | "query" | "fragment" | "manual" | "none";

export type InviteLocationTokenExtractionResult = {
  inviteToken: string | null;
  inviteSource: TokenSource;
  selfServiceToken: string | null;
  selfServiceSource: TokenSource;
  cleanedSearch: string;
  cleanedHash: string;
};

function normalizeSearchLike(value: string): string {
  if (!value) {
    return "";
  }
  return value.startsWith("?") ? value.slice(1) : value;
}

function normalizeHashLike(value: string): string {
  if (!value) {
    return "";
  }
  return value.startsWith("#") ? value.slice(1) : value;
}

function normalizeParamContainer(value: string, prefix: "?" | "#"): string {
  return value ? `${prefix}${value}` : "";
}

function extractTokenFromParams(
  value: string,
  key: string,
  prefix: "?" | "#",
): { token: string | null; nextValue: string } {
  const params = new URLSearchParams(
    prefix === "?" ? normalizeSearchLike(value) : normalizeHashLike(value),
  );
  const token = params.get(key)?.trim() ?? "";
  if (!token) {
    return {
      token: null,
      nextValue: normalizeParamContainer(params.toString(), prefix),
    };
  }
  params.delete(key);
  return {
    token,
    nextValue: normalizeParamContainer(params.toString(), prefix),
  };
}

export function extractInviteTokenFromPath(pathname: string): string | null {
  const segments = pathname
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean);
  if (segments.length < 2 || segments[0] !== "invite") {
    return null;
  }
  const token = decodeURIComponent(segments[1] ?? "").trim();
  return token || null;
}

export function extractInviteTokensFromLocation(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
): InviteLocationTokenExtractionResult {
  const pathInviteToken = extractInviteTokenFromPath(locationLike.pathname);
  const queryInvite = extractTokenFromParams(
    locationLike.search,
    INVITE_TOKEN_QUERY_KEY,
    "?",
  );
  const fragmentInvite = extractTokenFromParams(
    locationLike.hash,
    INVITE_TOKEN_QUERY_KEY,
    "#",
  );
  const querySelfService = extractTokenFromParams(
    queryInvite.nextValue,
    SELF_SERVICE_TOKEN_QUERY_KEY,
    "?",
  );
  const fragmentSelfService = extractTokenFromParams(
    fragmentInvite.nextValue,
    SELF_SERVICE_TOKEN_QUERY_KEY,
    "#",
  );

  if (pathInviteToken) {
    return {
      inviteToken: pathInviteToken,
      inviteSource: "path",
      selfServiceToken: querySelfService.token ?? fragmentSelfService.token,
      selfServiceSource: querySelfService.token
        ? "query"
        : fragmentSelfService.token
          ? "fragment"
          : "none",
      cleanedSearch: querySelfService.nextValue,
      cleanedHash: fragmentSelfService.nextValue,
    };
  }

  if (queryInvite.token) {
    return {
      inviteToken: queryInvite.token,
      inviteSource: "query",
      selfServiceToken: querySelfService.token ?? fragmentSelfService.token,
      selfServiceSource: querySelfService.token
        ? "query"
        : fragmentSelfService.token
          ? "fragment"
          : "none",
      cleanedSearch: querySelfService.nextValue,
      cleanedHash: fragmentSelfService.nextValue,
    };
  }

  if (fragmentInvite.token) {
    return {
      inviteToken: fragmentInvite.token,
      inviteSource: "fragment",
      selfServiceToken: querySelfService.token ?? fragmentSelfService.token,
      selfServiceSource: querySelfService.token
        ? "query"
        : fragmentSelfService.token
          ? "fragment"
          : "none",
      cleanedSearch: querySelfService.nextValue,
      cleanedHash: fragmentSelfService.nextValue,
    };
  }

  return {
    inviteToken: null,
    inviteSource: "none",
    selfServiceToken: querySelfService.token ?? fragmentSelfService.token,
    selfServiceSource: querySelfService.token
      ? "query"
      : fragmentSelfService.token
        ? "fragment"
        : "none",
    cleanedSearch: querySelfService.nextValue,
    cleanedHash: fragmentSelfService.nextValue,
  };
}

export function clearVisibleInviteTokenHints(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): InviteLocationTokenExtractionResult {
  const extracted = extractInviteTokensFromLocation(locationLike);
  if (
    extracted.inviteSource !== "query" &&
    extracted.inviteSource !== "fragment" &&
    extracted.selfServiceSource !== "query" &&
    extracted.selfServiceSource !== "fragment"
  ) {
    return extracted;
  }
  historyLike.replaceState(
    null,
    "",
    `${locationLike.pathname}${extracted.cleanedSearch}${extracted.cleanedHash}`,
  );
  return extracted;
}
