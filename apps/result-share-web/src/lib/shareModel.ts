import type {
  CollectActionResultViewModel,
  CollectablePaperViewModel,
  DigestDisplaySection,
  DigestShareViewModel,
  PaperSnapshotViewModel,
  ResultCollectViewModel,
  ResultShareCollectPreviewRead,
  ResultShareCollectResponseRead,
  ResultShareApiErrorShape,
  ResultShareKind,
  ResultShareViewModel,
  ShareErrorViewModel,
  SharedDigestIssueRead,
  SharedDigestItemRead,
  SharedPaperSnapshotRead,
  SharedResultContentRead,
  SharedTodaySectionKind,
  SharedTodaySectionRead,
  SharedWorkspaceBoardRead,
  ShareGrantBootstrapRead,
  WorkspaceBoardViewModel,
} from "./types";

export const stableSectionOrder: SharedTodaySectionKind[] = [
  "today_focus",
  "yesterday_recap",
  "signal_updates",
  "related_papers",
  "other_updates",
];

export function formatReasonCode(reasonCode: string): string {
  return reasonCode
    .split("_")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

const sectionTitleByKind: Record<string, string> = {
  today_focus: "Today Focus",
  yesterday_recap: "Yesterday Recap",
  signal_updates: "Signal Updates",
  related_papers: "Related Papers",
  other_updates: "Other Updates",
};

const cardTypeToSectionKind: Record<string, SharedTodaySectionKind> = {
  today_suggestion: "today_focus",
  yesterday_summary: "yesterday_recap",
  signal_change: "signal_updates",
  related_paper: "related_papers",
};

function buildGrantSummary(
  bootstrap: ShareGrantBootstrapRead,
): {
  shareKind: ResultShareKind;
  displayLabel: string | null;
  status: string;
  createdAt: string;
  expiresAt: string | null;
  targetTitle: string | null;
  notes: string[];
  collectionReserve: ShareGrantBootstrapRead["collection_reserve"];
  workspaceInviteHandoffReserve: ShareGrantBootstrapRead["workspace_invite_handoff_reserve"];
  resultCollectHandoffReserve: ShareGrantBootstrapRead["result_collect_handoff_reserve"];
} {
  return {
    shareKind: bootstrap.grant.share_kind,
    displayLabel: bootstrap.grant.display_label,
    status: bootstrap.grant.status,
    createdAt: bootstrap.grant.created_at,
    expiresAt: bootstrap.grant.expires_at,
    targetTitle: bootstrap.target.title,
    notes: bootstrap.notes,
    collectionReserve: bootstrap.collection_reserve,
    workspaceInviteHandoffReserve: bootstrap.workspace_invite_handoff_reserve,
    resultCollectHandoffReserve: bootstrap.result_collect_handoff_reserve,
  };
}

function resolvePublicUrl(apiBaseUrl: string | undefined, value: string | null): string | null {
  if (!value) {
    return null;
  }
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  const trimmedBaseUrl = apiBaseUrl?.trim().replace(/\/+$/, "");
  if (!trimmedBaseUrl) {
    return value;
  }
  return `${trimmedBaseUrl}${value.startsWith("/") ? value : `/${value}`}`;
}

function orderSectionKinds(sectionKinds: SharedTodaySectionKind[]): SharedTodaySectionKind[] {
  const unique = [...new Set(sectionKinds)];
  const known = stableSectionOrder.filter((kind) => unique.includes(kind));
  const extras = unique.filter((kind) => !stableSectionOrder.includes(kind));
  return [...known, ...extras];
}

function fallbackSectionKindForCardType(cardType: string): SharedTodaySectionKind {
  return cardTypeToSectionKind[cardType] ?? "other_updates";
}

function buildFallbackSections(items: SharedDigestItemRead[]): DigestDisplaySection[] {
  const grouped = new Map<SharedTodaySectionKind, SharedDigestItemRead[]>();
  items.forEach((item) => {
    const kind = fallbackSectionKindForCardType(item.card_type);
    const existing = grouped.get(kind) ?? [];
    existing.push(item);
    grouped.set(kind, existing);
  });

  return orderSectionKinds([...grouped.keys()]).map((kind) => {
    const sectionItems = (grouped.get(kind) ?? []).sort(
      (left, right) => left.sort_order - right.sort_order,
    );
    return {
      kind,
      title: sectionTitleByKind[kind] ?? kind,
      item_count: sectionItems.length,
      items: sectionItems,
    };
  });
}

function buildStructuredSections(
  content: SharedDigestIssueRead,
): DigestDisplaySection[] {
  const sectionsByKind = new Map<SharedTodaySectionKind, SharedTodaySectionRead>(
    content.sections.map((section) => [section.kind, section]),
  );
  return orderSectionKinds(
    content.section_order.length > 0
      ? content.section_order
      : content.sections.map((section) => section.kind),
  )
    .map((kind) => sectionsByKind.get(kind))
    .filter((section): section is SharedTodaySectionRead => section !== undefined)
    .map((section) => ({
      kind: section.kind,
      title: section.title || sectionTitleByKind[section.kind] || section.kind,
      item_count: section.item_count,
      items: [...section.items].sort((left, right) => left.sort_order - right.sort_order),
    }));
}

export function buildDigestShareViewModel(
  bootstrap: ShareGrantBootstrapRead,
  content: SharedDigestIssueRead,
): DigestShareViewModel {
  const structuredSections = buildStructuredSections(content);
  const fallbackSections = buildFallbackSections(
    content.items.length > 0 ? content.items : content.highlights,
  );
  const sectionViews = structuredSections.length > 0 ? structuredSections : fallbackSections;
  return {
    ...buildGrantSummary(bootstrap),
    shareKind: "digest_issue",
    pageTitle:
      content.publication_preview?.digest_title?.trim() || content.title,
    pageSubtitle:
      content.publication_preview?.digest_subtitle?.trim() || content.summary,
    issueDate: content.issue_date,
    highlightCount: content.highlight_count,
    selectedCardCount: content.selected_card_count,
    deepLinkPath: content.deep_link_path,
    isStructured: content.is_structured,
    fallbackMode: content.fallback_mode,
    sectionViews,
    quickStats: content.quick_stats,
    focusCard: content.focus_card,
    publicationPreview: content.publication_preview,
    legacyHighlights: content.highlights,
  };
}

export function buildPaperSnapshotViewModel(
  bootstrap: ShareGrantBootstrapRead,
  content: SharedPaperSnapshotRead,
): PaperSnapshotViewModel {
  return {
    ...buildGrantSummary(bootstrap),
    shareKind: "paper_snapshot",
    pageTitle: content.title,
    metadataRows: [
      { label: "Type", value: content.type },
      { label: "Stage", value: content.stage },
      { label: "Venue", value: content.venue ?? "Unavailable" },
      { label: "Priority", value: String(content.priority) },
      {
        label: "Progress",
        value: `${content.progress_percentage}%`,
      },
      {
        label: "Last touch",
        value: content.last_touch_at ?? "Unavailable",
      },
    ],
    nextAction: content.next_action,
    blocker: content.blocker,
    latestSignalSummary: content.latest_signal_summary,
    ownerName: content.owner_name,
  };
}

export function buildWorkspaceBoardViewModel(
  bootstrap: ShareGrantBootstrapRead,
  content: SharedWorkspaceBoardRead,
  apiBaseUrl?: string,
): WorkspaceBoardViewModel {
  const grantSummary = buildGrantSummary(bootstrap);
  return {
    ...grantSummary,
    shareKind: "workspace_board",
    pageTitle: content.workspace.name,
    description: content.workspace.description,
    statusLabel: content.workspace.status,
    memberCount: content.member_count,
    paperCount: content.paper_count,
    quickStats: content.quick_stats,
    members: content.members,
    papers: content.papers,
    workspaceInviteHandoff: grantSummary.workspaceInviteHandoffReserve
      ? {
          supported: grantSummary.workspaceInviteHandoffReserve.supported,
          separateInviteTokenRequired:
            grantSummary.workspaceInviteHandoffReserve.separate_invite_token_required,
          inviteBootstrapAvailable:
            grantSummary.workspaceInviteHandoffReserve.invite_bootstrap_available,
          selfServiceClaimSupported:
            grantSummary.workspaceInviteHandoffReserve.self_service_claim_supported,
          directClaimViaSharePage:
            grantSummary.workspaceInviteHandoffReserve.direct_claim_via_share_page,
          handoffRedirectSupported:
            grantSummary.workspaceInviteHandoffReserve.handoff_redirect_supported,
          sourceFilesIncluded:
            grantSummary.workspaceInviteHandoffReserve.source_files_included,
          inviteShellEntryUrl:
            grantSummary.workspaceInviteHandoffReserve.invite_shell_entry_url,
          inviteHandoffUrl: resolvePublicUrl(
            apiBaseUrl,
            grantSummary.workspaceInviteHandoffReserve.invite_handoff_url,
          ),
          notes: grantSummary.workspaceInviteHandoffReserve.notes,
        }
      : null,
    resultCollectHandoff: grantSummary.resultCollectHandoffReserve
      ? {
          supported: grantSummary.resultCollectHandoffReserve.supported,
          separateResultShareTokenRequired:
            grantSummary.resultCollectHandoffReserve.separate_result_share_token_required,
          resultShareBootstrapAvailable:
            grantSummary.resultCollectHandoffReserve.result_share_bootstrap_available,
          collectSupportedViaSelfService:
            grantSummary.resultCollectHandoffReserve.collect_supported_via_self_service,
          directCollectViaCurrentShare:
            grantSummary.resultCollectHandoffReserve.direct_collect_via_current_share,
          handoffRedirectSupported:
            grantSummary.resultCollectHandoffReserve.handoff_redirect_supported,
          sourceFilesIncluded:
            grantSummary.resultCollectHandoffReserve.source_files_included,
          supportedShareKinds:
            grantSummary.resultCollectHandoffReserve.supported_share_kinds,
          resultShareShellEntryUrl:
            grantSummary.resultCollectHandoffReserve.result_share_shell_entry_url,
          collectHandoffUrl: resolvePublicUrl(
            apiBaseUrl,
            grantSummary.resultCollectHandoffReserve.collect_handoff_url,
          ),
          notes: grantSummary.resultCollectHandoffReserve.notes,
        }
      : null,
  };
}

export function buildResultShareViewModel(
  bootstrap: ShareGrantBootstrapRead,
  content: SharedResultContentRead,
  apiBaseUrl?: string,
): ResultShareViewModel {
  switch (content.share_kind) {
    case "digest_issue":
      return buildDigestShareViewModel(bootstrap, content);
    case "paper_snapshot":
      return buildPaperSnapshotViewModel(bootstrap, content);
    case "workspace_board":
      return buildWorkspaceBoardViewModel(bootstrap, content, apiBaseUrl);
    default:
      return buildWorkspaceBoardViewModel(bootstrap, content as SharedWorkspaceBoardRead, apiBaseUrl);
  }
}

function buildCollectablePaperViewModel(
  paper: ResultShareCollectPreviewRead["collectable_items"][number],
): CollectablePaperViewModel {
  const subtitleParts = [paper.type, paper.stage, paper.venue ?? "Venue unavailable"].filter(
    Boolean,
  );
  const sourceParts = [
    paper.source_section_kind,
    paper.source_card_type,
  ].filter((value): value is string => Boolean(value?.trim()));
  return {
    paperId: paper.paper_id,
    title: paper.title,
    subtitle: subtitleParts.join(" · "),
    nextAction: paper.next_action,
    blocker: paper.blocker,
    sourceSummary: sourceParts.length > 0 ? sourceParts.join(" / ") : null,
    notes: paper.notes ?? [],
  };
}

export function buildResultCollectViewModel(
  bootstrap: ShareGrantBootstrapRead,
  preview: ResultShareCollectPreviewRead,
): ResultCollectViewModel {
  const collectionReserve = bootstrap.collection_reserve;
  const shareKind = preview.share?.share_kind ?? bootstrap.grant.share_kind;
  const shareKindCollectable = collectionReserve?.share_kind_collectable ?? false;
  const collectionSupported = collectionReserve?.supported ?? false;
  const collectSupportedViaSelfService =
    collectionReserve?.collect_supported_via_self_service ?? false;

  return {
    shareKind,
    collectionSupported,
    shareKindCollectable,
    collectSupportedViaSelfService,
    canCollect: preview.can_collect,
    requiresPaperSelection:
      shareKind === "digest_issue" && preview.collectable_items.length > 1,
    reasonCodes: preview.reason_codes,
    notes: [...(collectionReserve?.notes ?? []), ...preview.notes],
    collectableItems: preview.collectable_items.map(buildCollectablePaperViewModel),
    eligibleWorkspaces: preview.eligible_workspaces.map((item) => ({
      workspaceId: item.workspace.id,
      label: `${item.workspace.name} (${item.workspace.slug})`,
      description: item.workspace.description,
      membershipRole: item.membership_role,
      status: item.workspace.status,
    })),
  };
}

export function buildCollectActionResultViewModel(
  response: ResultShareCollectResponseRead,
): CollectActionResultViewModel {
  if (response.action === "collected") {
    return {
      action: response.action,
      title: "Collected into workspace",
      message:
        "Selected paper summaries were added to the workspace through the self-service collect boundary.",
      notes: response.notes,
      itemResults: response.collected_results.map((item) => ({
        paperId: item.paper_id,
        title: item.paper.title,
        status: item.status,
        reasonCodes: item.reason_codes,
      })),
    };
  }
  if (response.action === "already_present") {
    return {
      action: response.action,
      title: "Already present",
      message:
        "The selected paper summaries were already present in the target workspace. No duplicate inclusion was created.",
      notes: response.notes,
      itemResults: response.collected_results.map((item) => ({
        paperId: item.paper_id,
        title: item.paper.title,
        status: item.status,
        reasonCodes: item.reason_codes,
      })),
    };
  }
  return {
    action: response.action,
    title: "Collect rejected",
    message:
      "The current self-service token could not complete the collect action. Review the reason codes before trying again.",
    notes: response.notes,
    itemResults: response.collected_results.map((item) => ({
      paperId: item.paper_id,
      title: item.paper.title,
      status: item.status,
      reasonCodes: item.reason_codes,
    })),
  };
}

export function buildShareErrorViewModel(
  error: Pick<ResultShareApiErrorShape, "kind" | "detail">,
): ShareErrorViewModel {
  switch (error.kind) {
    case "revoked_token":
      return {
        kind: error.kind,
        title: "Share link revoked",
        message: error.detail,
      };
    case "expired_token":
      return {
        kind: error.kind,
        title: "Share link expired",
        message: error.detail,
      };
    case "invalid_token":
      return {
        kind: error.kind,
        title: "Invalid share link",
        message: error.detail,
      };
    case "unauthorized_self_service":
      return {
        kind: error.kind,
        title: "Self-service token rejected",
        message: error.detail,
      };
    case "network_error":
      return {
        kind: error.kind,
        title: "Network error",
        message: error.detail,
      };
    default:
      return {
        kind: "request_failed",
        title: "Unable to load share",
        message: error.detail,
      };
  }
}

export function isSafeExternalHref(value: string | null): boolean {
  if (!value) {
    return false;
  }
  return /^https?:\/\//i.test(value.trim());
}
