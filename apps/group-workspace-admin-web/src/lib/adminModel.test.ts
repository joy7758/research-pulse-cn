import {
  buildApiErrorViewModel,
  buildGlobalConversionOverviewViewModel,
  buildPaperLookupOptions,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
  buildWorkspaceConversionOverviewViewModel,
  buildWorkspaceListItems,
} from "./adminModel";
import type {
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  PaperProfileRead,
  UserProfileRead,
} from "./types";

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

const globalConversionOverview: GroupWorkspaceConversionOverviewRead = {
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  total_share_view_events: 4,
  bootstrap_view_count: 1,
  content_view_count: 1,
  redirect_count: 0,
  invite_handoff_redirect_count: 1,
  collect_handoff_redirect_count: 1,
  resolved_event_count: 4,
  rejected_event_count: 0,
  by_share_kind: { workspace_board: 4 },
  by_access_mode: { share_token: 2, alias: 2 },
  by_handoff_target: { group_workspace_invite_entry: 1, result_share_collect_entry: 1 },
  invite_claimed_count: 1,
  invite_already_member_count: 1,
  invite_rejected_count: 1,
  collect_collected_count: 1,
  collect_already_present_count: 1,
  collect_rejected_count: 0,
  unique_result_share_grant_count: 3,
  unique_workspace_count: 1,
  last_activity_at: "2026-04-17T08:00:00Z",
  attribution_scope: {
    direct_attribution_metrics: ["total_share_view_events", "collect_collected_count"],
    workspace_level_aggregate_metrics: ["invite_claimed_count"],
    notes: ["Invite claim metrics are workspace-level aggregate signals in v1."],
  },
};

const workspaceConversionOverview: GroupWorkspaceWorkspaceConversionOverviewRead = {
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  workspace: {
    id: workspace.id,
    slug: workspace.slug,
    name: workspace.name,
    description: workspace.description,
    status: workspace.status,
  },
  active_workspace_board_share_grant_count: 1,
  active_digest_issue_share_grant_count: 1,
  active_paper_snapshot_share_grant_count: 2,
  active_invite_grant_count: 1,
  workspace_board_view_count: 2,
  invite_handoff_redirect_count: 1,
  collect_handoff_redirect_count: 1,
  invite_claimed_count: 1,
  invite_already_member_count: 1,
  collect_collected_count: 2,
  collect_already_present_count: 1,
  unique_collected_paper_count: 3,
  unique_collecting_user_count: 1,
  last_activity_at: "2026-04-17T08:00:00Z",
  attribution_scope: {
    direct_attribution_metrics: ["workspace_board_view_count", "collect_collected_count"],
    workspace_level_aggregate_metrics: ["invite_claimed_count"],
    notes: ["Collect metrics are directly linked when result_share_grant_id is present."],
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

  it("shapes global conversion overviews for dashboard rendering", () => {
    expect(buildGlobalConversionOverviewViewModel(globalConversionOverview)).toMatchObject({
      empty: false,
      summaryMetrics: expect.arrayContaining([
        expect.objectContaining({ label: "Total share events", value: 4 }),
        expect.objectContaining({ label: "Collect collected", value: 1 }),
      ]),
      sections: expect.arrayContaining([
        expect.objectContaining({ title: "By share kind" }),
        expect.objectContaining({ title: "By access mode" }),
      ]),
      attributionScope: expect.objectContaining({
        directMetrics: expect.arrayContaining(["Total Share View Events"]),
        workspaceLevelAggregateMetrics: expect.arrayContaining(["Invite Claimed count"]),
      }),
    });
  });

  it("shapes workspace conversion overviews for dashboard rendering", () => {
    expect(buildWorkspaceConversionOverviewViewModel(workspaceConversionOverview)).toMatchObject({
      empty: false,
      workspace: expect.objectContaining({ id: "workspace-1" }),
      summaryMetrics: expect.arrayContaining([
        expect.objectContaining({ label: "Workspace-board views", value: 2 }),
        expect.objectContaining({ label: "Unique collected papers", value: 3 }),
      ]),
      sections: expect.arrayContaining([
        expect.objectContaining({ title: "Active grant inventory" }),
        expect.objectContaining({ title: "Invite and collect outcomes" }),
      ]),
    });
  });

  it("marks zeroed global overviews as empty", () => {
    expect(
      buildGlobalConversionOverviewViewModel({
        ...globalConversionOverview,
        total_share_view_events: 0,
        bootstrap_view_count: 0,
        content_view_count: 0,
        invite_handoff_redirect_count: 0,
        collect_handoff_redirect_count: 0,
        invite_claimed_count: 0,
        invite_already_member_count: 0,
        invite_rejected_count: 0,
        collect_collected_count: 0,
        collect_already_present_count: 0,
        collect_rejected_count: 0,
        by_share_kind: {},
        by_access_mode: {},
        by_handoff_target: {},
      }).empty,
    ).toBe(true);
  });
});
