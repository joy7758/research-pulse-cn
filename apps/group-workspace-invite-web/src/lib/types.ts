export type InviteGrantStatus = "active" | "revoked" | "expired" | "exhausted" | string;
export type GroupWorkspaceStatus = "active" | "archived" | string;
export type InviteClaimAction = "claimed" | "already_member" | "rejected";
export type InviteClaimStatus = "claimed" | "already_member" | "rejected" | string;
export type InviteRole = "editor" | "viewer" | string;
export type InviteApiErrorKind =
  | "invalid_invite"
  | "revoked_invite"
  | "expired_invite"
  | "invite_exhausted"
  | "unauthorized_self_service"
  | "request_failed"
  | "network_error";

export type GroupWorkspaceSafeSummaryRead = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: GroupWorkspaceStatus;
};

export type GroupWorkspaceInvitePublicSummaryRead = {
  id: string;
  workspace_id: string;
  role_to_assign: InviteRole;
  status: InviteGrantStatus;
  display_label: string | null;
  max_claims: number | null;
  claim_count: number;
  expires_at: string | null;
  created_at: string;
};

export type GroupWorkspaceInviteBootstrapRead = {
  invite: GroupWorkspaceInvitePublicSummaryRead;
  workspace: GroupWorkspaceSafeSummaryRead;
  role_to_assign: InviteRole;
  remaining_claims: number | null;
  expires_at: string | null;
  notes: string[];
};

export type GroupWorkspaceMembershipRead = {
  member_id: string;
  workspace_id: string;
  user_id: string;
  role: InviteRole;
  joined_at: string;
  workspace_summary: GroupWorkspaceSafeSummaryRead;
};

export type GroupWorkspaceInviteClaimRead = {
  id: string;
  invite_grant_id: string;
  workspace_id: string;
  user_id: string;
  membership_id: string | null;
  role_assigned: InviteRole;
  claim_status: InviteClaimStatus;
  reason_codes: string[];
  created_at: string;
  updated_at: string;
  claimed_at: string | null;
};

export type GroupWorkspaceInviteClaimPreviewRead = {
  can_claim: boolean;
  reason_codes: string[];
  current_membership: GroupWorkspaceMembershipRead | null;
  invite: GroupWorkspaceInvitePublicSummaryRead | null;
  workspace: GroupWorkspaceSafeSummaryRead | null;
};

export type GroupWorkspaceInviteClaimResponse = {
  action: InviteClaimAction;
  membership: GroupWorkspaceMembershipRead | null;
  invite_claim: GroupWorkspaceInviteClaimRead | null;
  invite: GroupWorkspaceInvitePublicSummaryRead | null;
  workspace: GroupWorkspaceSafeSummaryRead | null;
};

export type GroupWorkspaceInviteApiErrorShape = {
  status: number | null;
  detail: string;
  body: unknown;
  kind: InviteApiErrorKind;
};

export type ApiErrorViewModel = {
  kind: InviteApiErrorKind;
  title: string;
  message: string;
};

export type InvitePageViewModel = {
  pageTitle: string;
  pageSubtitle: string;
  workspaceName: string;
  workspaceSlug: string;
  workspaceDescription: string | null;
  workspaceStatus: string;
  roleToAssign: string;
  inviteStatus: string;
  displayLabel: string | null;
  remainingClaimsText: string;
  expiresAtText: string;
  notes: string[];
};

export type MembershipStatusViewModel = {
  kind: "claimable" | "already_member" | "claimed" | "rejected";
  title: string;
  message: string;
  reasonCodes: string[];
  canClaim: boolean;
  membership: GroupWorkspaceMembershipRead | null;
};
