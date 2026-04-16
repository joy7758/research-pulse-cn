import type {
  ResultShareApiErrorShape,
  SharedDigestIssueRead,
  SharedPaperSnapshotRead,
  SharedWorkspaceBoardRead,
  ShareGrantBootstrapRead,
} from "./types";
import {
  buildDigestShareViewModel,
  buildPaperSnapshotViewModel,
  buildShareErrorViewModel,
  buildWorkspaceBoardViewModel,
} from "./shareModel";

function bootstrapFixture(kind: ShareGrantBootstrapRead["grant"]["share_kind"]): ShareGrantBootstrapRead {
  return {
    grant: {
      id: "grant-1",
      share_kind: kind,
      display_label: "Weekly share",
      status: "active",
      expires_at: null,
      created_at: "2026-04-16T06:00:00Z",
    },
    target: {
      workspace_id: kind === "workspace_board" ? "workspace-1" : null,
      digest_issue_id: kind === "digest_issue" ? "digest-1" : null,
      paper_id: kind === "paper_snapshot" ? "paper-1" : null,
      title: kind === "workspace_board" ? "Materials Group" : "Shared Target",
    },
    notes: ["Structured read-only share."],
  };
}

describe("result share view shaping", () => {
  it("prefers structured digest sections when present", () => {
    const digest: SharedDigestIssueRead = {
      share_kind: "digest_issue",
      id: "digest-1",
      issue_date: "2026-04-16",
      status: "ready",
      title: "Digest title",
      summary: "Digest summary",
      highlight_count: 2,
      selected_card_count: 2,
      deep_link_path: "/mini/pulse-digests/user-1/2026-04-16",
      highlights: [],
      is_structured: true,
      fallback_mode: "structured",
      section_order: ["today_focus", "signal_updates"],
      sections: [
        {
          kind: "signal_updates",
          title: "Signal Updates",
          item_count: 1,
          items: [
            {
              sort_order: 2,
              pulse_card_id: "card-2",
              card_type: "signal_change",
              source_paper_id: null,
              title: "Signal moved",
              summary: "Signal summary",
              why_now: null,
              action_text: null,
              deep_link: null,
              paper: null,
            },
          ],
        },
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
              title: "Focus now",
              summary: "Focus summary",
              why_now: "Why now",
              action_text: "Do it",
              deep_link: "/papers/paper-1",
              paper: null,
            },
          ],
        },
      ],
      quick_stats: {
        selected_card_count: 2,
        related_paper_count: 0,
        signal_update_count: 1,
        touched_paper_count: 1,
      },
      focus_card: null,
      publication_preview: {
        digest_title: "Publication digest title",
        digest_subtitle: "Publication digest subtitle",
        digest_highlights: [],
        primary_cta_text: "Read digest",
        primary_cta_path: "/mini/pulse-digests/user-1/2026-04-16",
        mini_program_path: "mini/path",
        article_url: null,
      },
      items: [],
    };

    const viewModel = buildDigestShareViewModel(bootstrapFixture("digest_issue"), digest);

    expect(viewModel.pageTitle).toBe("Publication digest title");
    expect(viewModel.sectionViews.map((section) => section.kind)).toEqual([
      "today_focus",
      "signal_updates",
    ]);
  });

  it("falls back to grouped legacy digest highlights when structured sections are absent", () => {
    const digest: SharedDigestIssueRead = {
      share_kind: "digest_issue",
      id: "digest-legacy-1",
      issue_date: "2026-04-16",
      status: "ready",
      title: "Legacy Digest",
      summary: "Legacy summary",
      highlight_count: 2,
      selected_card_count: 2,
      deep_link_path: null,
      highlights: [
        {
          sort_order: 1,
          pulse_card_id: "card-1",
          card_type: "today_suggestion",
          source_paper_id: "paper-1",
          title: "Focus",
          summary: "Focus summary",
          why_now: null,
          action_text: null,
          deep_link: null,
          paper: null,
        },
        {
          sort_order: 2,
          pulse_card_id: "card-2",
          card_type: "related_paper",
          source_paper_id: null,
          title: "Related",
          summary: "Related summary",
          why_now: null,
          action_text: null,
          deep_link: null,
          paper: null,
        },
      ],
      is_structured: false,
      fallback_mode: "highlights_only",
      section_order: [],
      sections: [],
      quick_stats: null,
      focus_card: null,
      publication_preview: null,
      items: [],
    };

    const viewModel = buildDigestShareViewModel(bootstrapFixture("digest_issue"), digest);

    expect(viewModel.sectionViews.map((section) => section.kind)).toEqual([
      "today_focus",
      "related_papers",
    ]);
  });

  it("shapes paper snapshot and workspace board views", () => {
    const paper: SharedPaperSnapshotRead = {
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
    const workspace: SharedWorkspaceBoardRead = {
      share_kind: "workspace_board",
      workspace: {
        id: "workspace-1",
        slug: "materials-group",
        name: "Materials Group",
        description: "Description",
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
      papers: [paper],
      quick_stats: {
        member_count: 1,
        paper_count: 1,
        blocked_paper_count: 0,
        papers_with_signals_count: 1,
      },
    };

    expect(buildPaperSnapshotViewModel(bootstrapFixture("paper_snapshot"), paper).pageTitle).toBe(
      "Shared Paper",
    );
    expect(
      buildWorkspaceBoardViewModel(bootstrapFixture("workspace_board"), workspace).memberCount,
    ).toBe(1);
  });

  it("maps invalid, revoked, and expired token failures to clear public states", () => {
    const revokedError: ResultShareApiErrorShape = {
      status: 401,
      detail: "result share grant has been revoked",
      body: null,
      kind: "revoked_token",
    };
    const expiredError: ResultShareApiErrorShape = {
      status: 401,
      detail: "result share grant has expired",
      body: null,
      kind: "expired_token",
    };
    const invalidError: ResultShareApiErrorShape = {
      status: 401,
      detail: "result share grant was not found",
      body: null,
      kind: "invalid_token",
    };

    expect(buildShareErrorViewModel(revokedError).title).toBe("Share link revoked");
    expect(buildShareErrorViewModel(expiredError).title).toBe("Share link expired");
    expect(buildShareErrorViewModel(invalidError).title).toBe("Invalid share link");
  });
});
