import type { PaperListItemRead, TodayOverviewRead } from "./types";

export const progressPercentageByPaperType = {
  published: 100,
  revision: 80,
  under_review: 65,
  in_prep: 35,
  paused: 0,
} as const;

export type KnownPaperType = keyof typeof progressPercentageByPaperType;

export function deriveProgressPercentage(paperType: string): number {
  return progressPercentageByPaperType[paperType as KnownPaperType] ?? 0;
}

export function buildTodayEmptyState(message?: string): TodayOverviewRead {
  return {
    state: "empty",
    issueId: null,
    issueDate: null,
    status: null,
    title: null,
    summary: null,
    highlightCount: 0,
    selectedCardCount: 0,
    deepLinkPath: null,
    highlights: [],
    message: message ?? "No digest issue is cached yet.",
    updatedAt: null,
  };
}

export function sortPapers(papers: PaperListItemRead[]): PaperListItemRead[] {
  return [...papers].sort((left, right) => {
    if (left.priority !== right.priority) {
      return right.priority - left.priority;
    }
    if ((left.lastTouchAt ?? "") !== (right.lastTouchAt ?? "")) {
      return (right.lastTouchAt ?? "").localeCompare(left.lastTouchAt ?? "");
    }
    if ((left.updatedAt ?? "") !== (right.updatedAt ?? "")) {
      return (right.updatedAt ?? "").localeCompare(left.updatedAt ?? "");
    }
    const titleOrder = left.title.localeCompare(right.title);
    if (titleOrder !== 0) {
      return titleOrder;
    }
    return left.id.localeCompare(right.id);
  });
}

export function extractQuietHoursDraft(quietHours: Record<string, unknown> | null) {
  return {
    start:
      quietHours && typeof quietHours.start === "string" ? quietHours.start : "",
    end: quietHours && typeof quietHours.end === "string" ? quietHours.end : "",
  };
}

export function buildQuietHoursPatch(
  currentQuietHours: Record<string, unknown> | null,
  start: string,
  end: string,
) {
  const nextStart = start.trim();
  const nextEnd = end.trim();
  if (!nextStart && !nextEnd) {
    return null;
  }
  return {
    ...(currentQuietHours ?? {}),
    start: nextStart,
    end: nextEnd,
  };
}
