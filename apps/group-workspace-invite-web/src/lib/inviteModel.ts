import type {
  ApiErrorViewModel,
  GroupWorkspaceInviteBootstrapRead,
  GroupWorkspaceInviteClaimPreviewRead,
  GroupWorkspaceInviteClaimResponse,
  GroupWorkspaceInvitePublicSummaryRead,
  GroupWorkspaceInviteApiErrorShape,
  InvitePageViewModel,
  MembershipStatusViewModel,
} from "./types";

function formatCountLabel(
  invite: GroupWorkspaceInvitePublicSummaryRead,
  remainingClaims: number | null,
): string {
  if (remainingClaims === null) {
    if (invite.max_claims === null) {
      return "Multi-use invite";
    }
    return `${invite.claim_count} / ${invite.max_claims} claims used`;
  }
  return `${remainingClaims} claim slot(s) remaining`;
}

export function formatReasonCode(reasonCode: string): string {
  return reasonCode
    .split("_")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

export function buildInvitePageViewModel(
  bootstrap: GroupWorkspaceInviteBootstrapRead,
): InvitePageViewModel {
  const notes = [
    "This invite shares workspace membership access only.",
    "Source files are not included.",
    "Claiming membership requires a self-service token.",
    ...bootstrap.notes,
  ];
  return {
    pageTitle: bootstrap.workspace.name,
    pageSubtitle: `Join ${bootstrap.workspace.slug} as ${bootstrap.role_to_assign}.`,
    workspaceName: bootstrap.workspace.name,
    workspaceSlug: bootstrap.workspace.slug,
    workspaceDescription: bootstrap.workspace.description,
    workspaceStatus: bootstrap.workspace.status,
    roleToAssign: bootstrap.role_to_assign,
    inviteStatus: bootstrap.invite.status,
    displayLabel: bootstrap.invite.display_label,
    remainingClaimsText: formatCountLabel(bootstrap.invite, bootstrap.remaining_claims),
    expiresAtText: bootstrap.expires_at ?? "No expiry set",
    notes,
  };
}

export function buildClaimPreviewStatusViewModel(
  preview: GroupWorkspaceInviteClaimPreviewRead,
): MembershipStatusViewModel {
  if (preview.current_membership) {
    return {
      kind: "already_member",
      title: "Already a member",
      message:
        "This self-service grant is already linked to the workspace. No duplicate membership will be created.",
      reasonCodes:
        preview.reason_codes.length > 0 ? preview.reason_codes : ["already_member"],
      canClaim: false,
      membership: preview.current_membership,
    };
  }
  if (preview.can_claim) {
    return {
      kind: "claimable",
      title: "Ready to claim",
      message:
        "This self-service grant can claim workspace membership through the current self-service boundary.",
      reasonCodes: preview.reason_codes,
      canClaim: true,
      membership: null,
    };
  }
  return {
    kind: "rejected",
    title: "Cannot claim yet",
    message:
      "The current self-service grant cannot claim this invite. Review the reason codes before trying again.",
    reasonCodes: preview.reason_codes,
    canClaim: false,
    membership: null,
  };
}

export function buildClaimResultStatusViewModel(
  response: GroupWorkspaceInviteClaimResponse,
): MembershipStatusViewModel {
  if (response.action === "claimed") {
    return {
      kind: "claimed",
      title: "Membership claimed",
      message:
        "Workspace membership was created successfully through the current self-service boundary.",
      reasonCodes: response.invite_claim?.reason_codes ?? [],
      canClaim: false,
      membership: response.membership,
    };
  }
  if (response.action === "already_member") {
    return {
      kind: "already_member",
      title: "Already a member",
      message:
        "This self-service grant already belongs to the target workspace. The membership was reused deterministically.",
      reasonCodes: response.invite_claim?.reason_codes ?? ["already_member"],
      canClaim: false,
      membership: response.membership,
    };
  }
  return {
    kind: "rejected",
    title: "Claim rejected",
    message:
      "The invite could not be claimed through the current self-service boundary.",
    reasonCodes: response.invite_claim?.reason_codes ?? [],
    canClaim: false,
    membership: response.membership,
  };
}

export function buildInviteErrorViewModel(
  error: Pick<GroupWorkspaceInviteApiErrorShape, "kind" | "detail">,
): ApiErrorViewModel {
  switch (error.kind) {
    case "revoked_invite":
      return {
        kind: error.kind,
        title: "Invite revoked",
        message: error.detail,
      };
    case "expired_invite":
      return {
        kind: error.kind,
        title: "Invite expired",
        message: error.detail,
      };
    case "invite_exhausted":
      return {
        kind: error.kind,
        title: "Invite exhausted",
        message: error.detail,
      };
    case "unauthorized_self_service":
      return {
        kind: error.kind,
        title: "Self-service token rejected",
        message: error.detail,
      };
    case "invalid_invite":
      return {
        kind: error.kind,
        title: "Invite not found",
        message: error.detail,
      };
    case "network_error":
      return {
        kind: error.kind,
        title: "Network request failed",
        message: error.detail,
      };
    default:
      return {
        kind: error.kind,
        title: "Invite request failed",
        message: error.detail,
      };
  }
}
