const SHARE_TOKEN_QUERY_KEY = "share_token";
const SELF_SERVICE_TOKEN_QUERY_KEY = "self_service_token";

export type ShareTokenSource = "path" | "query" | "fragment" | "manual" | "none";

export type ShareTokenExtractionResult = {
  shareToken: string | null;
  source: ShareTokenSource;
  cleanedSearch: string;
  cleanedHash: string;
};

export type ShareLocationTokenExtractionResult = {
  shareToken: string | null;
  shareSource: ShareTokenSource;
  selfServiceToken: string | null;
  selfServiceSource: ShareTokenSource;
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

export function extractShareTokenFromPath(pathname: string): string | null {
  const segments = pathname
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean);
  if (segments.length < 2 || segments[0] !== "share") {
    return null;
  }
  const token = decodeURIComponent(segments[1] ?? "").trim();
  return token || null;
}

export function extractShareTokenFromSearch(search: string): {
  shareToken: string | null;
  nextSearch: string;
} {
  const { token, nextValue } = extractTokenFromParams(search, SHARE_TOKEN_QUERY_KEY, "?");
  return {
    shareToken: token,
    nextSearch: nextValue,
  };
}

export function extractShareTokenFromFragment(fragment: string): {
  shareToken: string | null;
  nextFragment: string;
} {
  const { token, nextValue } = extractTokenFromParams(
    fragment,
    SHARE_TOKEN_QUERY_KEY,
    "#",
  );
  return {
    shareToken: token,
    nextFragment: nextValue,
  };
}

export function extractShareTokensFromLocation(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
): ShareLocationTokenExtractionResult {
  const pathShareToken = extractShareTokenFromPath(locationLike.pathname);
  const queryShare = extractTokenFromParams(locationLike.search, SHARE_TOKEN_QUERY_KEY, "?");
  const fragmentShare = extractTokenFromParams(locationLike.hash, SHARE_TOKEN_QUERY_KEY, "#");
  const querySelfService = extractTokenFromParams(
    queryShare.nextValue,
    SELF_SERVICE_TOKEN_QUERY_KEY,
    "?",
  );
  const fragmentSelfService = extractTokenFromParams(
    fragmentShare.nextValue,
    SELF_SERVICE_TOKEN_QUERY_KEY,
    "#",
  );

  if (pathShareToken) {
    return {
      shareToken: pathShareToken,
      shareSource: "path",
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

  if (queryShare.token) {
    return {
      shareToken: queryShare.token,
      shareSource: "query",
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

  if (fragmentShare.token) {
    return {
      shareToken: fragmentShare.token,
      shareSource: "fragment",
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
    shareToken: null,
    shareSource: "none",
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

export function extractShareTokenFromLocation(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
): ShareTokenExtractionResult {
  const extracted = extractShareTokensFromLocation(locationLike);
  return {
    shareToken: extracted.shareToken,
    source: extracted.shareSource,
    cleanedSearch: extracted.cleanedSearch,
    cleanedHash: extracted.cleanedHash,
  };
}

export function clearVisibleShareAndSelfServiceTokenHints(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): ShareLocationTokenExtractionResult {
  const extracted = extractShareTokensFromLocation(locationLike);
  if (
    extracted.shareSource !== "query" &&
    extracted.shareSource !== "fragment" &&
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

export function clearVisibleShareTokenHints(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): ShareTokenExtractionResult {
  const extracted = clearVisibleShareAndSelfServiceTokenHints(locationLike, historyLike);
  return {
    shareToken: extracted.shareToken,
    source: extracted.shareSource,
    cleanedSearch: extracted.cleanedSearch,
    cleanedHash: extracted.cleanedHash,
  };
}
