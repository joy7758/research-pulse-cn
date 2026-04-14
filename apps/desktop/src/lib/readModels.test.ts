import type { PaperListItemRead } from "./types";
import {
  buildTodayEmptyState,
  deriveProgressPercentage,
  sortPapers,
} from "./readModels";

describe("desktop read model helpers", () => {
  it("uses the fixed derived progress percentage mapping", () => {
    expect(deriveProgressPercentage("published")).toBe(100);
    expect(deriveProgressPercentage("revision")).toBe(80);
    expect(deriveProgressPercentage("under_review")).toBe(65);
    expect(deriveProgressPercentage("in_prep")).toBe(35);
    expect(deriveProgressPercentage("paused")).toBe(0);
  });

  it("builds a stable today empty state", () => {
    expect(buildTodayEmptyState("No digest yet.")).toEqual({
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
      message: "No digest yet.",
      updatedAt: null,
    });
  });

  it("sorts paper list items by stable desktop ordering", () => {
    const papers: PaperListItemRead[] = [
      {
        id: "paper-b",
        userId: "user-1",
        title: "Beta Paper",
        paperType: "published",
        stage: "published",
        venue: null,
        priority: 4,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-14T00:00:00Z",
        progressPercentage: 100,
        updatedAt: "2026-04-14T00:00:00Z",
      },
      {
        id: "paper-a",
        userId: "user-1",
        title: "Alpha Paper",
        paperType: "revision",
        stage: "revision",
        venue: null,
        priority: 5,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-15T00:00:00Z",
        progressPercentage: 80,
        updatedAt: "2026-04-15T00:00:00Z",
      },
      {
        id: "paper-c",
        userId: "user-1",
        title: "Gamma Paper",
        paperType: "revision",
        stage: "revision",
        venue: null,
        priority: 5,
        nextAction: null,
        blocker: null,
        lastTouchAt: "2026-04-14T00:00:00Z",
        progressPercentage: 80,
        updatedAt: "2026-04-13T00:00:00Z",
      },
    ];

    expect(sortPapers(papers).map((paper) => paper.id)).toEqual([
      "paper-a",
      "paper-c",
      "paper-b",
    ]);
  });
});
