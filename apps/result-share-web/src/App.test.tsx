import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ResultShareShell } from "./App";
import { ResultShareApiError, type ResultShareApiClient } from "./lib/apiClient";
import type {
  GroupWorkspaceResultCollectionRead,
  ResultShareCollectPreviewRead,
  ResultShareCollectResponseRead,
  SharedDigestIssueRead,
  SharedPaperSnapshotRead,
  SharedWorkspaceBoardRead,
  ShareGrantBootstrapRead,
} from "./lib/types";

function bootstrapFixture(
  kind: ShareGrantBootstrapRead["grant"]["share_kind"],
): ShareGrantBootstrapRead {
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
    collection_reserve: {
      supported: kind !== "workspace_board",
      share_kind_collectable: kind !== "workspace_board",
      collect_supported_via_self_service: kind !== "workspace_board",
      source_files_included: false,
      notes:
        kind === "workspace_board"
          ? ["Workspace-board shares are not collectable in this phase."]
          : ["Structured paper collection is available through a separate self-service grant."],
    },
    workspace_invite_handoff_reserve:
      kind === "workspace_board"
        ? {
            supported: true,
            share_kind: "workspace_board",
            separate_invite_token_required: true,
            invite_bootstrap_available: true,
            self_service_claim_supported: true,
            direct_claim_via_share_page: false,
            handoff_redirect_supported: true,
            source_files_included: false,
            invite_shell_entry_url: "http://127.0.0.1:5177",
            invite_handoff_url: "/result-shares/workspace-token/invite-handoff",
            notes: [
              "Joining requires a separate invite token and the existing self-service claim flow.",
            ],
          }
        : null,
    result_collect_handoff_reserve:
      kind === "workspace_board"
        ? {
            supported: true,
            share_kind: "workspace_board",
            separate_result_share_token_required: true,
            result_share_bootstrap_available: true,
            collect_supported_via_self_service: true,
            direct_collect_via_current_share: false,
            source_files_included: false,
            supported_share_kinds: ["digest_issue", "paper_snapshot"],
            result_share_shell_entry_url: "http://127.0.0.1:5174",
            notes: [
              "Collecting papers into the workspace requires a separate digest or paper share token and the existing self-service collect flow.",
            ],
          }
        : null,
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
    selected_card_count: 2,
    deep_link_path: "/mini/pulse-digests/user-1/2026-04-16",
    highlights: [],
    is_structured: true,
    fallback_mode: "structured",
    section_order: ["today_focus"],
    sections: [
      {
        kind: "today_focus",
        title: "Today Focus",
        item_count: 2,
        items: [
          {
            sort_order: 1,
            pulse_card_id: "card-1",
            card_type: "today_suggestion",
            source_paper_id: "paper-1",
            title: "Digest Paper A",
            summary: "Focus summary",
            why_now: "Why now",
            action_text: "Do the work",
            deep_link: "/papers/paper-1",
            paper: null,
          },
          {
            sort_order: 2,
            pulse_card_id: "card-2",
            card_type: "signal_change",
            source_paper_id: "paper-2",
            title: "Digest Paper B",
            summary: "Signal summary",
            why_now: null,
            action_text: null,
            deep_link: null,
            paper: null,
          },
        ],
      },
    ],
    quick_stats: {
      selected_card_count: 2,
      related_paper_count: 0,
      signal_update_count: 1,
      touched_paper_count: 2,
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

function paperSnapshotPreview(): ResultShareCollectPreviewRead {
  return {
    share: {
      id: "share-1",
      share_kind: "paper_snapshot",
      status: "active",
      display_label: "Paper share",
      expires_at: null,
      target: {
        workspace_id: null,
        digest_issue_id: null,
        paper_id: "paper-1",
        title: "Shared Paper",
      },
    },
    collectable_items: [
      {
        paper_id: "paper-1",
        title: "Shared Paper",
        type: "published",
        stage: "published",
        venue: "JOM",
        priority: 4,
        next_action: "Review delta",
        blocker: null,
        progress_percentage: 100,
        source_card_type: null,
        source_pulse_card_id: null,
        source_section_kind: null,
        notes: null,
      },
    ],
    eligible_workspaces: [
      {
        workspace: {
          id: "workspace-1",
          slug: "materials-group",
          name: "Materials Group",
          description: "Workspace description",
          status: "active",
        },
        membership_role: "editor",
      },
    ],
    can_collect: true,
    reason_codes: [],
    notes: ["Single paper collect is available."],
  };
}

function digestPreview(): ResultShareCollectPreviewRead {
  return {
    share: {
      id: "share-2",
      share_kind: "digest_issue",
      status: "active",
      display_label: "Digest share",
      expires_at: null,
      target: {
        workspace_id: null,
        digest_issue_id: "digest-1",
        paper_id: null,
        title: "Digest title",
      },
    },
    collectable_items: [
      {
        paper_id: "paper-1",
        title: "Digest Paper A",
        type: "published",
        stage: "published",
        venue: "JOM",
        priority: 4,
        next_action: "Review A",
        blocker: null,
        progress_percentage: 100,
        source_card_type: "today_suggestion",
        source_pulse_card_id: "card-1",
        source_section_kind: "today_focus",
        notes: [],
      },
      {
        paper_id: "paper-2",
        title: "Digest Paper B",
        type: "published",
        stage: "published",
        venue: "JOM",
        priority: 3,
        next_action: "Review B",
        blocker: null,
        progress_percentage: 100,
        source_card_type: "signal_change",
        source_pulse_card_id: "card-2",
        source_section_kind: "signal_updates",
        notes: [],
      },
    ],
    eligible_workspaces: [
      {
        workspace: {
          id: "workspace-1",
          slug: "materials-group",
          name: "Materials Group",
          description: "Workspace description",
          status: "active",
        },
        membership_role: "owner",
      },
    ],
    can_collect: true,
    reason_codes: [],
    notes: ["Explicit paper selection is required for multi-paper digest collect."],
  };
}

function boardPreview(): ResultShareCollectPreviewRead {
  return {
    share: {
      id: "share-3",
      share_kind: "workspace_board",
      status: "active",
      display_label: "Workspace board",
      expires_at: null,
      target: {
        workspace_id: "workspace-1",
        digest_issue_id: null,
        paper_id: null,
        title: "Materials Group",
      },
    },
    collectable_items: [],
    eligible_workspaces: [],
    can_collect: false,
    reason_codes: ["share_kind_not_collectable"],
    notes: ["Workspace-board shares are not collectable in this phase."],
  };
}

function collectedResponse(): ResultShareCollectResponseRead {
  return {
    action: "collected",
    workspace: {
      id: "workspace-1",
      slug: "materials-group",
      name: "Materials Group",
      description: "Workspace description",
      status: "active",
    },
    collected_results: [
      {
        paper_id: "paper-1",
        status: "collected",
        reason_codes: [],
        collect_record: null,
        paper: {
          paper_id: "paper-1",
          title: "Shared Paper",
          type: "published",
          stage: "published",
          venue: "JOM",
          priority: 4,
          next_action: "Review delta",
          blocker: null,
          progress_percentage: 100,
        },
      },
    ],
    notes: ["Structured paper objects were collected into the workspace without source files."],
  };
}

function alreadyPresentResponse(): ResultShareCollectResponseRead {
  return {
    action: "already_present",
    workspace: {
      id: "workspace-1",
      slug: "materials-group",
      name: "Materials Group",
      description: "Workspace description",
      status: "active",
    },
    collected_results: [
      {
        paper_id: "paper-1",
        status: "already_present",
        reason_codes: ["already_present"],
        collect_record: null,
        paper: {
          paper_id: "paper-1",
          title: "Digest Paper A",
          type: "published",
          stage: "published",
          venue: "JOM",
          priority: 4,
          next_action: "Review A",
          blocker: null,
          progress_percentage: 100,
        },
      },
    ],
    notes: [],
  };
}

function collectionHistory(title: string): GroupWorkspaceResultCollectionRead[] {
  return [
    {
      record: {
        id: "record-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        result_share_grant_id: "share-1",
        share_kind: "paper_snapshot",
        digest_issue_id: null,
        source_pulse_card_id: null,
        source_paper_id: "paper-1",
        collected_paper_id: "paper-1",
        status: "collected",
        reason_codes: [],
        created_at: "2026-04-16T07:00:00Z",
        updated_at: "2026-04-16T07:00:00Z",
      },
      workspace: {
        id: "workspace-1",
        slug: "materials-group",
        name: "Materials Group",
        description: "Workspace description",
        status: "active",
      },
      paper: {
        paper_id: "paper-1",
        title,
        type: "published",
        stage: "published",
        venue: "JOM",
        priority: 4,
        next_action: "Review delta",
        blocker: null,
        progress_percentage: 100,
      },
    },
  ];
}

function createApiClientFactory(overrides: Partial<ResultShareApiClient> = {}) {
  return () => createClientStub(overrides);
}

function createClientStub(overrides: Partial<ResultShareApiClient>): ResultShareApiClient {
  return {
    getShareBootstrap:
      "getShareBootstrap" in overrides
        ? (overrides.getShareBootstrap as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(bootstrapFixture("digest_issue")),
    getAliasBootstrap:
      "getAliasBootstrap" in overrides
        ? (overrides.getAliasBootstrap as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(bootstrapFixture("digest_issue")),
    getShareContent:
      "getShareContent" in overrides
        ? (overrides.getShareContent as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(digestFixture()),
    getAliasContent:
      "getAliasContent" in overrides
        ? (overrides.getAliasContent as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(digestFixture()),
    getCollectPreview:
      "getCollectPreview" in overrides
        ? (overrides.getCollectPreview as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(digestPreview()),
    getAliasCollectPreview:
      "getAliasCollectPreview" in overrides
        ? (overrides.getAliasCollectPreview as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(digestPreview()),
    postCollect:
      "postCollect" in overrides
        ? (overrides.postCollect as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(collectedResponse()),
    postAliasCollect:
      "postAliasCollect" in overrides
        ? (overrides.postAliasCollect as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(collectedResponse()),
    listWorkspaceResultCollections:
      "listWorkspaceResultCollections" in overrides
        ? (overrides.listWorkspaceResultCollections as ReturnType<typeof vi.fn>)
        : vi.fn().mockResolvedValue(collectionHistory("Shared Paper")),
  };
}

describe("result share shell", () => {
  it("renders the token entry state by default", () => {
    render(<ResultShareShell />);

    expect(screen.getByRole("heading", { name: /open a read-only structured share/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /open share/i })).toBeVisible();
  });

  it("loads and renders a digest share from the /share/<token> path", async () => {
    const apiClientFactory = createApiClientFactory({
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

  it("loads and renders a digest share from the /share-alias/<alias> path", async () => {
    const apiClientFactory = createApiClientFactory({
      getAliasBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("digest_issue")),
      getAliasContent: vi.fn().mockResolvedValue(digestFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share-alias/alias-123", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Focus summary")).toBeVisible();
    expect(screen.getByText("Today Focus")).toBeVisible();
    expect(screen.getByText("alias")).toBeVisible();
  });

  it("supports paper_snapshot collect preview and collect with a self-service token", async () => {
    const user = userEvent.setup();
    const getCollectPreview = vi
      .fn()
      .mockResolvedValueOnce(paperSnapshotPreview())
      .mockResolvedValueOnce(paperSnapshotPreview());
    const listWorkspaceResultCollections = vi
      .fn()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(collectionHistory("Shared Paper"));
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("paper_snapshot")),
      getShareContent: vi.fn().mockResolvedValue(paperFixture()),
      getCollectPreview,
      postCollect: vi.fn().mockResolvedValue(collectedResponse()),
      listWorkspaceResultCollections,
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/share token/i), "paper-share-token");
    await user.click(screen.getByRole("button", { name: /open share/i }));
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Shared Paper",
      }),
    ).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "self-service-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Review workspace intake options")).toBeVisible();
    expect(screen.getByText("Single paper flow")).toBeVisible();

    await user.click(screen.getByRole("button", { name: /collect into workspace/i }));

    expect(await screen.findByText("Collected into workspace")).toBeVisible();
    expect(screen.getByText(/without source files/i)).toBeVisible();
    expect(screen.getByText("Current self-service collection history")).toBeVisible();
  });

  it("supports alias-based paper_snapshot collect preview and collect", async () => {
    const user = userEvent.setup();
    const getAliasCollectPreview = vi
      .fn()
      .mockResolvedValueOnce(paperSnapshotPreview())
      .mockResolvedValueOnce(paperSnapshotPreview());
    const postAliasCollect = vi.fn().mockResolvedValue(collectedResponse());
    const listWorkspaceResultCollections = vi
      .fn()
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(collectionHistory("Shared Paper"));
    const apiClientFactory = createApiClientFactory({
      getAliasBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("paper_snapshot")),
      getAliasContent: vi.fn().mockResolvedValue(paperFixture()),
      getAliasCollectPreview,
      postAliasCollect,
      listWorkspaceResultCollections,
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.selectOptions(screen.getByLabelText(/share access mode/i), "alias");
    await user.type(screen.getByLabelText(/share alias/i), "paper-share-alias");
    await user.click(screen.getByRole("button", { name: /open share/i }));
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Shared Paper",
      }),
    ).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "self-service-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Review workspace intake options")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /collect into workspace/i }));

    expect(await screen.findByText("Collected into workspace")).toBeVisible();
    expect(postAliasCollect).toHaveBeenCalledWith(
      "paper-share-alias",
      "self-service-token",
      expect.any(Object),
    );
  });

  it("requires explicit paper selection for multi-paper digest collect", async () => {
    const user = userEvent.setup();
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("digest_issue")),
      getShareContent: vi.fn().mockResolvedValue(digestFixture()),
      getCollectPreview: vi
        .fn()
        .mockResolvedValueOnce(digestPreview())
        .mockResolvedValueOnce(digestPreview()),
      postCollect: vi.fn().mockResolvedValue(alreadyPresentResponse()),
      listWorkspaceResultCollections: vi
        .fn()
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(collectionHistory("Digest Paper A")),
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/share token/i), "digest-share-token");
    await user.click(screen.getByRole("button", { name: /open share/i }));
    await user.type(screen.getByLabelText(/self-service token/i), "self-service-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Explicit paper selection required")).toBeVisible();
    const collectButton = screen.getByRole("button", { name: /collect into workspace/i });
    expect(collectButton).toBeDisabled();

    await user.click(screen.getAllByRole("checkbox")[0]);
    await waitFor(() => expect(collectButton).toBeEnabled());

    await user.click(collectButton);
    expect(await screen.findByText("Already present")).toBeVisible();
  });

  it("shows workspace_board shares as non-collectable in v1", async () => {
    const user = userEvent.setup();
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("workspace_board")),
      getShareContent: vi.fn().mockResolvedValue(workspaceFixture()),
      getCollectPreview: vi.fn().mockResolvedValue(boardPreview()),
      listWorkspaceResultCollections: vi.fn().mockResolvedValue([]),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share/workspace-token", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Workspace description")).toBeVisible();
    expect(screen.getByText("Invite and join stay in a separate flow")).toBeVisible();
    expect(screen.getByText(/separate invite token required/i)).toBeVisible();
    expect(screen.getByText("http://127.0.0.1:5177")).toBeVisible();
    expect(screen.getByRole("link", { name: /open invite entry/i })).toHaveAttribute(
      "href",
      "http://127.0.0.1:8000/result-shares/workspace-token/invite-handoff",
    );
    expect(screen.getByText("Next step: collect papers into this workspace")).toBeVisible();
    expect(screen.getByText(/separate result share token required/i)).toBeVisible();
    expect(screen.getByText("http://127.0.0.1:5174")).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "self-service-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Not collectable in v1")).toBeVisible();
    expect(screen.getByText(/share kind not collectable/i)).toBeVisible();
  });

  it("renders workspace_board shares through alias mode without changing handoff behavior", async () => {
    const apiClientFactory = createApiClientFactory({
      getAliasBootstrap: vi.fn().mockResolvedValue(bootstrapFixture("workspace_board")),
      getAliasContent: vi.fn().mockResolvedValue(workspaceFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share-alias/workspace-alias", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Workspace description")).toBeVisible();
    expect(screen.getByText("Invite and join stay in a separate flow")).toBeVisible();
    expect(screen.getByText("Next step: collect papers into this workspace")).toBeVisible();
    expect(screen.getByText("http://127.0.0.1:5177")).toBeVisible();
    expect(screen.getByText("http://127.0.0.1:5174")).toBeVisible();
    expect(screen.getByRole("link", { name: /open invite entry/i })).toBeVisible();
  });

  it("keeps workspace_board rendering stable when the handoff reserve is omitted", async () => {
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockResolvedValue({
        ...bootstrapFixture("workspace_board"),
        workspace_invite_handoff_reserve: null,
        result_collect_handoff_reserve: null,
      }),
      getShareContent: vi.fn().mockResolvedValue(workspaceFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share/workspace-no-handoff", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Workspace description")).toBeVisible();
    expect(screen.queryByText("Invite and join stay in a separate flow")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Next step: collect papers into this workspace"),
    ).not.toBeInTheDocument();
  });

  it("does not show the invite handoff CTA when the backend omits the redirect URL", async () => {
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockResolvedValue({
        ...bootstrapFixture("workspace_board"),
        workspace_invite_handoff_reserve: {
          ...bootstrapFixture("workspace_board").workspace_invite_handoff_reserve!,
          handoff_redirect_supported: false,
          invite_handoff_url: null,
        },
      }),
      getShareContent: vi.fn().mockResolvedValue(workspaceFixture()),
    });

    render(
      <ResultShareShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/share/workspace-no-cta", search: "", hash: "" }}
      />,
    );

    expect(await screen.findByText("Workspace description")).toBeVisible();
    expect(screen.queryByRole("link", { name: /open invite entry/i })).not.toBeInTheDocument();
  });

  it("shows a clear invalid token state when the share token is revoked or invalid", async () => {
    const user = userEvent.setup();
    const apiClientFactory = createApiClientFactory({
      getShareBootstrap: vi.fn().mockRejectedValue(
        new ResultShareApiError({
          status: 401,
          detail: "result share grant has expired",
          body: null,
          kind: "expired_token",
        }),
      ),
    });

    render(<ResultShareShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/share token/i), "expired-token");
    await user.click(screen.getByRole("button", { name: /open share/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Share link expired");
    });
  });
});
