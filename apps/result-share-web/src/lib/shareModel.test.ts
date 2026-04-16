import type {
  ResultShareCollectPreviewRead,
  ResultShareCollectResponseRead,
  ResultShareApiErrorShape,
  SharedDigestIssueRead,
  SharedPaperSnapshotRead,
  SharedWorkspaceBoardRead,
  ShareGrantBootstrapRead,
} from "./types";
import {
  buildCollectActionResultViewModel,
  buildDigestShareViewModel,
  buildPaperSnapshotViewModel,
  buildResultCollectViewModel,
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
    collection_reserve: {
      supported: kind !== "workspace_board",
      share_kind_collectable: kind !== "workspace_board",
      collect_supported_via_self_service: kind !== "workspace_board",
      source_files_included: false,
      notes: ["Source files remain excluded."],
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
            notes: ["Joining requires a separate invite token."],
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
            handoff_redirect_supported: true,
            source_files_included: false,
            supported_share_kinds: ["digest_issue", "paper_snapshot"],
            result_share_shell_entry_url: "http://127.0.0.1:5174",
            collect_handoff_url: "/result-shares/workspace-token/collect-handoff",
            notes: ["Collecting papers requires a separate digest or paper share token."],
          }
        : null,
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
    const workspaceViewModel = buildWorkspaceBoardViewModel(
      bootstrapFixture("workspace_board"),
      workspace,
      "http://127.0.0.1:8000",
    );
    expect(workspaceViewModel.memberCount).toBe(1);
    expect(workspaceViewModel.workspaceInviteHandoff?.inviteShellEntryUrl).toBe(
      "http://127.0.0.1:5177",
    );
    expect(workspaceViewModel.workspaceInviteHandoff?.handoffRedirectSupported).toBe(true);
    expect(workspaceViewModel.workspaceInviteHandoff?.inviteHandoffUrl).toBe(
      "http://127.0.0.1:8000/result-shares/workspace-token/invite-handoff",
    );
    expect(workspaceViewModel.workspaceInviteHandoff?.directClaimViaSharePage).toBe(false);
    expect(workspaceViewModel.resultCollectHandoff?.resultShareShellEntryUrl).toBe(
      "http://127.0.0.1:5174",
    );
    expect(workspaceViewModel.resultCollectHandoff?.handoffRedirectSupported).toBe(true);
    expect(workspaceViewModel.resultCollectHandoff?.collectHandoffUrl).toBe(
      "http://127.0.0.1:8000/result-shares/workspace-token/collect-handoff",
    );
    expect(workspaceViewModel.resultCollectHandoff?.directCollectViaCurrentShare).toBe(false);
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

  it("shapes collect preview for paper snapshots and digests", () => {
    const singlePaperPreview: ResultShareCollectPreviewRead = {
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
    const multiDigestPreview: ResultShareCollectPreviewRead = {
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
      eligible_workspaces: [],
      can_collect: false,
      reason_codes: ["paper_selection_required", "no_eligible_workspace_membership"],
      notes: ["Explicit paper selection is required for multi-paper digest collect."],
    };

    expect(
      buildResultCollectViewModel(bootstrapFixture("paper_snapshot"), singlePaperPreview),
    ).toMatchObject({
      shareKind: "paper_snapshot",
      collectionSupported: true,
      requiresPaperSelection: false,
      canCollect: true,
    });
    expect(
      buildResultCollectViewModel(bootstrapFixture("digest_issue"), multiDigestPreview),
    ).toMatchObject({
      shareKind: "digest_issue",
      requiresPaperSelection: true,
      reasonCodes: ["paper_selection_required", "no_eligible_workspace_membership"],
    });
  });

  it("shapes collect action results for collected and already-present outcomes", () => {
    const collectedResponse: ResultShareCollectResponseRead = {
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
      notes: ["Collected without source files."],
    };
    const alreadyPresentResponse: ResultShareCollectResponseRead = {
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

    expect(buildCollectActionResultViewModel(collectedResponse).title).toBe(
      "Collected into workspace",
    );
    expect(buildCollectActionResultViewModel(alreadyPresentResponse).title).toBe(
      "Already present",
    );
  });
});
