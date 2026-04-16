import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { GroupWorkspaceInviteShell } from "./App";
import { GroupWorkspaceInviteApiError } from "./lib/apiClient";
import type {
  GroupWorkspaceInviteBootstrapRead,
  GroupWorkspaceInviteClaimPreviewRead,
  GroupWorkspaceInviteClaimResponse,
  GroupWorkspaceMembershipRead,
} from "./lib/types";

function bootstrapFixture(): GroupWorkspaceInviteBootstrapRead {
  return {
    invite: {
      id: "invite-1",
      workspace_id: "workspace-1",
      role_to_assign: "editor",
      status: "active",
      display_label: "Materials invite",
      max_claims: 3,
      claim_count: 0,
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
    remaining_claims: 3,
    expires_at: "2026-04-19T09:16:05Z",
    notes: ["Safe summary only."],
  };
}

function membershipsFixture(): GroupWorkspaceMembershipRead[] {
  return [
    {
      member_id: "member-1",
      workspace_id: "workspace-1",
      user_id: "user-1",
      role: "editor",
      joined_at: "2026-04-16T09:16:05Z",
      workspace_summary: bootstrapFixture().workspace,
    },
  ];
}

function claimablePreviewFixture(): GroupWorkspaceInviteClaimPreviewRead {
  return {
    can_claim: true,
    reason_codes: [],
    current_membership: null,
    invite: bootstrapFixture().invite,
    workspace: bootstrapFixture().workspace,
  };
}

function alreadyMemberPreviewFixture(): GroupWorkspaceInviteClaimPreviewRead {
  return {
    can_claim: false,
    reason_codes: ["already_member"],
    current_membership: membershipsFixture()[0],
    invite: bootstrapFixture().invite,
    workspace: bootstrapFixture().workspace,
  };
}

function claimedResponseFixture(): GroupWorkspaceInviteClaimResponse {
  return {
    action: "claimed",
    membership: membershipsFixture()[0],
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
  };
}

describe("group workspace invite shell", () => {
  it("renders the invite token entry state by default", () => {
    render(<GroupWorkspaceInviteShell />);

    expect(screen.getByRole("heading", { name: /open a safe workspace invite/i })).toBeVisible();
    expect(screen.getByRole("button", { name: /open invite/i })).toBeVisible();
  });

  it("loads and renders bootstrap data from the /invite/<token> path", async () => {
    const apiClientFactory = () => ({
      getInviteBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
      getClaimPreview: vi.fn(),
      claimInvite: vi.fn(),
      getWorkspaceMemberships: vi.fn(),
    });

    render(
      <GroupWorkspaceInviteShell
        apiClientFactory={apiClientFactory}
        locationLike={{ pathname: "/invite/token-123", search: "", hash: "" }}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Materials Lab", level: 1 }),
    ).toBeVisible();
    expect(screen.getByText("Shared methods workspace")).toBeVisible();
    expect(screen.getByText(/source files are not included/i)).toBeVisible();
  });

  it("supports manual self-service token connect and renders claim preview plus memberships", async () => {
    const user = userEvent.setup();
    const client = {
      getInviteBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
      getClaimPreview: vi.fn().mockResolvedValue(claimablePreviewFixture()),
      claimInvite: vi.fn(),
      getWorkspaceMemberships: vi.fn().mockResolvedValue(membershipsFixture()),
    };

    render(<GroupWorkspaceInviteShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/invite token/i), "manual-invite-token");
    await user.click(screen.getByRole("button", { name: /open invite/i }));

    expect(
      await screen.findByRole("heading", { name: "Materials Lab", level: 1 }),
    ).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "grant-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Ready to claim")).toBeVisible();
    expect(screen.getByText("Workspace memberships")).toBeVisible();
    expect(screen.getByText("materials-lab · active")).toBeVisible();
  });

  it("renders claim success and refreshes memberships", async () => {
    const user = userEvent.setup();
    const client = {
      getInviteBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
      getClaimPreview: vi
        .fn()
        .mockResolvedValueOnce(claimablePreviewFixture())
        .mockResolvedValueOnce(alreadyMemberPreviewFixture()),
      claimInvite: vi.fn().mockResolvedValue(claimedResponseFixture()),
      getWorkspaceMemberships: vi
        .fn()
        .mockResolvedValueOnce([])
        .mockResolvedValueOnce(membershipsFixture()),
    };

    render(<GroupWorkspaceInviteShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/invite token/i), "manual-invite-token");
    await user.click(screen.getByRole("button", { name: /open invite/i }));
    expect(
      await screen.findByRole("heading", { name: "Materials Lab", level: 1 }),
    ).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "grant-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));
    expect(await screen.findByText("Ready to claim")).toBeVisible();

    await user.click(screen.getByRole("button", { name: /claim membership/i }));
    expect(await screen.findByText("Membership claimed")).toBeVisible();
    expect(screen.getByText("materials-lab · active")).toBeVisible();
  });

  it("renders already_member state without duplicate claim language", async () => {
    const user = userEvent.setup();
    const client = {
      getInviteBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
      getClaimPreview: vi.fn().mockResolvedValue(alreadyMemberPreviewFixture()),
      claimInvite: vi.fn(),
      getWorkspaceMemberships: vi.fn().mockResolvedValue(membershipsFixture()),
    };

    render(<GroupWorkspaceInviteShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/invite token/i), "manual-invite-token");
    await user.click(screen.getByRole("button", { name: /open invite/i }));
    expect(
      await screen.findByRole("heading", { name: "Materials Lab", level: 1 }),
    ).toBeVisible();

    await user.type(screen.getByLabelText(/self-service token/i), "grant-token");
    await user.click(screen.getByRole("button", { name: /connect self-service token/i }));

    expect(await screen.findByText("Already a member")).toBeVisible();
    expect(screen.getByText(/no duplicate membership will be created/i)).toBeVisible();
  });

  it("shows a clear revoked or expired invite state when bootstrap fails", async () => {
    const user = userEvent.setup();
    const apiClientFactory = () => ({
      getInviteBootstrap: vi.fn().mockRejectedValue(
        new GroupWorkspaceInviteApiError({
          status: 401,
          detail: "group workspace invite has expired",
          body: null,
          kind: "expired_invite",
        }),
      ),
      getClaimPreview: vi.fn(),
      claimInvite: vi.fn(),
      getWorkspaceMemberships: vi.fn(),
    });

    render(<GroupWorkspaceInviteShell apiClientFactory={apiClientFactory} />);

    await user.type(screen.getByLabelText(/invite token/i), "expired-token");
    await user.click(screen.getByRole("button", { name: /open invite/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invite expired");
    });
  });

  it("moves query or fragment tokens into memory and clears visible url hints", async () => {
    const replaceState = vi.fn();
    const client = {
      getInviteBootstrap: vi.fn().mockResolvedValue(bootstrapFixture()),
      getClaimPreview: vi.fn().mockResolvedValue(claimablePreviewFixture()),
      claimInvite: vi.fn(),
      getWorkspaceMemberships: vi.fn().mockResolvedValue(membershipsFixture()),
    };

    render(
      <GroupWorkspaceInviteShell
        apiClientFactory={() => client}
        historyLike={{ replaceState }}
        locationLike={{
          pathname: "/join",
          search: "?invite_token=query-invite",
          hash: "#self_service_token=fragment-grant&tab=invite",
        }}
      />,
    );

    expect(
      await screen.findByRole("heading", { name: "Materials Lab", level: 1 }),
    ).toBeVisible();
    expect(await screen.findByText(/self-service token was moved from the url/i)).toBeVisible();
    expect(replaceState).toHaveBeenCalledWith(null, "", "/join#tab=invite");
  });
});
