import {
  buildClaimPreviewStatusViewModel,
  buildClaimResultStatusViewModel,
  buildInviteErrorViewModel,
  buildInvitePageViewModel,
  buildResultCollectHandoffViewModel,
} from "./inviteModel";
import type {
  GroupWorkspaceInviteBootstrapRead,
  GroupWorkspaceInviteClaimPreviewRead,
  GroupWorkspaceInviteClaimResponse,
  ResultCollectHandoffReserveRead,
} from "./types";

function resultCollectHandoffFixture(): ResultCollectHandoffReserveRead {
  return {
    supported: true,
    separate_result_share_token_required: true,
    result_share_bootstrap_available: true,
    collect_supported_via_self_service: true,
    direct_collect_via_invite_page: false,
    source_files_included: false,
    supported_share_kinds: ["digest_issue", "paper_snapshot"],
    result_share_shell_entry_url: "http://127.0.0.1:5174",
    notes: ["Collecting shared results requires a separate result-share token."],
  };
}

function bootstrapFixture(): GroupWorkspaceInviteBootstrapRead {
  return {
    invite: {
      id: "invite-1",
      workspace_id: "workspace-1",
      role_to_assign: "editor",
      status: "active",
      display_label: "Materials Lab Invite",
      max_claims: 3,
      claim_count: 1,
      expires_at: "2026-04-19T09:16:05Z",
      created_at: "2026-04-16T09:16:05Z",
    },
    workspace: {
      id: "workspace-1",
      slug: "materials-lab",
      name: "Materials Lab",
      description: "Shared methods workspace",
      status: "active",
    },
    role_to_assign: "editor",
    remaining_claims: 2,
    expires_at: "2026-04-19T09:16:05Z",
    result_collect_handoff_reserve: resultCollectHandoffFixture(),
    notes: ["Safe summary only."],
  };
}

describe("group workspace invite view shaping", () => {
  it("builds the bootstrap view model with safe notes", () => {
    const viewModel = buildInvitePageViewModel(bootstrapFixture());

    expect(viewModel.workspaceSlug).toBe("materials-lab");
    expect(viewModel.remainingClaimsText).toContain("2 claim slot");
    expect(viewModel.notes).toContain("Source files are not included.");
  });

  it("builds claim preview states for claimable and already_member flows", () => {
    const claimable: GroupWorkspaceInviteClaimPreviewRead = {
      can_claim: true,
      reason_codes: [],
      current_membership: null,
      invite: bootstrapFixture().invite,
      workspace: bootstrapFixture().workspace,
      result_collect_handoff_reserve: resultCollectHandoffFixture(),
    };
    const alreadyMember: GroupWorkspaceInviteClaimPreviewRead = {
      can_claim: false,
      reason_codes: ["already_member"],
      current_membership: {
        member_id: "member-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        role: "editor",
        joined_at: "2026-04-16T09:16:05Z",
        workspace_summary: bootstrapFixture().workspace,
        result_collect_handoff_reserve: resultCollectHandoffFixture(),
      },
      invite: bootstrapFixture().invite,
      workspace: bootstrapFixture().workspace,
      result_collect_handoff_reserve: resultCollectHandoffFixture(),
    };

    expect(buildClaimPreviewStatusViewModel(claimable)).toMatchObject({
      kind: "claimable",
      canClaim: true,
    });
    expect(buildClaimPreviewStatusViewModel(alreadyMember)).toMatchObject({
      kind: "already_member",
      canClaim: false,
    });
  });

  it("builds claim result states for claimed and rejected responses", () => {
    const claimed: GroupWorkspaceInviteClaimResponse = {
      action: "claimed",
      membership: {
        member_id: "member-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        role: "editor",
        joined_at: "2026-04-16T09:16:05Z",
        workspace_summary: bootstrapFixture().workspace,
        result_collect_handoff_reserve: resultCollectHandoffFixture(),
      },
      invite_claim: {
        id: "claim-1",
        invite_grant_id: "invite-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        membership_id: "member-1",
        role_assigned: "editor",
        claim_status: "claimed",
        reason_codes: [],
        created_at: "2026-04-16T09:16:05Z",
        updated_at: "2026-04-16T09:16:05Z",
        claimed_at: "2026-04-16T09:16:05Z",
      },
      invite: bootstrapFixture().invite,
      workspace: bootstrapFixture().workspace,
      result_collect_handoff_reserve: resultCollectHandoffFixture(),
    };
    const rejected: GroupWorkspaceInviteClaimResponse = {
      action: "rejected",
      membership: null,
      invite_claim: {
        id: "claim-2",
        invite_grant_id: "invite-1",
        workspace_id: "workspace-1",
        user_id: "user-1",
        membership_id: null,
        role_assigned: "editor",
        claim_status: "rejected",
        reason_codes: ["invite_revoked"],
        created_at: "2026-04-16T09:16:05Z",
        updated_at: "2026-04-16T09:16:05Z",
        claimed_at: null,
      },
      invite: bootstrapFixture().invite,
      workspace: bootstrapFixture().workspace,
      result_collect_handoff_reserve: resultCollectHandoffFixture(),
    };

    expect(buildClaimResultStatusViewModel(claimed)).toMatchObject({
      kind: "claimed",
      membership: claimed.membership,
    });
    expect(buildClaimResultStatusViewModel(rejected)).toMatchObject({
      kind: "rejected",
      reasonCodes: ["invite_revoked"],
    });
  });

  it("builds result-collect handoff copy from the reserve block", () => {
    expect(buildResultCollectHandoffViewModel(resultCollectHandoffFixture())).toMatchObject({
      title: "Next step: collect shared results",
      directCollectViaInvitePage: false,
      supportedShareKindsText: "digest_issue, paper_snapshot",
      resultShareShellEntryUrl: "http://127.0.0.1:5174",
    });
  });

  it("maps API errors into invite-friendly copy", () => {
    expect(
      buildInviteErrorViewModel({ kind: "expired_invite", detail: "invite has expired" }),
    ).toMatchObject({
      title: "Invite expired",
    });
    expect(
      buildInviteErrorViewModel({
        kind: "unauthorized_self_service",
        detail: "Not authenticated",
      }),
    ).toMatchObject({
      title: "Self-service token rejected",
    });
  });
});
