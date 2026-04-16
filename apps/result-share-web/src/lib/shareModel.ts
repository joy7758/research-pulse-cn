import type {
  DigestDisplaySection,
  DigestShareViewModel,
  PaperSnapshotViewModel,
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
} {
  return {
    shareKind: bootstrap.grant.share_kind,
    displayLabel: bootstrap.grant.display_label,
    status: bootstrap.grant.status,
    createdAt: bootstrap.grant.created_at,
    expiresAt: bootstrap.grant.expires_at,
    targetTitle: bootstrap.target.title,
    notes: bootstrap.notes,
  };
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
): WorkspaceBoardViewModel {
  return {
    ...buildGrantSummary(bootstrap),
    shareKind: "workspace_board",
    pageTitle: content.workspace.name,
    description: content.workspace.description,
    statusLabel: content.workspace.status,
    memberCount: content.member_count,
    paperCount: content.paper_count,
    quickStats: content.quick_stats,
    members: content.members,
    papers: content.papers,
  };
}

export function buildResultShareViewModel(
  bootstrap: ShareGrantBootstrapRead,
  content: SharedResultContentRead,
): ResultShareViewModel {
  switch (content.share_kind) {
    case "digest_issue":
      return buildDigestShareViewModel(bootstrap, content);
    case "paper_snapshot":
      return buildPaperSnapshotViewModel(bootstrap, content);
    case "workspace_board":
      return buildWorkspaceBoardViewModel(bootstrap, content);
    default:
      return buildWorkspaceBoardViewModel(bootstrap, content as SharedWorkspaceBoardRead);
  }
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
