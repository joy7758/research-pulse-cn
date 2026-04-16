import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GroupWorkspaceAdminShell } from "./App";
import { GroupWorkspaceAdminApiError } from "./lib/apiClient";
import type {
  GroupWorkspaceBoardRead,
  GroupWorkspaceRead,
  PaperProfileRead,
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

function buildApiClient() {
  return {
    listWorkspaces: vi.fn().mockResolvedValue([workspaceFixture()]),
    createWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    getWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    updateWorkspace: vi.fn().mockResolvedValue(workspaceFixture()),
    getWorkspaceBoard: vi.fn().mockResolvedValue(boardFixture()),
    addWorkspaceMember: vi.fn().mockResolvedValue(undefined),
    removeWorkspaceMember: vi.fn().mockResolvedValue(undefined),
    addWorkspacePaper: vi.fn().mockResolvedValue(undefined),
    removeWorkspacePaper: vi.fn().mockResolvedValue(undefined),
    listResultShareGrants: vi.fn().mockResolvedValue(shareGrantFixture()),
    createWorkspaceBoardShareGrant: vi.fn().mockResolvedValue(issuedShareFixture()),
    revokeResultShareGrant: vi.fn().mockResolvedValue(undefined),
    listUsers: vi.fn().mockResolvedValue(userFixture()),
    listPapers: vi.fn().mockResolvedValue(paperFixture()),
  };
}

describe("group workspace admin shell", () => {
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
});
