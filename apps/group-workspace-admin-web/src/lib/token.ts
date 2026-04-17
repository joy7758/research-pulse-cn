import type { AdminTokenSource } from "./types";

const ADMIN_BEARER_QUERY_KEY = "admin_bearer";

export type AdminTokenExtractionResult = {
  adminToken: string | null;
  source: AdminTokenSource;
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

function normalizeContainer(value: string, prefix: "?" | "#"): string {
  return value ? `${prefix}${value}` : "";
}

export function extractAdminTokenFromSearch(search: string): {
  adminToken: string | null;
  nextSearch: string;
} {
  const params = new URLSearchParams(normalizeSearchLike(search));
  const token = params.get(ADMIN_BEARER_QUERY_KEY)?.trim() ?? "";
  if (!token) {
    return {
      adminToken: null,
      nextSearch: normalizeContainer(params.toString(), "?"),
    };
  }
  params.delete(ADMIN_BEARER_QUERY_KEY);
  return {
    adminToken: token,
    nextSearch: normalizeContainer(params.toString(), "?"),
  };
}

export function extractAdminTokenFromFragment(fragment: string): {
  adminToken: string | null;
  nextFragment: string;
} {
  const params = new URLSearchParams(normalizeHashLike(fragment));
  const token = params.get(ADMIN_BEARER_QUERY_KEY)?.trim() ?? "";
  if (!token) {
    return {
      adminToken: null,
      nextFragment: normalizeContainer(params.toString(), "#"),
    };
  }
  params.delete(ADMIN_BEARER_QUERY_KEY);
  return {
    adminToken: token,
    nextFragment: normalizeContainer(params.toString(), "#"),
  };
}

export function extractAdminTokenFromLocation(
  locationLike: Pick<Location, "search" | "hash">,
): AdminTokenExtractionResult {
  const searchMatch = extractAdminTokenFromSearch(locationLike.search);
  if (searchMatch.adminToken) {
    return {
      adminToken: searchMatch.adminToken,
      source: "query",
      cleanedSearch: searchMatch.nextSearch,
      cleanedHash: extractAdminTokenFromFragment(locationLike.hash).nextFragment,
    };
  }

  const fragmentMatch = extractAdminTokenFromFragment(locationLike.hash);
  if (fragmentMatch.adminToken) {
    return {
      adminToken: fragmentMatch.adminToken,
      source: "fragment",
      cleanedSearch: extractAdminTokenFromSearch(locationLike.search).nextSearch,
      cleanedHash: fragmentMatch.nextFragment,
    };
  }

  return {
    adminToken: null,
    source: "none",
    cleanedSearch: extractAdminTokenFromSearch(locationLike.search).nextSearch,
    cleanedHash: extractAdminTokenFromFragment(locationLike.hash).nextFragment,
  };
}

export function clearVisibleAdminTokenHints(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): AdminTokenExtractionResult {
  const extracted = extractAdminTokenFromLocation(locationLike);
  if (extracted.source !== "query" && extracted.source !== "fragment") {
    return extracted;
  }
  historyLike.replaceState(
    null,
    "",
    `${locationLike.pathname}${extracted.cleanedSearch}${extracted.cleanedHash}`,
  );
  return extracted;
}
