import type {
  ApiErrorViewModel,
  ConversionAttributionScopeViewModel,
  ConversionMetricBucketViewModel,
  ConversionMetricSectionViewModel,
  ConversionSummaryMetricViewModel,
  GroupWorkspaceAdminApiErrorShape,
  GroupWorkspaceBoardRead,
  GroupWorkspaceConversionAttributionRead,
  GroupWorkspaceConversionOverviewRead,
  GroupWorkspaceRead,
  GroupWorkspaceWorkspaceConversionOverviewRead,
  GlobalConversionOverviewViewModel,
  LookupOption,
  PaperProfileRead,
  ResultShareGrantIssueResponse,
  UserProfileRead,
  WorkspaceConversionOverviewViewModel,
  WorkspaceListItemViewModel,
  WorkspaceBoardViewModel,
  ShareGrantOneTimeDisplayModel,
} from "./types";

export function buildWorkspaceListItems(
  workspaces: GroupWorkspaceRead[],
  boardCache: Record<string, GroupWorkspaceBoardRead | undefined>,
): WorkspaceListItemViewModel[] {
  return workspaces.map((workspace) => {
    const cachedBoard = boardCache[workspace.id];
    return {
      id: workspace.id,
      slug: workspace.slug,
      name: workspace.name,
      description: workspace.description,
      status: workspace.status,
      memberCount: cachedBoard?.member_count ?? null,
      paperCount: cachedBoard?.paper_count ?? null,
    };
  });
}

export function buildWorkspaceBoardViewModel(board: GroupWorkspaceBoardRead): WorkspaceBoardViewModel {
  return {
    workspaceId: board.workspace.id,
    title: board.workspace.name,
    description: board.workspace.description,
    status: board.workspace.status,
    memberCount: board.member_count,
    paperCount: board.paper_count,
    blockedPaperCount: board.quick_stats.blocked_paper_count,
    papersWithSignalsCount: board.quick_stats.papers_with_signals_count,
    members: board.members,
    papers: board.papers,
  };
}

export function buildUserLookupOptions(users: UserProfileRead[]): LookupOption[] {
  return users.map((user) => ({
    id: user.id,
    label: user.email ? `${user.name} (${user.email})` : user.name,
    hint: user.field,
  }));
}

export function buildPaperLookupOptions(papers: PaperProfileRead[]): LookupOption[] {
  return papers.map((paper) => ({
    id: paper.id,
    label: paper.title,
    hint: [paper.stage, paper.venue].filter(Boolean).join(" · ") || null,
  }));
}

export function buildShareGrantIssueViewModel(
  response: ResultShareGrantIssueResponse,
): ShareGrantOneTimeDisplayModel {
  return {
    grantId: response.grant.id,
    shareKind: response.grant.share_kind,
    displayLabel: response.grant.display_label,
    plainTextToken: response.plain_text_token,
    expiresAt: response.expires_at,
    copyHint: "Copy this token now. It is only returned once at creation time.",
  };
}

const metricKeyLabels: Record<string, string> = {
  workspace_board: "Workspace board",
  digest_issue: "Digest issue",
  paper_snapshot: "Paper snapshot",
  share_token: "Raw share token",
  alias: "Alias",
  alias_redirect: "Alias redirect",
  group_workspace_invite_entry: "Invite entry",
  result_share_collect_entry: "Result collect entry",
};

function humanizeMetricKey(value: string): string {
  const preset = metricKeyLabels[value];
  if (preset) {
    return preset;
  }
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function humanizeAttributionMetric(metric: string): string {
  if (metric.endsWith("_count")) {
    return `${humanizeMetricKey(metric.slice(0, -6))} count`;
  }
  return humanizeMetricKey(metric);
}

function buildMetricBuckets(bucketMap: Record<string, number>): ConversionMetricBucketViewModel[] {
  return Object.entries(bucketMap)
    .sort((left, right) => {
      if (right[1] !== left[1]) {
        return right[1] - left[1];
      }
      return left[0].localeCompare(right[0]);
    })
    .map(([key, count]) => ({
      key,
      label: humanizeMetricKey(key),
      count,
    }));
}

function buildMetricSection(
  title: string,
  rows: ConversionMetricBucketViewModel[],
  emptyLabel: string,
): ConversionMetricSectionViewModel {
  return {
    title,
    rows,
    emptyLabel,
  };
}

function buildSummaryMetric(
  label: string,
  value: number,
  hint: string | null = null,
): ConversionSummaryMetricViewModel {
  return {
    label,
    value,
    hint,
  };
}

export function buildConversionAttributionScopeViewModel(
  scope: GroupWorkspaceConversionAttributionRead,
): ConversionAttributionScopeViewModel {
  return {
    directMetrics: scope.direct_attribution_metrics.map(humanizeAttributionMetric),
    workspaceLevelAggregateMetrics: scope.workspace_level_aggregate_metrics.map(
      humanizeAttributionMetric,
    ),
    notes: scope.notes,
  };
}

export function buildGlobalConversionOverviewViewModel(
  overview: GroupWorkspaceConversionOverviewRead,
): GlobalConversionOverviewViewModel {
  const shareKindBuckets = buildMetricBuckets(overview.by_share_kind);
  const accessModeBuckets = buildMetricBuckets(overview.by_access_mode);
  const handoffTargetBuckets = buildMetricBuckets(overview.by_handoff_target);
  const sections = [
    buildMetricSection(
      "Event counts",
      [
        buildSummaryMetric("Bootstrap views", overview.bootstrap_view_count),
        buildSummaryMetric("Content views", overview.content_view_count),
        buildSummaryMetric("Redirects", overview.redirect_count),
        buildSummaryMetric("Invite handoffs", overview.invite_handoff_redirect_count),
        buildSummaryMetric("Collect handoffs", overview.collect_handoff_redirect_count),
        buildSummaryMetric("Resolved events", overview.resolved_event_count),
        buildSummaryMetric("Rejected events", overview.rejected_event_count),
      ].map(({ label, value }) => ({ key: label, label, count: value })),
      "No view events in this window.",
    ),
    buildMetricSection("By share kind", shareKindBuckets, "No share-kind counts recorded."),
    buildMetricSection("By access mode", accessModeBuckets, "No access-mode counts recorded."),
    buildMetricSection(
      "By handoff target",
      handoffTargetBuckets,
      "No invite or collect handoff redirects recorded.",
    ),
    buildMetricSection(
      "Invite outcomes",
      [
        { key: "claimed", label: "Claimed", count: overview.invite_claimed_count },
        {
          key: "already_member",
          label: "Already member",
          count: overview.invite_already_member_count,
        },
        { key: "rejected", label: "Rejected", count: overview.invite_rejected_count },
      ],
      "No invite claims recorded.",
    ),
    buildMetricSection(
      "Collect outcomes",
      [
        { key: "collected", label: "Collected", count: overview.collect_collected_count },
        {
          key: "already_present",
          label: "Already present",
          count: overview.collect_already_present_count,
        },
        { key: "rejected", label: "Rejected", count: overview.collect_rejected_count },
      ],
      "No collect records recorded.",
    ),
  ];

  const empty =
    overview.total_share_view_events === 0 &&
    overview.invite_claimed_count === 0 &&
    overview.invite_already_member_count === 0 &&
    overview.invite_rejected_count === 0 &&
    overview.collect_collected_count === 0 &&
    overview.collect_already_present_count === 0 &&
    overview.collect_rejected_count === 0;

  return {
    summaryMetrics: [
      buildSummaryMetric("Total share events", overview.total_share_view_events),
      buildSummaryMetric("Invite handoffs", overview.invite_handoff_redirect_count),
      buildSummaryMetric("Collect handoffs", overview.collect_handoff_redirect_count),
      buildSummaryMetric("Invite claimed", overview.invite_claimed_count),
      buildSummaryMetric("Collect collected", overview.collect_collected_count),
      buildSummaryMetric("Rejected events", overview.rejected_event_count),
      buildSummaryMetric("Unique share grants", overview.unique_result_share_grant_count),
      buildSummaryMetric("Active workspaces", overview.unique_workspace_count),
    ],
    sections,
    windowStart: overview.window_start,
    windowEnd: overview.window_end,
    lastActivityAt: overview.last_activity_at,
    attributionScope: buildConversionAttributionScopeViewModel(overview.attribution_scope),
    empty,
  };
}

export function buildWorkspaceConversionOverviewViewModel(
  overview: GroupWorkspaceWorkspaceConversionOverviewRead,
): WorkspaceConversionOverviewViewModel {
  const sections = [
    buildMetricSection(
      "Active grant inventory",
      [
        {
          key: "workspace_board_share",
          label: "Workspace-board shares",
          count: overview.active_workspace_board_share_grant_count,
        },
        {
          key: "digest_issue_share",
          label: "Digest-issue shares",
          count: overview.active_digest_issue_share_grant_count,
        },
        {
          key: "paper_snapshot_share",
          label: "Paper-snapshot shares",
          count: overview.active_paper_snapshot_share_grant_count,
        },
        {
          key: "invite_grant",
          label: "Invite grants",
          count: overview.active_invite_grant_count,
        },
      ],
      "No active share or invite grants for this workspace.",
    ),
    buildMetricSection(
      "Invite and collect outcomes",
      [
        {
          key: "invite_claimed",
          label: "Invite claimed",
          count: overview.invite_claimed_count,
        },
        {
          key: "invite_already_member",
          label: "Invite already member",
          count: overview.invite_already_member_count,
        },
        {
          key: "collect_collected",
          label: "Collect collected",
          count: overview.collect_collected_count,
        },
        {
          key: "collect_already_present",
          label: "Collect already present",
          count: overview.collect_already_present_count,
        },
      ],
      "No invite or collect outcomes recorded in this window.",
    ),
  ];

  const empty =
    overview.workspace_board_view_count === 0 &&
    overview.invite_handoff_redirect_count === 0 &&
    overview.collect_handoff_redirect_count === 0 &&
    overview.invite_claimed_count === 0 &&
    overview.invite_already_member_count === 0 &&
    overview.collect_collected_count === 0 &&
    overview.collect_already_present_count === 0;

  return {
    workspace: overview.workspace,
    summaryMetrics: [
      buildSummaryMetric(
        "Workspace-board views",
        overview.workspace_board_view_count,
        "Bootstrap and content views only.",
      ),
      buildSummaryMetric("Invite handoffs", overview.invite_handoff_redirect_count),
      buildSummaryMetric("Collect handoffs", overview.collect_handoff_redirect_count),
      buildSummaryMetric("Invite claimed", overview.invite_claimed_count),
      buildSummaryMetric("Collect collected", overview.collect_collected_count),
      buildSummaryMetric("Unique collected papers", overview.unique_collected_paper_count),
      buildSummaryMetric("Unique collecting users", overview.unique_collecting_user_count),
      buildSummaryMetric("Invite grants", overview.active_invite_grant_count),
    ],
    sections,
    windowStart: overview.window_start,
    windowEnd: overview.window_end,
    lastActivityAt: overview.last_activity_at,
    attributionScope: buildConversionAttributionScopeViewModel(overview.attribution_scope),
    empty,
  };
}

export function buildApiErrorViewModel(
  shape: Pick<GroupWorkspaceAdminApiErrorShape, "kind" | "detail">,
): ApiErrorViewModel {
  switch (shape.kind) {
    case "unauthorized":
      return {
        kind: shape.kind,
        title: "Unauthorized admin token",
        message: "Paste a valid admin/operator bearer token and try again.",
      };
    case "forbidden":
      return {
        kind: shape.kind,
        title: "Forbidden action",
        message: "This token can read some data but cannot perform this admin action.",
      };
    case "not_found":
      return {
        kind: shape.kind,
        title: "Resource not found",
        message: shape.detail,
      };
    case "conflict":
      return {
        kind: shape.kind,
        title: "Conflict",
        message: shape.detail,
      };
    case "network_error":
      return {
        kind: shape.kind,
        title: "Network failure",
        message: "The admin shell could not reach the API.",
      };
    default:
      return {
        kind: shape.kind,
        title: "Request failed",
        message: shape.detail,
      };
  }
}
