const HANDOFF_TOKEN_FRAGMENT_KEY = "handoff_token";

export type HandoffTokenFragmentResult = {
  handoffToken: string | null;
  nextFragment: string;
};

export function extractHandoffTokenFromFragment(fragment: string): HandoffTokenFragmentResult {
  const rawFragment = fragment.startsWith("#") ? fragment.slice(1) : fragment;
  if (!rawFragment) {
    return {
      handoffToken: null,
      nextFragment: "",
    };
  }

  const params = new URLSearchParams(rawFragment);
  const token = params.get(HANDOFF_TOKEN_FRAGMENT_KEY)?.trim() ?? "";
  if (!token) {
    return {
      handoffToken: null,
      nextFragment: fragment.startsWith("#") ? fragment : `#${fragment}`,
    };
  }

  params.delete(HANDOFF_TOKEN_FRAGMENT_KEY);
  const nextRaw = params.toString();
  return {
    handoffToken: token,
    nextFragment: nextRaw ? `#${nextRaw}` : "",
  };
}

export function clearHandoffTokenFromVisibleUrl(
  locationLike: Pick<Location, "pathname" | "search" | "hash">,
  historyLike: Pick<History, "replaceState">,
): string | null {
  const extracted = extractHandoffTokenFromFragment(locationLike.hash);
  if (!extracted.handoffToken) {
    return null;
  }

  historyLike.replaceState(
    null,
    "",
    `${locationLike.pathname}${locationLike.search}${extracted.nextFragment}`,
  );
  return extracted.handoffToken;
}
