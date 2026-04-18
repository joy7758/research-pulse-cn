import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GroupWorkspaceAdminShell } from "./App";
import { GroupWorkspaceAdminApiError } from "./lib/apiClient";
import { DEFAULT_CONVERSION_FILTER_INPUT } from "./lib/conversionFilters";
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
  ResultShareGrantIssueResponse,
  ResultShareGrantRead,
  UserProfileRead,
} from "./lib/types";

function workspaceFixture(): GroupWorkspaceRead {
  return {
    id: "workspace-1",
    slug: "materials-group",
    name: "Materials Group",
    description: "Workspace description",
    status: "active",
    created_by_admin_id: "admin-1",
    created_at: "2026-04-16T06:00:00Z",
    updated_at: "2026-04-16T06:00:00Z",
  };
}

function boardFixture(): GroupWorkspaceBoardRead {
  return {
    workspace: workspaceFixture(),
    member_count: 1,
    paper_count: 1,
    members: [
      {
        member_id: "member-1",
        user_id: "user-1",
        role: "owner",
        name: "Owner",
        email: "owner@example.com",
        joined_at: "2026-04-16T06:00:00Z",
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
}

function userFixture(): UserProfileRead[] {
  return [
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
    {
      id: "user-2",
      name: "Viewer",
      email: "viewer@example.com",
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
}

function paperFixture(): PaperProfileRead[] {
  return [
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
      last_touch_at: "2026-04-16T05:00:00Z",
      next_action: "Review delta",
      blocker: null,
      priority: 4,
      created_at: "2026-04-16T06:00:00Z",
      updated_at: "2026-04-16T06:00:00Z",
      progress_events: [],
      signal_snapshots: [],
    },
    {
      id: "paper-2",
      user_id: "user-2",
      title: "Candidate Paper",
      title_zh: null,
      title_en: null,
      type: "draft",
      stage: "draft",
      venue: null,
      identifiers: {},
      source_links: [],
      last_touch_at: null,
      next_action: null,
      blocker: null,
      priority: 3,
      created_at: "2026-04-16T06:00:00Z",
      updated_at: "2026-04-16T06:00:00Z",
      progress_events: [],
      signal_snapshots: [],
    },
  ];
}

function shareGrantFixture(): ResultShareGrantRead[] {
  return [
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
      last_used_at: null,
      created_at: "2026-04-16T06:10:00Z",
      updated_at: "2026-04-16T06:10:00Z",
    },
  ];
}

function shareAliasFixture(): ResultShareAliasRead[] {
  return [
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
  ];
}

function issuedShareFixture(): ResultShareGrantIssueResponse {
  return {
    grant: {
      id: "grant-2",
      share_kind: "workspace_board",
      workspace_id: "workspace-1",
      digest_issue_id: null,
      paper_id: null,
      status: "active",
      display_label: "Board share 2",
      issued_by_admin_id: "admin-1",
      expires_at: null,
      last_used_at: null,
      created_at: "2026-04-16T06:11:00Z",
      updated_at: "2026-04-16T06:11:00Z",
    },
    plain_text_token: "share-token-once",
    expires_at: null,
  };
}

function globalConversionFixture(): GroupWorkspaceConversionOverviewRead {
  return {
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
    by_share_kind: {
      workspace_board: 4,
    },
    by_access_mode: {
      share_token: 2,
      alias: 2,
    },
    by_handoff_target: {
      group_workspace_invite_entry: 1,
      result_share_collect_entry: 1,
    },
    invite_claimed_count: 1,
    invite_already_member_count: 1,
    invite_rejected_count: 0,
    collect_collected_count: 1,
    collect_already_present_count: 1,
    collect_rejected_count: 0,
    unique_result_share_grant_count: 3,
    unique_workspace_count: 1,
    last_activity_at: "2026-04-17T08:00:00Z",
    attribution_scope: {
      direct_attribution_metrics: ["total_share_view_events", "collect_collected_count"],
      workspace_level_aggregate_metrics: ["invite_claimed_count"],
      notes: [
        "Invite claim metrics are workspace-level aggregate signals in v1 and are not strict per-share causal attribution.",
      ],
    },
  };
}

function workspaceConversionFixture(): GroupWorkspaceWorkspaceConversionOverviewRead {
  return {
    window_start: "2026-03-18T00:00:00Z",
    window_end: null,
    workspace: {
      id: "workspace-1",
      slug: "materials-group",
      name: "Materials Group",
      description: "Workspace description",
      status: "active",
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
      notes: [
        "Collect metrics are directly linked when result_share_grant_id is present; records without that link remain aggregate-only signals.",
      ],
    },
  };
}

function globalConversionDrilldownFixture(): GroupWorkspaceConversionDrilldownRead {
  return {
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
          id: "workspace-1",
          slug: "materials-group",
          name: "Materials Group",
          description: "Workspace description",
          status: "active",
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
        workspace_id: "workspace-1",
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
        workspace_id: "workspace-1",
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
}

function workspaceConversionDrilldownFixture(): GroupWorkspaceWorkspaceConversionDrilldownRead {
  return {
    window_start: "2026-03-18T00:00:00Z",
    window_end: null,
    workspace: {
      id: "workspace-1",
      slug: "materials-group",
      name: "Materials Group",
      description: "Workspace description",
      status: "active",
    },
    daily_buckets: globalConversionDrilldownFixture().daily_buckets,
    recent_share_events: globalConversionDrilldownFixture().recent_share_events,
    recent_invite_claims: globalConversionDrilldownFixture().recent_invite_claims,
    recent_collect_records: globalConversionDrilldownFixture().recent_collect_records,
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
}

function resultShareGrantDrilldownFixture(): ResultShareGrantConversionDrilldownRead {
  return {
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
}

function resultShareAliasDrilldownFixture(): ResultShareAliasConversionDrilldownRead {
  return {
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
    result_share_grant: resultShareGrantDrilldownFixture().share_grant,
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
    recent_events: resultShareGrantDrilldownFixture().recent_events,
    last_activity_at: "2026-04-17T08:00:00Z",
    attribution_scope: {
      direct_event_metrics: ["total_events", "recent_events"],
      direct_collect_metrics: [],
      non_attribution_fields: ["alias", "result_share_grant", "notes"],
      notes: ["Alias drilldown is access-path scoped only."],
    },
    notes: ["Collect linkage remains grant-level unless alias-linked persistence exists."],
  };
}

function buildApiClient() {
  return {
    listWorkspaces: vi.fn().mockResolvedValue([workspaceFixture()]),
    createWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    getWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    updateWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    getWorkspaceBoard: vi.fn().mockResolvedValue(boardFixture()),
    getConversionOverview: vi.fn().mockResolvedValue(globalConversionFixture()),
    getConversionDrilldown: vi.fn().mockResolvedValue(globalConversionDrilldownFixture()),
    getWorkspaceConversionOverview: vi.fn().mockResolvedValue(workspaceConversionFixture()),
    getWorkspaceConversionDrilldown: vi.fn().mockResolvedValue(workspaceConversionDrilldownFixture()),
    getResultShareGrantConversionDrilldown: vi
      .fn()
      .mockResolvedValue(resultShareGrantDrilldownFixture()),
    getResultShareAliasConversionDrilldown: vi
      .fn()
      .mockResolvedValue(resultShareAliasDrilldownFixture()),
    addWorkspaceMember: vi.fn().mockResolvedValue(undefined),
    removeWorkspaceMember: vi.fn().mockResolvedValue(undefined),
    addWorkspacePaper: vi.fn().mockResolvedValue(undefined),
    removeWorkspacePaper: vi.fn().mockResolvedValue(undefined),
    listResultShareGrants: vi.fn().mockResolvedValue(shareGrantFixture()),
    listResultShareAliases: vi.fn().mockResolvedValue(shareAliasFixture()),
    createWorkspaceBoardShareGrant: vi.fn().mockResolvedValue(issuedShareFixture()),
    revokeResultShareGrant: vi.fn().mockResolvedValue(undefined),
    listUsers: vi.fn().mockResolvedValue(userFixture()),
    listPapers: vi.fn().mockResolvedValue(paperFixture()),
  };
}

function createMemoryStorage(): Storage {
  let store: Record<string, string> = {};
  return {
    get length() {
      return Object.keys(store).length;
    },
    clear() {
      store = {};
    },
    getItem(key: string) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null;
    },
    key(index: number) {
      return Object.keys(store)[index] ?? null;
    },
    removeItem(key: string) {
      delete store[key];
    },
    setItem(key: string, value: string) {
      store[key] = value;
    },
  };
}

describe("group workspace admin shell", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      value: createMemoryStorage(),
      configurable: true,
    });
  });

  it("renders the token entry state by default", () => {
    render(<GroupWorkspaceAdminShell />);
    expect(
      screen.getByRole("heading", { name: /manage group workspaces and workspace-board shares/i }),
    ).toBeVisible();
  });

  it("loads from a fragment token and clears the visible URL", async () => {
    const client = buildApiClient();
    const historyLike = {
      replaceState: vi.fn(),
    };

    render(
      <GroupWorkspaceAdminShell
        apiClientFactory={() => client}
        locationLike={{ pathname: "/", search: "", hash: "#admin_bearer=fragment-token" }}
        historyLike={historyLike}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Materials Group" })).toBeVisible();
    expect(screen.getAllByText("Workspace description")[0]).toBeVisible();
    expect(historyLike.replaceState).toHaveBeenCalledWith(null, "", "/");
  });

  it("supports manual token entry and renders the workspace board", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    expect(await screen.findByText("Shared Paper")).toBeVisible();
    expect(screen.getByText("Workspace members")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Global conversion filters" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Workspace conversion filters" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Global conversion overview" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Global conversion drilldown" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Result share registry" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Workspace conversion overview" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Workspace conversion drilldown" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Share grant and alias drilldown" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Top workspaces" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Active share-grant snapshot" })).toBeVisible();
    expect(screen.getAllByText("Invite handoffs").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Attribution scope")).toHaveLength(4);
  });

  it("shows the one-time share token after workspace_board grant creation", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(
      <GroupWorkspaceAdminShell
        apiClientFactory={() => client}
        locationLike={{ pathname: "/", search: "", hash: "#admin_bearer=fragment-token" }}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Materials Group" })).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: /create workspace_board share grant/i }),
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue("share-token-once")).toBeVisible();
    });
  });

  it("shows a clear unauthorized state when the admin token is rejected", async () => {
    const user = userEvent.setup();
    const failingClient = {
      listWorkspaces: vi.fn().mockRejectedValue(
        new GroupWorkspaceAdminApiError({
          status: 401,
          detail: "invalid admin token",
          body: null,
          kind: "unauthorized",
        }),
      ),
      getConversionOverview: vi.fn().mockResolvedValue(globalConversionFixture()),
      getConversionDrilldown: vi.fn().mockResolvedValue(globalConversionDrilldownFixture()),
      listUsers: vi.fn(),
      listPapers: vi.fn(),
    };

    render(<GroupWorkspaceAdminShell apiClientFactory={() => failingClient as never} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "bad-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Unauthorized admin token");
    });
  });

  it("applies and resets global conversion filters without a page reload", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const globalFilterCard = screen
      .getByRole("heading", { name: "Global conversion filters" })
      .closest("section");
    expect(globalFilterCard).not.toBeNull();
    const scoped = within(globalFilterCard as HTMLElement);

    fireEvent.change(scoped.getByLabelText("Date from"), {
      target: { value: "2026-04-01" },
    });
    fireEvent.change(scoped.getByLabelText("Date to"), {
      target: { value: "2026-04-17" },
    });
    await user.selectOptions(scoped.getByLabelText("Share kind"), "workspace_board");
    await user.selectOptions(scoped.getByLabelText("Access mode"), "alias");
    await user.selectOptions(scoped.getByLabelText("Event type"), "content_view");
    await user.selectOptions(scoped.getByLabelText("Outcome"), "resolved");
    await user.selectOptions(scoped.getByLabelText("Recent rows limit"), "50");
    await user.click(scoped.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(client.getConversionOverview).toHaveBeenLastCalledWith({
        dateFrom: "2026-04-01",
        dateTo: "2026-04-17",
        shareKind: "workspace_board",
        accessMode: "alias",
        eventType: "content_view",
        outcome: "resolved",
        limit: 50,
      });
      expect(client.getConversionDrilldown).toHaveBeenLastCalledWith({
        dateFrom: "2026-04-01",
        dateTo: "2026-04-17",
        shareKind: "workspace_board",
        accessMode: "alias",
        eventType: "content_view",
        outcome: "resolved",
        limit: 50,
      });
    });

    const summaryCard = scoped
      .getByRole("heading", { name: "Applied filter summary" })
      .closest("section");
    expect(summaryCard).not.toBeNull();

    const summary = within(summaryCard as HTMLElement);
    expect(summary.getByText("Workspace board")).toBeVisible();
    expect(summary.getByText("Resolved")).toBeVisible();

    await user.click(scoped.getByRole("button", { name: "Reset defaults" }));

    await waitFor(() => {
      expect(client.getConversionOverview).toHaveBeenLastCalledWith(
        DEFAULT_CONVERSION_FILTER_INPUT,
      );
      expect(client.getConversionDrilldown).toHaveBeenLastCalledWith(
        DEFAULT_CONVERSION_FILTER_INPUT,
      );
    });
  });

  it("applies workspace conversion filters inside workspace detail", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const workspaceFilterCard = screen
      .getByRole("heading", { name: "Workspace conversion filters" })
      .closest("section");
    expect(workspaceFilterCard).not.toBeNull();
    const scoped = within(workspaceFilterCard as HTMLElement);

    fireEvent.change(scoped.getByLabelText("Date from"), {
      target: { value: "2026-04-05" },
    });
    await user.selectOptions(scoped.getByLabelText("Share kind"), "paper_snapshot");
    await user.selectOptions(scoped.getByLabelText("Event type"), "collect_handoff_redirect");
    await user.selectOptions(scoped.getByLabelText("Outcome"), "rejected");
    await user.selectOptions(scoped.getByLabelText("Recent rows limit"), "10");
    await user.click(scoped.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(client.getWorkspaceConversionOverview).toHaveBeenLastCalledWith("workspace-1", {
        dateFrom: "2026-04-05",
        dateTo: null,
        shareKind: "paper_snapshot",
        accessMode: null,
        eventType: "collect_handoff_redirect",
        outcome: "rejected",
        limit: 10,
      });
      expect(client.getWorkspaceConversionDrilldown).toHaveBeenLastCalledWith("workspace-1", {
        dateFrom: "2026-04-05",
        dateTo: null,
        shareKind: "paper_snapshot",
        accessMode: null,
        eventType: "collect_handoff_redirect",
        outcome: "rejected",
        limit: 10,
      });
    });
  });

  it("renders a graceful empty conversion state when overview counts are zero", async () => {
    const client = buildApiClient();
    client.getConversionOverview.mockResolvedValue({
      ...globalConversionFixture(),
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
    });
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    expect(
      await screen.findByText(
        "No share, invite, or collect activity has been recorded in this analytics window.",
      ),
    ).toBeVisible();
  });

  it("renders graceful empty drilldown states when reserve rows are absent", async () => {
    const client = buildApiClient();
    client.getConversionDrilldown.mockResolvedValue({
      ...globalConversionDrilldownFixture(),
      daily_buckets: [],
      top_workspaces: [],
      top_result_share_grants: [],
      recent_share_events: [],
      recent_invite_claims: [],
      recent_collect_records: [],
    });
    client.getWorkspaceConversionDrilldown.mockResolvedValue({
      ...workspaceConversionDrilldownFixture(),
      daily_buckets: [],
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
    });
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    expect(
      await screen.findByText(
        "No global drilldown activity has been recorded in this analytics window.",
      ),
    ).toBeVisible();
    expect(
      screen.getByText("No workspace drilldown activity has been recorded in this window."),
    ).toBeVisible();
  });

  it("opens share grant drilldown from the existing share-grant list", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));
    await user.click(screen.getByRole("button", { name: "Open drilldown" }));

    await waitFor(() => {
      expect(client.getResultShareGrantConversionDrilldown).toHaveBeenLastCalledWith(
        "grant-1",
        DEFAULT_CONVERSION_FILTER_INPUT,
      );
    });

    expect(await screen.findByRole("heading", { name: "Direct collect records" })).toBeVisible();
    const aliasSection = screen.getByRole("heading", { name: "Aliases" }).closest("section");
    expect(aliasSection).not.toBeNull();
    const aliasScoped = within(aliasSection as HTMLElement);
    expect(aliasScoped.getByRole("button", { name: "Open alias drilldown" })).toBeVisible();
    expect(aliasScoped.getByText("Board alias")).toBeVisible();
  });

  it("opens alias drilldown from grant aliases without adding collect linkage", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));
    await user.click(screen.getByRole("button", { name: "Open drilldown" }));
    const aliasSection = await screen.findByRole("heading", { name: "Aliases" });
    await user.click(
      within(aliasSection.closest("section") as HTMLElement).getByRole("button", {
        name: "Open alias drilldown",
      }),
    );

    await waitFor(() => {
      expect(client.getResultShareAliasConversionDrilldown).toHaveBeenLastCalledWith(
        "alias-1",
        DEFAULT_CONVERSION_FILTER_INPUT,
      );
    });

    expect(await screen.findByRole("heading", { name: "Underlying grant summary" })).toBeVisible();
    expect(
      screen.getByText(
        "Alias-scoped access behavior only. Grant-level collect linkage remains separate.",
      ),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Direct collect records" }),
    ).not.toBeInTheDocument();
  });

  it("applies per-share drilldown filters without exposing share-kind controls", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));
    await user.click(screen.getByRole("button", { name: "Open drilldown" }));

    const perShareFilterCard = screen
      .getByRole("heading", { name: "Per-share drilldown filters" })
      .closest("section");
    expect(perShareFilterCard).not.toBeNull();
    const scoped = within(perShareFilterCard as HTMLElement);

    expect(scoped.queryByLabelText("Share kind")).not.toBeInTheDocument();
    await user.selectOptions(scoped.getByLabelText("Access mode"), "alias");
    await user.selectOptions(scoped.getByLabelText("Event type"), "content_view");
    await user.selectOptions(scoped.getByLabelText("Outcome"), "resolved");
    await user.selectOptions(scoped.getByLabelText("Recent rows limit"), "10");
    await user.click(scoped.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(client.getResultShareGrantConversionDrilldown).toHaveBeenLastCalledWith("grant-1", {
        dateFrom: null,
        dateTo: null,
        shareKind: null,
        accessMode: "alias",
        eventType: "content_view",
        outcome: "resolved",
        limit: 10,
      });
    });
  });

  it("renders read-only share registries and quick-opens drilldown from registry rows", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    expect(await screen.findByRole("heading", { name: "Result share registry" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Share grant registry" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Alias registry" })).toBeVisible();
    expect(screen.getByText("Board alias")).toBeVisible();
    expect(screen.getAllByText("Board share").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Show aliases for this grant" })).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Open linked grant" }));

    await waitFor(() => {
      expect(client.getResultShareGrantConversionDrilldown).toHaveBeenLastCalledWith(
        "grant-1",
        DEFAULT_CONVERSION_FILTER_INPUT,
      );
    });
  });

  it("applies the grant-to-alias quick filter from a registry row", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));
    await user.click(screen.getByRole("button", { name: "Show aliases for this grant" }));

    await waitFor(() => {
      expect(client.listResultShareAliases).toHaveBeenLastCalledWith({
        resultShareGrantId: "grant-1",
        shareKind: "workspace_board",
        status: undefined,
      });
    });

    const summaryCard = screen
      .getByRole("heading", { name: "Applied registry filters and sort" })
      .closest("section");
    expect(summaryCard).not.toBeNull();
    const summaryScoped = within(summaryCard as HTMLElement);
    expect(summaryScoped.getByText("Alias grant")).toBeVisible();
    expect(summaryScoped.getByText("grant-1")).toBeVisible();
  });

  it("applies stable registry sort controls and shows sort chips", async () => {
    const client = buildApiClient();
    client.listResultShareGrants.mockResolvedValue([
      {
        id: "grant-z",
        share_kind: "workspace_board",
        workspace_id: "workspace-1",
        digest_issue_id: null,
        paper_id: null,
        status: "active",
        display_label: "Newest grant",
        issued_by_admin_id: "admin-1",
        expires_at: null,
        last_used_at: null,
        created_at: "2026-04-17T06:10:00Z",
        updated_at: "2026-04-17T06:10:00Z",
      },
      {
        id: "grant-a",
        share_kind: "workspace_board",
        workspace_id: "workspace-1",
        digest_issue_id: null,
        paper_id: null,
        status: "revoked",
        display_label: "Older grant",
        issued_by_admin_id: "admin-1",
        expires_at: null,
        last_used_at: "2026-04-17T08:00:00Z",
        created_at: "2026-04-15T06:10:00Z",
        updated_at: "2026-04-15T06:10:00Z",
      },
    ]);
    client.listResultShareAliases.mockResolvedValue([
      {
        id: "alias-b",
        result_share_grant_id: "grant-z",
        share_kind: "workspace_board",
        status: "active",
        display_label: "Alias B",
        alias_prefix: "bbb222",
        expires_at: null,
        last_used_at: null,
        created_at: "2026-04-17T06:11:00Z",
        updated_at: "2026-04-17T06:11:00Z",
      },
      {
        id: "alias-a",
        result_share_grant_id: "grant-a",
        share_kind: "workspace_board",
        status: "revoked",
        display_label: "Alias A",
        alias_prefix: "aaa111",
        expires_at: null,
        last_used_at: "2026-04-17T08:00:00Z",
        created_at: "2026-04-15T06:11:00Z",
        updated_at: "2026-04-15T06:11:00Z",
      },
    ]);
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);
    await user.selectOptions(scoped.getByLabelText("Grant sort"), "createdAt_asc");
    await user.selectOptions(scoped.getByLabelText("Alias sort"), "status_desc");
    await user.click(scoped.getByRole("button", { name: "Apply filters" }));

    const summaryCard = scoped
      .getByRole("heading", { name: "Applied registry filters and sort" })
      .closest("section");
    expect(summaryCard).not.toBeNull();
    const summaryScoped = within(summaryCard as HTMLElement);
    expect(summaryScoped.getByText("Created, oldest first")).toBeVisible();
    expect(summaryScoped.getByText("Status, Z-A")).toBeVisible();

    const grantSection = screen.getByRole("heading", { name: "Share grant registry" }).closest("section");
    const aliasSection = screen.getByRole("heading", { name: "Alias registry" }).closest("section");
    expect(grantSection).not.toBeNull();
    expect(aliasSection).not.toBeNull();

    const grantRows = within(grantSection as HTMLElement).getAllByRole("listitem");
    const aliasRows = within(aliasSection as HTMLElement).getAllByRole("listitem");
    expect(grantRows[0]).toHaveTextContent("Older grant");
    expect(aliasRows[0]).toHaveTextContent("Alias A");
  });

  it("renders a filtered empty registry state without breaking the rest of the shell", async () => {
    const client = buildApiClient();
    client.listResultShareGrants.mockResolvedValue([]);
    client.listResultShareAliases.mockResolvedValue([]);
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = screen.getByRole("heading", { name: "Result share registry" }).closest("section");
    expect(registryPanel).not.toBeNull();
    const scoped = within(registryPanel as HTMLElement);
    await user.type(scoped.getByLabelText("Workspace ID"), "workspace-1");
    await user.type(scoped.getByLabelText("Grant ID"), "grant-1");
    await user.click(scoped.getByRole("button", { name: "Apply filters" }));

    expect(
      await scoped.findByText(
        "No share grants matched the current grant filters.",
      ),
    ).toBeVisible();
    expect(
      scoped.getByText("No aliases matched the current alias filters."),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Workspace conversion overview" })).toBeVisible();
  });

  it("saves, applies, overwrites, and deletes local registry presets without storing the admin token", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);

    await user.clear(scoped.getByLabelText("Workspace ID"));
    await user.type(scoped.getByLabelText("Workspace ID"), "workspace-1");
    await user.selectOptions(scoped.getByLabelText("Grant sort"), "createdAt_asc");
    await user.type(scoped.getByLabelText("Grant preset name"), "Board triage");
    await user.click(scoped.getByRole("button", { name: "Save current grant view" }));

    expect(await scoped.findByText("Board triage")).toBeVisible();
    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).toContain("Board triage");
    expect(JSON.stringify(window.localStorage)).not.toContain("manual-token");

    await user.clear(scoped.getByLabelText("Workspace ID"));
    await user.type(scoped.getByLabelText("Workspace ID"), "workspace-2");
    await user.clear(scoped.getByLabelText("Grant preset name"));
    await user.type(scoped.getByLabelText("Grant preset name"), "Renamed triage");
    await user.click(scoped.getByRole("button", { name: "Overwrite with current view" }));

    expect(await scoped.findByText("Renamed triage")).toBeVisible();
    expect(scoped.queryByText("Board triage")).not.toBeInTheDocument();

    await user.clear(scoped.getByLabelText("Workspace ID"));
    await user.click(scoped.getByRole("button", { name: "Apply registry only" }));

    await waitFor(() => {
      expect(scoped.getByLabelText("Workspace ID")).toHaveValue("workspace-2");
    });
    expect(scoped.getByLabelText("Grant sort")).toHaveValue("createdAt_asc");

    await user.click(scoped.getByRole("button", { name: "Delete preset" }));
    const grantSavedViewSection = scoped
      .getByRole("heading", { name: "Grant saved views" })
      .closest("section");
    expect(grantSavedViewSection).not.toBeNull();
    expect(
      await within(grantSavedViewSection as HTMLElement).findByText("No saved views yet."),
    ).toBeVisible();
  });

  it("applies saved drilldown context to quick-opened grant drilldown when requested", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    await user.click(screen.getByRole("button", { name: "Open drilldown" }));

    const perShareFilterCard = screen
      .getByRole("heading", { name: "Per-share drilldown filters" })
      .closest("section");
    expect(perShareFilterCard).not.toBeNull();
    const perShareScoped = within(perShareFilterCard as HTMLElement);
    await user.type(perShareScoped.getByLabelText("Date from"), "2026-04-01");
    await user.selectOptions(perShareScoped.getByLabelText("Event type"), "content_view");
    await user.selectOptions(perShareScoped.getByLabelText("Recent rows limit"), "10");
    await user.click(perShareScoped.getByRole("button", { name: "Apply filters" }));

    const registryPanel = screen.getByRole("heading", { name: "Result share registry" }).closest("section");
    expect(registryPanel).not.toBeNull();
    const registryScoped = within(registryPanel as HTMLElement);
    const grantSavedViewSection = registryScoped
      .getByRole("heading", { name: "Grant saved views" })
      .closest("section");
    expect(grantSavedViewSection).not.toBeNull();
    const grantPresetScoped = within(grantSavedViewSection as HTMLElement);

    await user.type(registryScoped.getByLabelText("Grant preset name"), "Board drilldown preset");
    await user.click(grantPresetScoped.getByLabelText("Include current per-share drilldown filters"));
    await user.click(registryScoped.getByRole("button", { name: "Save current grant view" }));

    expect(await registryScoped.findByText("Board drilldown preset")).toBeVisible();
    expect(registryScoped.getByText("Linked per-share drilldown context")).toBeVisible();
    expect(registryScoped.getByText("Date from: 2026-04-01")).toBeVisible();

    await user.click(registryScoped.getByRole("button", { name: "Reset drilldown context" }));
    expect(
      registryScoped.getByText("Manual / current per-share drilldown filters"),
    ).toBeVisible();

    await user.click(registryScoped.getByRole("button", { name: "Apply registry + drilldown" }));

    expect(
      await screen.findAllByText("Saved view drilldown context · Board drilldown preset"),
    ).not.toHaveLength(0);
    await user.click(registryScoped.getByRole("button", { name: "Open grant drilldown" }));

    await waitFor(() => {
      expect(client.getResultShareGrantConversionDrilldown).toHaveBeenLastCalledWith("grant-1", {
        dateFrom: "2026-04-01",
        dateTo: null,
        shareKind: null,
        accessMode: null,
        eventType: "content_view",
        outcome: null,
        limit: 10,
      });
    });
  });

  it("renders import preview and validation errors for unsafe preset JSON", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);
    const fileInput = scoped.getByLabelText("Import preset JSON file");
    const importFile = new File(
      [
        JSON.stringify({
          schemaVersion: "result-share-registry-presets.v1",
          exportedAt: "2026-04-18T10:00:00Z",
          app: "research-pulse-cn",
          source: "group-workspace-admin-web",
          secret: "blocked",
          presets: {
            grantRegistry: [
              {
                id: "unsafe-grant",
                name: "Unsafe grant",
                scope: "grant_registry",
                filters: {
                  shareKind: "workspace_board",
                  grantStatus: "active",
                  aliasStatus: null,
                  workspaceId: "workspace-1",
                  resultShareGrantId: null,
                },
                sort: {
                  field: "createdAt",
                  direction: "asc",
                },
                sourceFile: "/tmp/preset.json",
                createdAt: "2026-04-18T08:00:00Z",
                updatedAt: "2026-04-18T08:00:00Z",
              },
            ],
            aliasRegistry: [],
          },
        }),
      ],
      "unsafe-presets.json",
      { type: "application/json" },
    );

    fireEvent.change(fileInput, {
      target: {
        files: [importFile],
      },
    });

    expect(await scoped.findByRole("heading", { name: "Import preview" })).toBeVisible();
    expect(scoped.getByRole("alert")).toHaveTextContent(/validation errors/i);
    expect(scoped.getByRole("alert")).toHaveTextContent(/unsafe field/i);
    expect(scoped.getByRole("button", { name: "Apply import" })).toBeDisabled();
  });

  it("renders local preset diagnostics for corrupted storage", async () => {
    window.localStorage.setItem("resultShareRegistryGrantPresets", "{not-json");
    window.localStorage.setItem(
      "resultShareRegistryAliasPresets",
      JSON.stringify({ broken: true }),
    );

    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);

    expect(scoped.getByRole("heading", { name: "Preset storage diagnostics" })).toBeVisible();
    expect(
      scoped.getByText(/resultShareRegistryGrantPresets.+not valid JSON/i),
    ).toBeVisible();
    expect(
      scoped.getByText(/resultShareRegistryAliasPresets.+must contain an array/i),
    ).toBeVisible();
    expect(scoped.getByRole("button", { name: "Run integrity check" })).toBeVisible();
  });

  it("keeps import preview in validation-only mode until apply is clicked", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);
    await user.type(scoped.getByLabelText("Grant preset name"), "Existing grant preset");
    await user.click(scoped.getByRole("button", { name: "Save current grant view" }));
    const beforeGrant = window.localStorage.getItem("resultShareRegistryGrantPresets");
    const beforeAlias = window.localStorage.getItem("resultShareRegistryAliasPresets");

    const importFile = new File(
      [
        JSON.stringify({
          schemaVersion: "result-share-registry-presets.v1",
          exportedAt: "2026-04-18T10:00:00Z",
          app: "research-pulse-cn",
          source: "group-workspace-admin-web",
          presets: {
            aliasRegistry: [
              {
                id: "alias-dry-run",
                name: "Alias dry run",
                scope: "alias_registry",
                filters: {
                  shareKind: "workspace_board",
                  grantStatus: null,
                  aliasStatus: "active",
                  workspaceId: null,
                  resultShareGrantId: "grant-1",
                },
                sort: {
                  field: "status",
                  direction: "desc",
                },
                createdAt: "2026-04-18T08:00:00Z",
                updatedAt: "2026-04-18T08:00:00Z",
              },
            ],
          },
        }),
      ],
      "dry-run-presets.json",
      { type: "application/json" },
    );

    fireEvent.change(scoped.getByLabelText("Import preset JSON file"), {
      target: {
        files: [importFile],
      },
    });

    expect(await scoped.findByRole("heading", { name: "Import preview" })).toBeVisible();
    expect(
      scoped.getByText(/Selecting a file is validation-only until you explicitly apply/i),
    ).toBeVisible();
    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).toBe(beforeGrant);
    expect(window.localStorage.getItem("resultShareRegistryAliasPresets")).toBe(beforeAlias);
    expect(window.localStorage.getItem("resultShareRegistryPresetLastGoodBackup")).toBeNull();
  });

  it("creates a backup before reset and restores it on demand", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);
    await user.type(scoped.getByLabelText("Grant preset name"), "Backupable preset");
    await user.click(scoped.getByRole("button", { name: "Save current grant view" }));
    expect(await scoped.findByText("Backupable preset")).toBeVisible();

    await user.click(scoped.getByRole("button", { name: "Reset all registry presets" }));
    expect(confirmSpy).toHaveBeenCalled();
    expect(await scoped.findAllByText("No saved views yet.")).toHaveLength(2);
    expect(window.localStorage.getItem("resultShareRegistryPresetLastGoodBackup")).not.toBeNull();

    await user.click(scoped.getByRole("button", { name: "Restore last-good backup" }));
    expect(await scoped.findAllByText("Backupable preset")).not.toHaveLength(0);

    confirmSpy.mockRestore();
  });

  it("merges imported presets without deleting existing local presets", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);

    await user.type(scoped.getByLabelText("Grant preset name"), "Existing grant preset");
    await user.click(scoped.getByRole("button", { name: "Save current grant view" }));
    expect(await scoped.findByText("Existing grant preset")).toBeVisible();

    const importFile = new File(
      [
        JSON.stringify({
          schemaVersion: "result-share-registry-presets.v1",
          exportedAt: "2026-04-18T10:00:00Z",
          app: "research-pulse-cn",
          source: "group-workspace-admin-web",
          presets: {
            aliasRegistry: [
              {
                id: "alias-imported",
                name: "Imported alias preset",
                scope: "alias_registry",
                filters: {
                  shareKind: "workspace_board",
                  grantStatus: null,
                  aliasStatus: "active",
                  workspaceId: null,
                  resultShareGrantId: "grant-1",
                },
                sort: {
                  field: "status",
                  direction: "desc",
                },
                createdAt: "2026-04-18T08:00:00Z",
                updatedAt: "2026-04-18T08:00:00Z",
              },
            ],
          },
        }),
      ],
      "merge-presets.json",
      { type: "application/json" },
    );

    fireEvent.change(scoped.getByLabelText("Import preset JSON file"), {
      target: {
        files: [importFile],
      },
    });

    expect(await scoped.findByRole("heading", { name: "Import preview" })).toBeVisible();
    await user.click(scoped.getByRole("button", { name: "Apply import" }));

    expect(await scoped.findByText("Existing grant preset")).toBeVisible();
    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).toContain(
      "Existing grant preset",
    );
    expect(window.localStorage.getItem("resultShareRegistryAliasPresets")).toContain(
      "Imported alias preset",
    );
  });

  it("replaces only imported scopes and keeps absent scopes intact", async () => {
    window.localStorage.setItem(
      "resultShareRegistryGrantPresets",
      JSON.stringify([
        {
          id: "grant-default",
          name: "Grant default",
          scope: "grant_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: "active",
            aliasStatus: null,
            workspaceId: "workspace-1",
            resultShareGrantId: null,
          },
          sort: {
            field: "createdAt",
            direction: "asc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem(
      "resultShareRegistryAliasPresets",
      JSON.stringify([
        {
          id: "alias-keep",
          name: "Alias keep",
          scope: "alias_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: null,
            aliasStatus: "active",
            workspaceId: null,
            resultShareGrantId: "grant-1",
          },
          sort: {
            field: "status",
            direction: "desc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem("resultShareRegistryDefaultPresetId", "grant-default");

    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);
    expect(scoped.getAllByText("Grant default").length).toBeGreaterThan(0);
    expect(scoped.getByText("Alias keep")).toBeVisible();

    const importFile = new File(
      [
        JSON.stringify({
          schemaVersion: "result-share-registry-presets.v1",
          exportedAt: "2026-04-18T10:00:00Z",
          app: "research-pulse-cn",
          source: "group-workspace-admin-web",
          presets: {
            grantRegistry: [
              {
                id: "grant-replaced",
                name: "Grant replaced",
                scope: "grant_registry",
                filters: {
                  shareKind: "digest_issue",
                  grantStatus: "revoked",
                  aliasStatus: null,
                  workspaceId: null,
                  resultShareGrantId: null,
                },
                sort: {
                  field: "status",
                  direction: "desc",
                },
                createdAt: "2026-04-18T09:00:00Z",
                updatedAt: "2026-04-18T09:00:00Z",
              },
            ],
          },
        }),
      ],
      "replace-presets.json",
      { type: "application/json" },
    );

    fireEvent.change(scoped.getByLabelText("Import preset JSON file"), {
      target: {
        files: [importFile],
      },
    });

    await scoped.findByRole("heading", { name: "Import preview" });
    await user.selectOptions(scoped.getByLabelText("Import mode"), "replace");
    await user.click(scoped.getByRole("button", { name: "Apply import" }));

    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).toContain(
      "Grant replaced",
    );
    expect(window.localStorage.getItem("resultShareRegistryGrantPresets")).not.toContain(
      "Grant default",
    );
    expect(window.localStorage.getItem("resultShareRegistryAliasPresets")).toContain("Alias keep");
    expect(window.localStorage.getItem("resultShareRegistryDefaultPresetId")).toBeNull();
    expect(scoped.getByText("No default saved view is set.")).toBeVisible();
  });

  it("restores the default local registry preset on shell load", async () => {
    window.localStorage.setItem(
      "resultShareRegistryGrantPresets",
      JSON.stringify([
        {
          id: "grant-default",
          name: "Grant default",
          scope: "grant_registry",
          filters: {
            shareKind: "workspace_board",
            grantStatus: "active",
            aliasStatus: null,
            workspaceId: "workspace-1",
            resultShareGrantId: null,
          },
          sort: {
            field: "createdAt",
            direction: "asc",
          },
          createdAt: "2026-04-18T08:00:00Z",
          updatedAt: "2026-04-18T08:00:00Z",
        },
      ]),
    );
    window.localStorage.setItem("resultShareRegistryAliasPresets", JSON.stringify([]));
    window.localStorage.setItem("resultShareRegistryDefaultPresetId", "grant-default");

    const client = buildApiClient();
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));

    const registryPanel = await screen.findByRole("heading", { name: "Result share registry" });
    const scoped = within(registryPanel.closest("section") as HTMLElement);

    expect(scoped.getByLabelText("Workspace ID")).toHaveValue("workspace-1");
    expect(scoped.getByLabelText("Grant sort")).toHaveValue("createdAt_asc");
    expect(scoped.getAllByText("Grant default").length).toBeGreaterThan(0);
    expect(client.listResultShareGrants).toHaveBeenCalledWith({
      workspaceId: "workspace-1",
      shareKind: "workspace_board",
      status: "active",
    });
  });

  it("renders a graceful empty per-share drilldown state", async () => {
    const client = buildApiClient();
    client.getResultShareGrantConversionDrilldown.mockResolvedValue({
      ...resultShareGrantDrilldownFixture(),
      total_events: 0,
      bootstrap_view_count: 0,
      content_view_count: 0,
      redirect_count: 0,
      invite_handoff_redirect_count: 0,
      collect_handoff_redirect_count: 0,
      resolved_event_count: 0,
      rejected_event_count: 0,
      by_access_mode: {},
      by_event_type: {},
      by_outcome: {},
      active_alias_count: 0,
      aliases: [],
      recent_events: [],
      direct_collect_records: [],
      direct_collect_collected_count: 0,
      direct_collect_already_present_count: 0,
      direct_collect_rejected_count: 0,
      unique_collecting_user_count: 0,
    });
    const user = userEvent.setup();

    render(<GroupWorkspaceAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workspace shell/i }));
    await user.click(screen.getByRole("button", { name: "Open drilldown" }));

    expect(
      await screen.findByText(
        "No events, aliases, or direct collect records were returned for this share grant.",
      ),
    ).toBeVisible();
  });
});
