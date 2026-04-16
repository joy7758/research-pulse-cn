const SHARE_TOKEN_QUERY_KEY = "share_token";

export type ShareTokenSource = "path" | "query" | "fragment" | "manual" | "none";

export type ShareTokenExtractionResult = {
  shareToken: string | null;
  source: ShareTokenSource;
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
  const params = new URLSearchParams(normalizeSearchLike(search));
  const token = params.get(SHARE_TOKEN_QUERY_KEY)?.trim() ?? "";
  if (!token) {
    return {
      shareToken: null,
      nextSearch: normalizeParamContainer(params.toString(), "?"),
    };
  }
  params.delete(SHARE_TOKEN_QUERY_KEY);
  return {
    shareToken: token,
    nextSearch: normalizeParamContainer(params.toString(), "?"),
  };
}

export function extractShareTokenFromFragment(fragment: string): {
  shareToken: string | null;
  nextFragment: string;
} {
  const params = new URLSearchParams(normalizeHashLike(fragment));
  const token = params.get(SHARE_TOKEN_QUERY_KEY)?.trim() ?? "";
  if (!token) {
    return {
      shareToken: null,
      nextFragment: normalizeParamContainer(params.toString(), "#"),
    };
  }
  params.delete(SHARE_TOKEN_QUERY_KEY);
  return {
    shareToken: token,
    nextFragment: normalizeParamContainer(params.toString(), "#"),
  };
}

export function extractShareTokenFromLocation(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
): ShareTokenExtractionResult {
  const pathToken = extractShareTokenFromPath(locationLike.pathname);
  if (pathToken) {
    return {
      shareToken: pathToken,
      source: "path",
      cleanedSearch: locationLike.search,
      cleanedHash: locationLike.hash,
    };
  }

  const searchMatch = extractShareTokenFromSearch(locationLike.search);
  if (searchMatch.shareToken) {
    return {
      shareToken: searchMatch.shareToken,
      source: "query",
      cleanedSearch: searchMatch.nextSearch,
      cleanedHash: extractShareTokenFromFragment(locationLike.hash).nextFragment,
    };
  }

  const fragmentMatch = extractShareTokenFromFragment(locationLike.hash);
  if (fragmentMatch.shareToken) {
    return {
      shareToken: fragmentMatch.shareToken,
      source: "fragment",
      cleanedSearch: extractShareTokenFromSearch(locationLike.search).nextSearch,
      cleanedHash: fragmentMatch.nextFragment,
    };
  }

  return {
    shareToken: null,
    source: "none",
    cleanedSearch: extractShareTokenFromSearch(locationLike.search).nextSearch,
    cleanedHash: extractShareTokenFromFragment(locationLike.hash).nextFragment,
  };
}

export function clearVisibleShareTokenHints(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): ShareTokenExtractionResult {
  const extracted = extractShareTokenFromLocation(locationLike);
  if (
    extracted.source !== "query" &&
    extracted.source !== "fragment"
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
