import {
  buildApiErrorViewModel,
  buildPaperCardViewModels,
  buildPaperDetailViewModel,
  buildUserCardViewModels,
  buildUserDetailViewModel,
  buildWatchProfileCardViewModels,
} from "./workbenchModel";

describe("user workbench model helpers", () => {
  const userSummary = {
    id: "user-1",
    name: "Workbench User",
    email: "user@example.com",
    field: "Materials",
    paper_count: 2,
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

  const paperSummary = {
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
  };

  const watchProfile = {
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
  };

  it("shapes user list cards", () => {
    expect(buildUserCardViewModels([userSummary])[0]).toMatchObject({
      title: "Workbench User",
      paperCount: 2,
      latestDigestTitle: "Digest title",
    });
  });

  it("shapes user detail drilldown", () => {
    expect(
      buildUserDetailViewModel({
        user: userSummary,
        papers: [paperSummary],
        watch_profiles: [watchProfile],
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
      }),
    ).toMatchObject({
      latestDigestTitle: "Digest title",
      paperTitles: ["Paper Title"],
      watchLabels: ["Watch label"],
    });
  });

  it("shapes paper detail drilldown", () => {
    expect(buildPaperCardViewModels([paperSummary])[0]).toMatchObject({
      title: "Paper Title",
      linkedWatchProfileCount: 1,
    });
    expect(
      buildPaperDetailViewModel({
        paper: paperSummary,
        owner: {
          id: "user-1",
          name: "Workbench User",
          email: "user@example.com",
          field: "Materials",
        },
        linked_watch_profiles: [watchProfile],
      }),
    ).toMatchObject({
      ownerLabel: "Workbench User (user@example.com)",
      linkedWatchLabels: ["Watch label"],
    });
  });

  it("shapes watch profile explorer cards", () => {
    expect(buildWatchProfileCardViewModels([watchProfile])[0]).toMatchObject({
      title: "Watch label",
      paperLabel: "Paper Title",
    });
  });

  it("shapes api errors", () => {
    expect(
      buildApiErrorViewModel({
        kind: "unauthorized",
        detail: "token expired",
      }),
    ).toMatchObject({
      title: "Unauthorized admin token",
    });
  });
});
