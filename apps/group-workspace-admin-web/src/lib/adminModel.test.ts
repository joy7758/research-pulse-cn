import {
  buildApiErrorViewModel,
  buildGlobalConversionDrilldownViewModel,
  buildGlobalConversionOverviewViewModel,
  buildPaperLookupOptions,
  buildResultShareAliasDrilldownViewModel,
  buildResultShareGrantDrilldownViewModel,
  buildResultShareRegistryViewModel,
  buildShareGrantIssueViewModel,
  buildUserLookupOptions,
  buildWorkspaceBoardViewModel,
  buildWorkspaceConversionDrilldownViewModel,
  buildWorkspaceConversionOverviewViewModel,
  buildWorkspaceListItems,
} from "./adminModel";
import type {
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionDrilldownRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionDrilldownRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  PaperProfileRead,
  ResultShareAliasRead,
  ResultShareAliasConversionDrilldownRead,
  ResultShareGrantConversionDrilldownRead,
  ResultShareGrantRead,
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

const globalConversionDrilldown: GroupWorkspaceConversionDrilldownRead = {
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  daily_buckets: [
    {
      day: "2026-04-16",
      share_view_count: 3,
      invite_handoff_redirect_count: 1,
      collect_handoff_redirect_count: 1,
      invite_claimed_count: 1,
      invite_already_member_count: 0,
      collect_collected_count: 1,
      collect_already_present_count: 0,
    },
    {
      day: "2026-04-17",
      share_view_count: 1,
      invite_handoff_redirect_count: 0,
      collect_handoff_redirect_count: 1,
      invite_claimed_count: 0,
      invite_already_member_count: 1,
      collect_collected_count: 1,
      collect_already_present_count: 1,
    },
  ],
  top_workspaces: [
    {
      workspace: {
        id: workspace.id,
        slug: workspace.slug,
        name: workspace.name,
        description: workspace.description,
        status: workspace.status,
      },
      workspace_board_view_count: 3,
      invite_handoff_redirect_count: 1,
      collect_handoff_redirect_count: 2,
      invite_claimed_count: 1,
      collect_collected_count: 2,
      last_activity_at: "2026-04-17T08:00:00Z",
    },
  ],
  top_result_share_grants: [
    {
      result_share_grant_id: "grant-1",
      share_kind: "workspace_board",
      bootstrap_view_count: 1,
      content_view_count: 2,
      invite_handoff_redirect_count: 1,
      collect_handoff_redirect_count: 1,
      collect_collected_count: 1,
      last_activity_at: "2026-04-17T07:00:00Z",
    },
  ],
  recent_share_events: [
    {
      id: "share-event-1",
      result_share_grant_id: "grant-1",
      result_share_alias_id: null,
      share_kind: "workspace_board",
      access_mode: "alias_redirect",
      event_type: "content_view",
      outcome: "resolved",
      handoff_target_kind: "result_share_collect_entry",
      occurred_at: "2026-04-17T07:00:00Z",
    },
  ],
  recent_invite_claims: [
    {
      id: "invite-claim-1",
      invite_grant_id: "invite-grant-1",
      workspace_id: workspace.id,
      user_id: "user-1",
      claim_status: "claimed",
      role_assigned: "viewer",
      claimed_at: "2026-04-17T06:30:00Z",
      reason_codes: [],
    },
  ],
  recent_collect_records: [
    {
      id: "collect-record-1",
      workspace_id: workspace.id,
      user_id: "user-1",
      result_share_grant_id: "grant-1",
      share_kind: "paper_snapshot",
      collected_paper_id: "paper-1",
      status: "collected",
      reason_codes: [],
      created_at: "2026-04-17T06:45:00Z",
    },
  ],
  attribution_scope: {
    direct_attribution_metrics: ["share_view_count", "collect_collected_count"],
    workspace_level_aggregate_metrics: ["invite_claimed_count"],
    notes: ["Invite claims remain workspace-level aggregate-only signals in v1."],
  },
  notes: ["Result-share grant rankings are read-only operator summaries."],
};

const workspaceConversionDrilldown: GroupWorkspaceWorkspaceConversionDrilldownRead = {
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  workspace: {
    id: workspace.id,
    slug: workspace.slug,
    name: workspace.name,
    description: workspace.description,
    status: workspace.status,
  },
  daily_buckets: globalConversionDrilldown.daily_buckets,
  recent_share_events: globalConversionDrilldown.recent_share_events,
  recent_invite_claims: globalConversionDrilldown.recent_invite_claims,
  recent_collect_records: globalConversionDrilldown.recent_collect_records,
  active_share_grant_snapshot: {
    active_workspace_board_share_grant_count: 1,
    active_digest_issue_share_grant_count: 1,
    active_paper_snapshot_share_grant_count: 2,
  },
  active_invite_grant_snapshot: {
    active_invite_grant_count: 1,
  },
  attribution_scope: {
    direct_attribution_metrics: ["share_view_count", "collect_collected_count"],
    workspace_level_aggregate_metrics: ["invite_claimed_count"],
    notes: ["Invite claims stay explicitly separate from direct per-share attribution."],
  },
  notes: ["Active share-grant inventory is a snapshot, not a time-series count."],
};

const resultShareGrants: ResultShareGrantRead[] = [
  {
    id: "grant-1",
    share_kind: "workspace_board",
    workspace_id: "workspace-1",
    digest_issue_id: null,
    paper_id: null,
    status: "active",
    display_label: "Board share",
    issued_by_admin_id: "admin-1",
    expires_at: null,
    last_used_at: "2026-04-17T08:00:00Z",
    created_at: "2026-04-16T06:10:00Z",
    updated_at: "2026-04-16T06:10:00Z",
  },
  {
    id: "grant-2",
    share_kind: "digest_issue",
    workspace_id: null,
    digest_issue_id: "digest-1",
    paper_id: null,
    status: "revoked",
    display_label: null,
    issued_by_admin_id: "admin-1",
    expires_at: null,
    last_used_at: null,
    created_at: "2026-04-15T06:10:00Z",
    updated_at: "2026-04-15T06:10:00Z",
  },
];

const resultShareAliases: ResultShareAliasRead[] = [
  {
    id: "alias-1",
    result_share_grant_id: "grant-1",
    share_kind: "workspace_board",
    status: "active",
    display_label: "Board alias",
    alias_prefix: "abc123",
    expires_at: null,
    last_used_at: "2026-04-17T08:00:00Z",
    created_at: "2026-04-16T06:11:00Z",
    updated_at: "2026-04-16T06:11:00Z",
  },
  {
    id: "alias-2",
    result_share_grant_id: "grant-missing",
    share_kind: "paper_snapshot",
    status: "expired",
    display_label: null,
    alias_prefix: "snap99",
    expires_at: "2026-04-17T00:00:00Z",
    last_used_at: null,
    created_at: "2026-04-16T07:11:00Z",
    updated_at: "2026-04-16T07:11:00Z",
  },
];

const resultShareGrantDrilldown: ResultShareGrantConversionDrilldownRead = {
  share_grant: {
    grant_id: "grant-1",
    share_kind: "workspace_board",
    workspace_id: "workspace-1",
    digest_issue_id: null,
    paper_id: null,
    status: "active",
    display_label: "Board share",
    expires_at: null,
    last_used_at: "2026-04-17T08:00:00Z",
    created_at: "2026-04-16T06:10:00Z",
  },
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  total_events: 5,
  bootstrap_view_count: 2,
  content_view_count: 2,
  redirect_count: 1,
  invite_handoff_redirect_count: 0,
  collect_handoff_redirect_count: 1,
  resolved_event_count: 5,
  rejected_event_count: 0,
  by_access_mode: {
    share_token: 2,
    alias: 2,
    alias_redirect: 1,
  },
  by_event_type: {
    bootstrap_view: 2,
    content_view: 2,
    redirect: 1,
  },
  by_outcome: {
    resolved: 5,
  },
  active_alias_count: 1,
  aliases: [
    {
      alias_id: "alias-1",
      result_share_grant_id: "grant-1",
      share_kind: "workspace_board",
      alias_prefix: "abc123",
      status: "active",
      display_label: "Board alias",
      expires_at: null,
      last_used_at: "2026-04-17T08:00:00Z",
      created_at: "2026-04-16T06:11:00Z",
    },
  ],
  recent_events: [
    {
      id: "event-1",
      result_share_grant_id: "grant-1",
      result_share_alias_id: "alias-1",
      share_kind: "workspace_board",
      access_mode: "alias",
      event_type: "content_view",
      outcome: "resolved",
      handoff_target_kind: "result_share_collect_entry",
      occurred_at: "2026-04-17T08:00:00Z",
    },
  ],
  direct_collect_records: [
    {
      id: "collect-1",
      workspace_id: "workspace-1",
      user_id: "user-1",
      result_share_grant_id: "grant-1",
      share_kind: "workspace_board",
      collected_paper_id: "paper-1",
      status: "collected",
      reason_codes: [],
      created_at: "2026-04-17T08:10:00Z",
    },
  ],
  direct_collect_collected_count: 1,
  direct_collect_already_present_count: 0,
  direct_collect_rejected_count: 0,
  unique_collecting_user_count: 1,
  last_activity_at: "2026-04-17T08:10:00Z",
  attribution_scope: {
    direct_event_metrics: ["total_events", "by_access_mode", "recent_events"],
    direct_collect_metrics: ["direct_collect_records", "direct_collect_collected_count"],
    non_attribution_fields: ["share_grant", "aliases", "notes"],
    notes: ["Collect linkage remains direct only when result_share_grant_id is present."],
  },
  notes: ["Safe read model excludes plaintext tokens and aliases."],
};

const resultShareAliasDrilldown: ResultShareAliasConversionDrilldownRead = {
  alias: {
    alias_id: "alias-1",
    result_share_grant_id: "grant-1",
    share_kind: "workspace_board",
    alias_prefix: "abc123",
    status: "active",
    display_label: "Board alias",
    expires_at: null,
    last_used_at: "2026-04-17T08:00:00Z",
    created_at: "2026-04-16T06:11:00Z",
  },
  result_share_grant: resultShareGrantDrilldown.share_grant,
  window_start: "2026-03-18T00:00:00Z",
  window_end: null,
  total_events: 3,
  bootstrap_view_count: 1,
  content_view_count: 1,
  redirect_count: 1,
  invite_handoff_redirect_count: 0,
  collect_handoff_redirect_count: 1,
  resolved_event_count: 3,
  rejected_event_count: 0,
  by_event_type: {
    bootstrap_view: 1,
    content_view: 1,
    redirect: 1,
  },
  by_outcome: {
    resolved: 3,
  },
  recent_events: resultShareGrantDrilldown.recent_events,
  last_activity_at: "2026-04-17T08:00:00Z",
  attribution_scope: {
    direct_event_metrics: ["total_events", "recent_events"],
    direct_collect_metrics: [],
    non_attribution_fields: ["alias", "result_share_grant", "notes"],
    notes: ["Alias drilldown is access-path scoped only."],
  },
  notes: ["Collect linkage remains grant-level unless alias-linked persistence exists."],
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

  it("shapes global conversion drilldowns for dashboard rendering", () => {
    expect(buildGlobalConversionDrilldownViewModel(globalConversionDrilldown)).toMatchObject({
      empty: false,
      summaryMetrics: expect.arrayContaining([
        expect.objectContaining({ label: "Share views", value: 4 }),
        expect.objectContaining({ label: "Collect collected", value: 2 }),
      ]),
      dailyBuckets: expect.arrayContaining([
        expect.objectContaining({
          day: "2026-04-16",
          metrics: expect.arrayContaining([
            expect.objectContaining({ label: "Share views", count: 3 }),
          ]),
        }),
      ]),
      topWorkspaces: expect.arrayContaining([
        expect.objectContaining({
          workspaceId: "workspace-1",
          metrics: expect.arrayContaining([
            expect.objectContaining({ label: "Workspace-board views", count: 3 }),
          ]),
        }),
      ]),
      recentShareEvents: expect.arrayContaining([
        expect.objectContaining({
          title: "Content View · Workspace Board",
          subtitle: "Alias Redirect · Resolved",
        }),
      ]),
      attributionScope: expect.objectContaining({
        directMetrics: expect.arrayContaining(["Share View count", "Collect Collected count"]),
      }),
      notes: ["Result-share grant rankings are read-only operator summaries."],
    });
  });

  it("shapes workspace conversion drilldowns for dashboard rendering", () => {
    expect(buildWorkspaceConversionDrilldownViewModel(workspaceConversionDrilldown)).toMatchObject({
      empty: false,
      workspace: expect.objectContaining({ id: "workspace-1" }),
      summaryMetrics: expect.arrayContaining([
        expect.objectContaining({ label: "Active share grants", value: 4 }),
        expect.objectContaining({ label: "Recent activity rows", value: 3 }),
      ]),
      activeShareGrantSnapshotRows: expect.arrayContaining([
        expect.objectContaining({ label: "Workspace-board shares", count: 1 }),
        expect.objectContaining({ label: "Paper-snapshot shares", count: 2 }),
      ]),
      recentInviteClaims: expect.arrayContaining([
        expect.objectContaining({
          title: "Claimed invite claim",
          detailRows: expect.arrayContaining([
            expect.objectContaining({ label: "Role assigned", value: "Viewer" }),
          ]),
        }),
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

  it("marks zeroed workspace drilldowns as empty", () => {
    expect(
      buildWorkspaceConversionDrilldownViewModel({
        ...workspaceConversionDrilldown,
        daily_buckets: [
          {
            day: "2026-04-17",
            share_view_count: 0,
            invite_handoff_redirect_count: 0,
            collect_handoff_redirect_count: 0,
            invite_claimed_count: 0,
            invite_already_member_count: 0,
            collect_collected_count: 0,
            collect_already_present_count: 0,
          },
        ],
        recent_share_events: [],
        recent_invite_claims: [],
        recent_collect_records: [],
        active_share_grant_snapshot: {
          active_workspace_board_share_grant_count: 0,
          active_digest_issue_share_grant_count: 0,
          active_paper_snapshot_share_grant_count: 0,
        },
        active_invite_grant_snapshot: {
          active_invite_grant_count: 0,
        },
      }).empty,
    ).toBe(true);
  });

  it("shapes share grant drilldowns for dashboard rendering", () => {
    expect(buildResultShareGrantDrilldownViewModel(resultShareGrantDrilldown)).toMatchObject({
      empty: false,
      shareGrant: expect.objectContaining({
        grantId: "grant-1",
        title: "Board share",
      }),
      summaryMetrics: expect.arrayContaining([
        expect.objectContaining({ label: "Total events", value: 5 }),
        expect.objectContaining({ label: "Collect collected", value: 1 }),
      ]),
      byAccessModeRows: expect.arrayContaining([
        expect.objectContaining({ label: "Alias", count: 2 }),
      ]),
      aliases: expect.arrayContaining([
        expect.objectContaining({ aliasId: "alias-1", title: "Board alias" }),
      ]),
      directCollectRecords: expect.arrayContaining([
        expect.objectContaining({
          title: "Collected collect record",
          subtitle: "Workspace board · Paper paper-1",
        }),
      ]),
      attributionScope: expect.objectContaining({
        directCollectMetrics: expect.arrayContaining(["Direct Collect Records"]),
        nonAttributionFields: expect.arrayContaining(["Share Grant"]),
      }),
    });
  });

  it("shapes alias drilldowns without inventing collect linkage", () => {
    expect(buildResultShareAliasDrilldownViewModel(resultShareAliasDrilldown)).toMatchObject({
      empty: false,
      alias: expect.objectContaining({
        aliasId: "alias-1",
        title: "Board alias",
      }),
      resultShareGrant: expect.objectContaining({
        grantId: "grant-1",
      }),
      byEventTypeRows: expect.arrayContaining([
        expect.objectContaining({ label: "Content View", count: 1 }),
      ]),
      recentEvents: expect.arrayContaining([
        expect.objectContaining({
          title: "Content View · Alias",
          subtitle: "Resolved · Workspace board",
        }),
      ]),
      attributionScope: expect.objectContaining({
        directCollectMetrics: [],
        notes: expect.arrayContaining(["Alias drilldown is access-path scoped only."]),
      }),
    });
  });

  it("marks zeroed per-share drilldowns as empty", () => {
    expect(
      buildResultShareGrantDrilldownViewModel({
        ...resultShareGrantDrilldown,
        total_events: 0,
        active_alias_count: 0,
        aliases: [],
        recent_events: [],
        direct_collect_records: [],
        direct_collect_collected_count: 0,
        direct_collect_already_present_count: 0,
        direct_collect_rejected_count: 0,
        unique_collecting_user_count: 0,
        by_access_mode: {},
        by_event_type: {},
        by_outcome: {},
      }).empty,
    ).toBe(true);
    expect(
      buildResultShareAliasDrilldownViewModel({
        ...resultShareAliasDrilldown,
        total_events: 0,
        bootstrap_view_count: 0,
        content_view_count: 0,
        redirect_count: 0,
        invite_handoff_redirect_count: 0,
        collect_handoff_redirect_count: 0,
        resolved_event_count: 0,
        rejected_event_count: 0,
        by_event_type: {},
        by_outcome: {},
        recent_events: [],
      }).empty,
    ).toBe(true);
  });

  it("shapes read-only share registries with grant-alias relationships", () => {
    expect(buildResultShareRegistryViewModel(resultShareGrants, resultShareAliases)).toMatchObject({
      grants: {
        summaryMetrics: expect.arrayContaining([
          expect.objectContaining({ label: "Total listed", value: 2 }),
          expect.objectContaining({ label: "Active", value: 1 }),
        ]),
        items: expect.arrayContaining([
          expect.objectContaining({
            grantId: "grant-1",
            title: "Board share",
            aliasCount: 1,
            relationshipHint: "1 alias linked · 1 active",
          }),
        ]),
      },
      aliases: {
        summaryMetrics: expect.arrayContaining([
          expect.objectContaining({ label: "Recent usage", value: 1 }),
        ]),
        items: expect.arrayContaining([
          expect.objectContaining({
            aliasId: "alias-1",
            grantId: "grant-1",
            linkedGrantInRegistry: true,
            relationshipHint: "Board share · active",
          }),
          expect.objectContaining({
            aliasId: "alias-2",
            linkedGrantInRegistry: false,
            relationshipHint: "Grant grant-missing",
          }),
        ]),
      },
    });
  });
});
