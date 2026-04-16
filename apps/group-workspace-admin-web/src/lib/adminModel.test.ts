import {
  buildApiErrorViewModel,
  buildPaperLookupOptions,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
  buildWorkspaceListItems,
} from "./adminModel";
import type { GroupWorkspaceBoardRead, GroupWorkspaceRead, PaperProfileRead, UserProfileRead } from "./types";

const workspace: GroupWorkspaceRead = {
  id: "workspace-1",
  slug: "materials-group",
  name: "Materials Group",
  description: "Workspace description",
  status: "active",
  created_by_admin_id: "admin-1",
  created_at: "2026-04-16T06:00:00Z",
  updated_at: "2026-04-16T06:00:00Z",
};

const board: GroupWorkspaceBoardRead = {
  workspace,
  member_count: 1,
  paper_count: 1,
  members: [
    {
      member_id: "member-1",
      user_id: "user-1",
      role: "owner",
      name: "Owner",
      email: "owner@example.com",
      joined_at: "2026-04-16T06:05:00Z",
    },
  ],
  papers: [
    {
      paper_id: "paper-1",
      user_id: "user-1",
      owner_name: "Owner",
      owner_email: "owner@example.com",
      title: "Shared Paper",
      type: "published",
      stage: "published",
      venue: "JOM",
      priority: 4,
      next_action: "Review delta",
      blocker: null,
      last_touch_at: "2026-04-16T05:00:00Z",
      progress_percentage: 100,
      latest_signal_summary: null,
    },
  ],
  quick_stats: {
    member_count: 1,
    paper_count: 1,
    blocked_paper_count: 0,
    papers_with_signals_count: 0,
  },
};

describe("group workspace admin model helpers", () => {
  it("shapes workspace list items with cached board counts", () => {
    expect(buildWorkspaceListItems([workspace], { [workspace.id]: board })).toEqual([
      {
        id: "workspace-1",
        slug: "materials-group",
        name: "Materials Group",
        description: "Workspace description",
        status: "active",
        memberCount: 1,
        paperCount: 1,
      },
    ]);
  });

  it("shapes workspace boards for rendering", () => {
    expect(buildWorkspaceBoardViewModel(board)).toMatchObject({
      workspaceId: "workspace-1",
      title: "Materials Group",
      memberCount: 1,
      paperCount: 1,
    });
  });

  it("builds one-time share token display models", () => {
    expect(
      buildShareGrantIssueViewModel({
        grant: {
          id: "grant-1",
          share_kind: "workspace_board",
          workspace_id: "workspace-1",
          digest_issue_id: null,
          paper_id: null,
          status: "active",
          display_label: "Board share",
          issued_by_admin_id: "admin-1",
          expires_at: null,
          last_used_at: null,
          created_at: "2026-04-16T06:10:00Z",
          updated_at: "2026-04-16T06:10:00Z",
        },
        plain_text_token: "share-token-once",
        expires_at: null,
      }),
    ).toMatchObject({
      grantId: "grant-1",
      plainTextToken: "share-token-once",
    });
  });

  it("builds user and paper lookup options", () => {
    const users: UserProfileRead[] = [
      {
        id: "user-1",
        name: "Owner",
        email: "owner@example.com",
        field: "Materials",
        interests: [],
        watched_topics: [],
        watched_venues: [],
        reminder_preferences: {},
        risk_thresholds: {},
        created_at: "2026-04-16T06:00:00Z",
        updated_at: "2026-04-16T06:00:00Z",
      },
    ];
    const papers: PaperProfileRead[] = [
      {
        id: "paper-1",
        user_id: "user-1",
        title: "Shared Paper",
        title_zh: null,
        title_en: null,
        type: "published",
        stage: "published",
        venue: "JOM",
        identifiers: {},
        source_links: [],
        last_touch_at: null,
        next_action: null,
        blocker: null,
        priority: 4,
        created_at: "2026-04-16T06:00:00Z",
        updated_at: "2026-04-16T06:00:00Z",
        progress_events: [],
        signal_snapshots: [],
      },
    ];
    expect(buildUserLookupOptions(users)[0].label).toContain("owner@example.com");
    expect(buildPaperLookupOptions(papers)[0].label).toBe("Shared Paper");
  });

  it("maps conflict errors into UI copy", () => {
    expect(
      buildApiErrorViewModel({
        kind: "conflict",
        detail: "group workspace paper already exists",
      }),
    ).toEqual({
      kind: "conflict",
      title: "Conflict",
      message: "group workspace paper already exists",
    });
  });
});
