import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ResultShareShell } from "./App";
import { ResultShareApiError } from "./lib/apiClient";
import type {
  SharedDigestIssueRead,
  SharedPaperSnapshotRead,
  SharedWorkspaceBoardRead,
  ShareGrantBootstrapRead,
} from "./lib/types";

function bootstrapFixture(kind: ShareGrantBootstrapRead["grant"]["share_kind"]): ShareGrantBootstrapRead {
  return {
    grant: {
      id: "grant-1",
      share_kind: kind,
      display_label: "Share label",
      status: "active",
      expires_at: null,
      created_at: "2026-04-16T06:00:00Z",
    },
    target: {
      workspace_id: kind === "workspace_board" ? "workspace-1" : null,
      digest_issue_id: kind === "digest_issue" ? "digest-1" : null,
      paper_id: kind === "paper_snapshot" ? "paper-1" : null,
      title:
        kind === "workspace_board"
          ? "Materials Group"
          : kind === "paper_snapshot"
            ? "Shared Paper"
            : "Digest title",
    },
    notes: ["Structured read-only share."],
  };
}

function digestFixture(): SharedDigestIssueRead {
  return {
    share_kind: "digest_issue",
    id: "digest-1",
    issue_date: "2026-04-16",
    status: "ready",
    title: "Digest title",
    summary: "Digest summary",
    highlight_count: 1,
    selected_card_count: 1,
    deep_link_path: "/mini/pulse-digests/user-1/2026-04-16",
    highlights: [],
    is_structured: true,
    fallback_mode: "structured",
    section_order: ["today_focus"],
    sections: [
      {
        kind: "today_focus",
        title: "Today Focus",
        item_count: 1,
        items: [
          {
            sort_order: 1,
            pulse_card_id: "card-1",
            card_type: "today_suggestion",
            source_paper_id: "paper-1",
            title: "Focus title",
            summary: "Focus summary",
            why_now: "Why now",
            action_text: "Do the work",
            deep_link: "/papers/paper-1",
            paper: null,
          },
        ],
      },
    ],
    quick_stats: {
      selected_card_count: 1,
      related_paper_count: 0,
      signal_update_count: 0,
      touched_paper_count: 1,
    },
    focus_card: null,
    publication_preview: {
      digest_title: "Digest title",
      digest_subtitle: "Digest subtitle",
      digest_highlights: [],
      primary_cta_text: "Read digest",
      primary_cta_path: "/mini/path",
      mini_program_path: "mini/path",
      article_url: null,
    },
    items: [],
  };
}

function paperFixture(): SharedPaperSnapshotRead {
  return {
    share_kind: "paper_snapshot",
    paper_id: "paper-1",
    user_id: "user-1",
    owner_name: "Owner",
    owner_email: null,
    title: "Shared Paper",
    type: "published",
    stage: "published",
    venue: "JOM",
    priority: 4,
    next_action: "Review delta",
    blocker: null,
    last_touch_at: "2026-04-16T05:00:00Z",
    progress_percentage: 100,
    latest_signal_summary: {
      source: "GOOGLE_SCHOLAR",
      citation_count: 14,
      download_count: 64,
      read_count: 91,
      inclusion_status: "indexed",
      fetched_at: "2026-04-16T04:48:25Z",
    },
  };
}

function workspaceFixture(): SharedWorkspaceBoardRead {
  return {
    share_kind: "workspace_board",
    workspace: {
      id: "workspace-1",
      slug: "materials-group",
      name: "Materials Group",
      description: "Workspace description",
      status: "active",
      created_by_admin_id: "admin-1",
      created_at: "2026-04-16T05:48:25Z",
      updated_at: "2026-04-16T05:48:25Z",
    },
    member_count: 1,
    paper_count: 1,
    members: [
      {
        member_id: "member-1",
        user_id: "user-1",
        role: "owner",
        name: "Owner",
        email: null,
        joined_at: "2026-04-16T05:48:25Z",
      },
    ],
    papers: [paperFixture()],
    quick_stats: {
      member_count: 1,
      paper_count: 1,
      blocked_paper_count: 0,
      papers_with_signals_count: 1,
    },
  };
}

describe("result share shell", () => {
  it("renders the token entry state by default", () => {
    render(<ResultShareShell />);

    expect(screen.getByRole("heading", { name: /open a read-only structured share/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /open share/i })).toBeVisible();
  });

  it("loads and renders a digest share from the /share/<token> path", async () => {
    const apiClientFactory = () => ({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("digest_issue")),
      getShareContent: vi.fn().mockResolvedValue(digestFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share/token-123", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Focus summary")).toBeVisible();
    expect(screen.getByText("Today Focus")).toBeVisible();
  });

  it("supports manual token entry and renders paper shares", async () => {
    const user = userEvent.setup();
    const apiClientFactory = () => ({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("paper_snapshot")),
      getShareContent: vi.fn().mockResolvedValue(paperFixture()),
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/share token/i), "manual-paper-token");
    await user.click(screen.getByRole("button", { name: /open share/i }));

    expect(await screen.findByText("Review delta")).toBeVisible();
    expect(screen.getByText("Review delta")).toBeVisible();
  });

  it("renders workspace board shares", async () => {
    const apiClientFactory = () => ({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("workspace_board")),
      getShareContent: vi.fn().mockResolvedValue(workspaceFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share/workspace-token", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Workspace description")).toBeVisible();
    expect(screen.getByText("Structured paper snapshots")).toBeVisible();
    expect(screen.getByText("Workspace description")).toBeVisible();
  });

  it("shows a clear invalid token state when the share token is revoked or invalid", async () => {
    const user = userEvent.setup();
    const apiClientFactory = () => ({
      getShareBootstrap: vi.fn().mockRejectedValue(
        new ResultShareApiError({
          status: 401,
          detail: "result share grant has expired",
          body: null,
          kind: "expired_token",
        }),
      ),
      getShareContent: vi.fn(),
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/share token/i), "expired-token");
    await user.click(screen.getByRole("button", { name: /open share/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Share link expired");
    });
  });
});
