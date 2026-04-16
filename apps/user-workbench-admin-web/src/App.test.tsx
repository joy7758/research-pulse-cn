import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { UserWorkbenchAdminShell } from "./App";

function userSummaryFixture() {
  return {
    id: "user-1",
    name: "Workbench User",
    email: "user@example.com",
    field: "Materials",
    paper_count: 1,
    watch_profile_count: 1,
    workspace_count: 1,
    latest_digest_issue_summary: {
      id: "digest-1",
      user_id: "user-1",
      issue_date: "2026-04-16",
      status: "ready",
      title: "Digest title",
      summary: "Digest summary",
      selected_card_count: 2,
      published_at: null,
      deep_link_path: "/mini/digest",
    },
  };
}

function userDetailFixture() {
  return {
    user: userSummaryFixture(),
    papers: [
      {
        id: "paper-1",
        user_id: "user-1",
        user_name: "Workbench User",
        user_email: "user@example.com",
        title: "Paper Title",
        type: "published",
        stage: "published",
        venue: "JOM",
        priority: 4,
        next_action: "Review delta",
        blocker: null,
        last_touch_at: "2026-04-16T06:00:00Z",
        progress_percentage: 100,
        latest_signal_summary: null,
        linked_watch_profiles: [
          {
            id: "watch-1",
            label: "Watch label",
            enabled: true,
            source_mode: "manual",
          },
        ],
      },
    ],
    watch_profiles: [
      {
        id: "watch-1",
        user_id: "user-1",
        paper_id: "paper-1",
        label: "Watch label",
        enabled: true,
        source_mode: "manual",
        topics: ["materials"],
        keywords: ["diffusion"],
        venues: ["JOM"],
        authors_of_interest: ["Dr. Smith"],
        user_name: "Workbench User",
        user_email: "user@example.com",
        paper_title: "Paper Title",
        created_at: "2026-04-16T06:00:00Z",
        updated_at: "2026-04-16T06:00:00Z",
      },
    ],
    workspace_memberships: [
      {
        workspace_id: "workspace-1",
        slug: "materials-group",
        name: "Materials Group",
        status: "active",
        role: "owner",
        joined_at: "2026-04-16T06:00:00Z",
      },
    ],
  };
}

function paperDetailFixture() {
  return {
    paper: userDetailFixture().papers[0],
    owner: {
      id: "user-1",
      name: "Workbench User",
      email: "user@example.com",
      field: "Materials",
    },
    linked_watch_profiles: userDetailFixture().watch_profiles,
  };
}

function buildApiClient() {
  return {
    listUsers: vi.fn().mockResolvedValue([userSummaryFixture()]),
    getUserDetail: vi.fn().mockResolvedValue(userDetailFixture()),
    listPapers: vi.fn().mockResolvedValue(userDetailFixture().papers),
    getPaperDetail: vi.fn().mockResolvedValue(paperDetailFixture()),
    listWatchProfiles: vi.fn().mockResolvedValue(userDetailFixture().watch_profiles),
  };
}

describe("user workbench admin shell", () => {
  it("renders the token entry state by default", () => {
    render(<UserWorkbenchAdminShell />);
    expect(screen.getByRole("heading", { name: /open the read-only user workbench/i })).toBeVisible();
  });

  it("loads from a fragment token and clears the visible URL", async () => {
    const client = buildApiClient();
    const historyLike = {
      replaceState: vi.fn(),
    };

    render(
      <UserWorkbenchAdminShell
        apiClientFactory={() => client}
        locationLike={{ pathname: "/", search: "", hash: "#admin_bearer=fragment-token" }}
        historyLike={historyLike}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Workbench User" })).toBeVisible();
    expect(historyLike.replaceState).toHaveBeenCalledWith(null, "", "/");
  });

  it("supports manual token entry and renders user detail", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(<UserWorkbenchAdminShell apiClientFactory={() => client} />);

    await user.type(screen.getByLabelText(/admin bearer token/i), "manual-token");
    await user.click(screen.getByRole("button", { name: /open workbench/i }));

    expect(await screen.findByText("Digest title")).toBeVisible();
    expect(screen.getByText("Materials Group")).toBeVisible();
  });

  it("renders paper detail after opening the paper explorer", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(
      <UserWorkbenchAdminShell
        apiClientFactory={() => client}
        locationLike={{ pathname: "/", search: "", hash: "#admin_bearer=fragment-token" }}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Workbench User" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /browse papers/i }));
    await waitFor(() => expect(client.listPapers).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: /open detail/i }));

    expect(await screen.findByText("Review delta")).toBeVisible();
    expect(screen.getAllByText("Watch label").length).toBeGreaterThan(0);
  });

  it("renders the watch profile explorer", async () => {
    const client = buildApiClient();
    const user = userEvent.setup();

    render(
      <UserWorkbenchAdminShell
        apiClientFactory={() => client}
        locationLike={{ pathname: "/", search: "", hash: "#admin_bearer=fragment-token" }}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Workbench User" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: /browse watch profiles/i }));

    expect(await screen.findByText("Read-only watch profile explorer")).toBeVisible();
    expect(screen.getByText("Watch label")).toBeVisible();
  });
});
