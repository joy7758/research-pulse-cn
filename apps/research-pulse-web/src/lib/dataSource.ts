import desktopNotificationJson from "../data/mock/desktop_notification.json";
import emptyImportCommitJson from "../data/mock/empty_import_commit.json";
import emptyImportPreviewJson from "../data/mock/empty_import_preview.json";
import emptyProgressSummaryJson from "../data/mock/empty_paper_progress_summary.json";
import emptyResearchPulseJson from "../data/mock/empty_research_pulse.json";
import importCommitJson from "../data/mock/import_commit.json";
import importPreviewWithErrorsJson from "../data/mock/import_preview_with_errors.json";
import importPreviewJson from "../data/mock/import_preview.json";
import miniProgramDailyPulseJson from "../data/mock/mini_program_daily_pulse_detail.json";
import miniProgramMetadataAttentionJson from "../data/mock/mini_program_metadata_attention_detail.json";
import miniProgramNextActionsJson from "../data/mock/mini_program_next_actions_detail.json";
import miniProgramPaperJson from "../data/mock/mini_program_paper_detail.json";
import miniProgramTriageJson from "../data/mock/mini_program_triage_detail.json";
import officialAccountDailySummaryJson from "../data/mock/official_account_daily_summary.json";
import paperProgressItemsJson from "../data/mock/paper_progress_items.json";
import progressSummaryJson from "../data/mock/paper_progress_summary.json";
import researchPulseJson from "../data/mock/research_pulse.json";
import type {
  ChannelStateHint,
  DataMode,
  DesktopNotificationActionRead,
  DesktopNotificationItemRead,
  DesktopNotificationRead,
  FrontendShellData,
  ImportCommitRead,
  ImportCommitRecordResult,
  ImportPreviewRead,
  ImportPreviewRecord,
  MiniProgramDetailActionRead,
  MiniProgramDetailCardRead,
  MiniProgramDetailItemRead,
  MiniProgramDetailRead,
  MiniProgramNavigationRead,
  MiniProgramPreviewCollection,
  MiniProgramShareCardRead,
  MockScenario,
  MockScenarioOption,
  OfficialAccountBindingPreview,
  OfficialAccountBindingTargetPreview,
  OfficialAccountDailySummaryHighlight,
  OfficialAccountDailySummaryItem,
  OfficialAccountDailySummaryRead,
  OfficialAccountDailySummarySection,
  OfficialAccountProviderPreview,
  OfficialAccountPublicationPreview,
  OfficialAccountTemplatePayloadPreview,
  PaperProgressItemRead,
  PaperProgressSummaryRead,
  Priority,
  ResearchPulseItem,
  ResearchPulseRead,
  ResearchPulseSection,
} from "./types";

const loadDelayMs = 220;

const sharedChannelStates: ChannelStateHint[] = [
  {
    id: "pulse",
    label: "Research Pulse",
    state: "draft",
    message: "当前页面展示的是本地 mock 草稿，不触发真实生成任务。",
  },
  {
    id: "official-account",
    label: "公众号摘要",
    state: "not_sent",
    message: "只展示公众号摘要草稿页，不触发真实微信发送。",
  },
  {
    id: "desktop",
    label: "桌面通知",
    state: "not_sent",
    message: "只展示桌面通知草稿页，不调用系统通知。",
  },
  {
    id: "mini-program",
    label: "小程序详情",
    state: "preview",
    message: "只展示 share-safe 预览，不做真实小程序交互。",
  },
];

export const mockScenarioOptions: MockScenarioOption[] = [
  {
    id: "default",
    label: "默认工作流",
    description: "展示正常的今日 Pulse、导入预览和草稿边界。",
  },
  {
    id: "empty",
    label: "空状态",
    description: "验证没有论文、没有待预览记录、没有可展示草稿时的引导文案。",
  },
  {
    id: "issues",
    label: "问题集中",
    description: "验证 warning、error、disabled 和补全建议。",
  },
  {
    id: "broken",
    label: "数据异常",
    description: "验证 mock 数据缺失或解析失败时的恢复路径。",
  },
];

type UnknownRecord = Record<string, unknown>;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function sleep(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function readString(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function readNullableString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function readNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function readNullableNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readStringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === "string" && entry.trim().length > 0)
    : [];
}

function readPriority(value: unknown, fallback: Priority = "normal"): Priority {
  return value === "low" || value === "normal" || value === "high" || value === "urgent"
    ? value
    : fallback;
}

function readStringRecord(value: unknown): Record<string, string> {
  if (!isRecord(value)) {
    return {};
  }

  const result: Record<string, string> = {};

  for (const [key, recordValue] of Object.entries(value)) {
    if (typeof recordValue === "string" && recordValue.trim().length > 0) {
      result[key] = recordValue;
    }
  }

  return result;
}

function readUnknownRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? clone(value) : {};
}

function normalizeImportPreviewRecord(value: unknown, index: number): ImportPreviewRecord {
  const record = isRecord(value) ? value : {};

  return {
    source_index: readNumber(record.source_index, index + 1),
    title: typeof record.title === "string" ? record.title : "",
    authors: readStringArray(record.authors),
    year: readNullableNumber(record.year),
    venue: readNullableString(record.venue),
    doi: readNullableString(record.doi),
    url: readNullableString(record.url),
    keywords: readStringArray(record.keywords),
    warnings: readStringArray(record.warnings),
    errors: readStringArray(record.errors),
    can_commit: Boolean(record.can_commit),
    selected: Boolean(record.selected),
  };
}

function normalizeImportPreview(value: unknown): ImportPreviewRead {
  const preview = isRecord(value) ? value : {};
  const recordsRaw = Array.isArray(preview.records) ? preview.records : [];
  const records = recordsRaw.map((record, index) => normalizeImportPreviewRecord(record, index));

  return {
    preview_id: readString(preview.preview_id, "mock-preview"),
    source_format: readString(preview.source_format, "mock"),
    created_at: readString(preview.created_at, "2026-04-19T00:00:00Z"),
    total_records: readNumber(preview.total_records, records.length),
    valid_records_count: readNumber(
      preview.valid_records_count,
      records.filter((record) => record.can_commit).length,
    ),
    warning_records_count: readNumber(
      preview.warning_records_count,
      records.filter((record) => record.warnings.length > 0).length,
    ),
    error_records_count: readNumber(
      preview.error_records_count,
      records.filter((record) => record.errors.length > 0).length,
    ),
    records,
  };
}

function normalizeImportCommitRecordResult(
  value: unknown,
  index: number,
): ImportCommitRecordResult {
  const result = isRecord(value) ? value : {};
  const status =
    result.status === "committed" || result.status === "skipped" || result.status === "failed"
      ? result.status
      : "skipped";

  return {
    source_index: readNumber(result.source_index, index + 1),
    status,
    reason: readString(result.reason, "当前 mock 结果没有给出更多说明。"),
    warnings: readStringArray(result.warnings),
    errors: readStringArray(result.errors),
  };
}

function normalizeImportCommit(value: unknown): ImportCommitRead {
  const commit = isRecord(value) ? value : {};
  const resultsRaw = Array.isArray(commit.record_results) ? commit.record_results : [];

  return {
    preview_id: readString(commit.preview_id, "mock-preview"),
    user_id: readString(commit.user_id, "mock-user"),
    source_format: readString(commit.source_format, "mock"),
    dry_run: Boolean(commit.dry_run),
    committed_at: readString(commit.committed_at, "2026-04-19T00:00:00Z"),
    total_selected: readNumber(commit.total_selected, resultsRaw.length),
    committed_count: readNumber(commit.committed_count),
    skipped_count: readNumber(commit.skipped_count),
    failed_count: readNumber(commit.failed_count),
    record_results: resultsRaw.map((item, index) => normalizeImportCommitRecordResult(item, index)),
  };
}

function normalizeProgressSummary(value: unknown): PaperProgressSummaryRead {
  const summary = isRecord(value) ? value : {};

  return {
    total_papers: readNumber(summary.total_papers),
    unread_count: readNumber(summary.unread_count),
    reading_count: readNumber(summary.reading_count),
    read_count: readNumber(summary.read_count),
    high_priority_count: readNumber(summary.high_priority_count),
    urgent_count: readNumber(summary.urgent_count),
    with_next_action_count: readNumber(summary.with_next_action_count),
    by_reading_status: isRecord(summary.by_reading_status)
      ? (summary.by_reading_status as Record<string, number>)
      : {},
    by_research_stage: isRecord(summary.by_research_stage)
      ? (summary.by_research_stage as Record<string, number>)
      : {},
    by_priority: isRecord(summary.by_priority) ? (summary.by_priority as Record<string, number>) : {},
  };
}

function normalizeProgressItem(value: unknown, index: number): PaperProgressItemRead {
  const item = isRecord(value) ? value : {};
  const priority = readPriority(item.priority);

  return {
    paper_id: readString(item.paper_id, `progress-paper-${index + 1}`),
    user_id: readString(item.user_id, "mock-user"),
    title: readString(item.title, "题名待补全"),
    authors: readStringArray(item.authors),
    year: readNullableNumber(item.year),
    venue: readNullableString(item.venue),
    doi: readNullableString(item.doi),
    url: readNullableString(item.url),
    source_format: readString(item.source_format, "mock"),
    reading_status: readString(item.reading_status, "unread"),
    research_stage: readString(item.research_stage, "inbox"),
    priority,
    priority_score: readNumber(
      item.priority_score,
      priority === "urgent" ? 5 : priority === "high" ? 4 : priority === "low" ? 1 : 3,
    ),
    next_action: readNullableString(item.next_action),
    user_note: readNullableString(item.user_note),
    research_note: readNullableString(item.research_note),
    tags: readStringArray(item.tags),
    keywords: readStringArray(item.keywords),
    imported_at: readString(item.imported_at, "2026-04-19T00:00:00Z"),
    created_at: readString(item.created_at, "2026-04-19T00:00:00Z"),
    updated_at: readString(item.updated_at, "2026-04-19T00:00:00Z"),
    last_touch_at: readString(item.last_touch_at, "2026-04-19T00:00:00Z"),
    warnings: readStringArray(item.warnings),
  };
}

function normalizePulseItem(value: unknown, index: number): ResearchPulseItem {
  const item = isRecord(value) ? value : {};
  const priority = readPriority(item.priority);

  return {
    paper_id: readString(item.paper_id, `mock-paper-${index + 1}`),
    title: readString(item.title, "题名待补全"),
    authors: readStringArray(item.authors),
    year: readNullableNumber(item.year),
    venue: readNullableString(item.venue),
    doi: readNullableString(item.doi),
    url: readNullableString(item.url),
    priority,
    reading_status: readString(item.reading_status, "unread"),
    research_stage: readString(item.research_stage, "inbox"),
    next_action: readNullableString(item.next_action),
    reason: readString(item.reason, "当前 mock 数据没有补充原因。"),
    suggested_action: readString(item.suggested_action, "先确认是否需要继续处理这篇论文。"),
    metadata_warnings: readStringArray(item.metadata_warnings),
    tags: readStringArray(item.tags),
    source_format: readString(item.source_format, "mock"),
  };
}

function normalizePulseSection(value: unknown, index: number): ResearchPulseSection {
  const section = isRecord(value) ? value : {};
  const itemsRaw = Array.isArray(section.items) ? section.items : [];

  return {
    section_id: readString(section.section_id, `section_${index + 1}`),
    title: readString(section.title, "未命名 section"),
    description: readString(section.description, "当前 section 还没有补充说明。"),
    empty_reason:
      section.empty_reason === null ? null : readString(section.empty_reason, "当前没有需要展示的内容。"),
    items: itemsRaw.map((item, itemIndex) => normalizePulseItem(item, itemIndex)),
  };
}

function normalizeResearchPulse(value: unknown): ResearchPulseRead {
  const pulse = isRecord(value) ? value : {};
  const sectionsRaw = Array.isArray(pulse.sections) ? pulse.sections : [];

  return {
    draft_id: readString(pulse.draft_id, "mock-pulse"),
    user_id: readString(pulse.user_id, "mock-user"),
    pulse_date: readString(pulse.pulse_date, "2026-04-19"),
    timezone: readString(pulse.timezone, "Asia/Shanghai"),
    dry_run: pulse.dry_run !== false,
    generated_at: readString(pulse.generated_at, "2026-04-19T00:00:00Z"),
    title: readString(pulse.title, "今日 Research Pulse 草稿"),
    summary: readString(pulse.summary, "当前 mock Pulse 还没有生成摘要。"),
    warnings: readStringArray(pulse.warnings),
    source_context_notes: readStringArray(pulse.source_context_notes),
    sections: sectionsRaw.map((section, index) => normalizePulseSection(section, index)),
  };
}

function normalizeOfficialSectionItem(
  value: unknown,
  index: number,
): OfficialAccountDailySummaryItem {
  const item = isRecord(value) ? value : {};

  return {
    paper_id: readString(item.paper_id, `official-item-${index + 1}`),
    title: readString(item.title, "题名待补全"),
    authors: readStringArray(item.authors),
    year: readNullableNumber(item.year),
    venue: readNullableString(item.venue),
    doi: readNullableString(item.doi),
    url: readNullableString(item.url),
    priority: readPriority(item.priority),
    reading_status: readString(item.reading_status, "unread"),
    research_stage: readString(item.research_stage, "inbox"),
    next_action: readNullableString(item.next_action),
    reason: readString(item.reason, "当前 mock 草稿没有补充原因。"),
    suggested_action: readString(item.suggested_action, "先确认这条摘要是否要继续保留。"),
    summary_line: readString(item.summary_line, "当前还没有生成摘要句。"),
    metadata_warnings: readStringArray(item.metadata_warnings),
    tags: readStringArray(item.tags),
    source_format: readNullableString(item.source_format),
  };
}

function normalizeOfficialSection(
  value: unknown,
  index: number,
): OfficialAccountDailySummarySection {
  const section = isRecord(value) ? value : {};
  const itemsRaw = Array.isArray(section.items) ? section.items : [];

  return {
    section_id: readString(section.section_id, `official-section-${index + 1}`),
    title: readString(section.title, "未命名 section"),
    description: readString(section.description, "当前还没有补充 section 说明。"),
    items: itemsRaw.map((item, itemIndex) => normalizeOfficialSectionItem(item, itemIndex)),
    empty_reason:
      section.empty_reason === null ? null : readString(section.empty_reason, "当前 section 还没有可展示内容。"),
  };
}

function normalizeOfficialHighlight(
  value: unknown,
  index: number,
): OfficialAccountDailySummaryHighlight {
  const highlight = isRecord(value) ? value : {};

  return {
    sort_order: readNumber(highlight.sort_order, index + 1),
    section_id: readString(highlight.section_id, `section_${index + 1}`),
    section_title: readString(highlight.section_title, "未命名 section"),
    paper_id: readString(highlight.paper_id, `paper-${index + 1}`),
    title: readString(highlight.title, "题名待补全"),
    summary: readString(highlight.summary, "当前还没有 highlight 摘要。"),
    why_now: readString(highlight.why_now, "当前还没有 why_now 说明。"),
    suggested_action: readString(highlight.suggested_action, "先确认是否继续保留这条摘要。"),
  };
}

function normalizeOfficialPublicationPreview(
  value: unknown,
): OfficialAccountPublicationPreview {
  const preview = isRecord(value) ? value : {};
  const highlightsRaw = Array.isArray(preview.digest_highlights) ? preview.digest_highlights : [];

  return {
    digest_title: readString(preview.digest_title, "公众号摘要草稿"),
    digest_subtitle: readString(preview.digest_subtitle, "当前仅为预览，不会真实发送。"),
    digest_highlights: highlightsRaw.map((highlight, index) =>
      normalizeOfficialHighlight(highlight, index),
    ),
    primary_cta_text: readString(preview.primary_cta_text, "查看今日 Pulse"),
    primary_cta_path: readNullableString(preview.primary_cta_path),
    mini_program_path: readNullableString(preview.mini_program_path),
    article_url: readNullableString(preview.article_url),
  };
}

function normalizeOfficialTemplatePayloadPreview(
  value: unknown,
): OfficialAccountTemplatePayloadPreview {
  const preview = isRecord(value) ? value : {};

  return {
    template_id_configured: Boolean(preview.template_id_configured),
    field_mapping: readStringRecord(preview.field_mapping),
    logical_fields: readStringRecord(preview.logical_fields),
    payload_preview: readUnknownRecord(preview.payload_preview),
  };
}

function normalizeOfficialBindingTargetPreview(
  value: unknown,
): OfficialAccountBindingTargetPreview {
  const binding = isRecord(value) ? value : {};

  return {
    binding_id: readString(binding.binding_id, "binding-preview"),
    channel_type: readString(binding.channel_type, "official_account"),
    bind_state: readString(binding.bind_state, "preview_only"),
    display_label: readNullableString(binding.display_label),
    subscribed: Boolean(binding.subscribed),
    digest_enabled: Boolean(binding.digest_enabled),
    masked_openid: readString(binding.masked_openid, "未绑定"),
  };
}

function normalizeOfficialBindingPreview(value: unknown): OfficialAccountBindingPreview {
  const preview = isRecord(value) ? value : {};

  return {
    active_binding_count: readNumber(preview.active_binding_count),
    selected_binding: preview.selected_binding
      ? normalizeOfficialBindingTargetPreview(preview.selected_binding)
      : null,
    notes: readStringArray(preview.notes),
  };
}

function normalizeOfficialProviderPreview(value: unknown): OfficialAccountProviderPreview {
  const preview = isRecord(value) ? value : {};

  return {
    provider_mode: readString(preview.provider_mode, "dry_run"),
    transport_kind: readString(preview.transport_kind, "preview_only"),
    template_id_configured: Boolean(preview.template_id_configured),
    template_field_mapping_configured: Boolean(preview.template_field_mapping_configured),
    article_base_url_configured: Boolean(preview.article_base_url_configured),
    mini_program_app_id_configured: Boolean(preview.mini_program_app_id_configured),
    callback_enabled: Boolean(preview.callback_enabled),
    real_send_enabled: Boolean(preview.real_send_enabled),
    notes: readStringArray(preview.notes),
  };
}

function normalizeOfficialAccountDailySummary(value: unknown): OfficialAccountDailySummaryRead {
  const summary = isRecord(value) ? value : {};
  const sectionsRaw = Array.isArray(summary.sections) ? summary.sections : [];

  return {
    draft_id: readString(summary.draft_id, "official-draft"),
    source_research_pulse_draft_id: readString(summary.source_research_pulse_draft_id, "mock-pulse"),
    user_id: readString(summary.user_id, "mock-user"),
    pulse_date: readString(summary.pulse_date, "2026-04-19"),
    timezone: readString(summary.timezone, "Asia/Shanghai"),
    dry_run: summary.dry_run !== false,
    title: readString(summary.title, "公众号每日摘要草稿"),
    headline: readString(summary.headline, "当前还没有生成 headline。"),
    summary: readString(summary.summary, "当前还没有生成摘要。"),
    sections: sectionsRaw.map((section, index) => normalizeOfficialSection(section, index)),
    highlight_count: readNumber(summary.highlight_count),
    publication_preview: normalizeOfficialPublicationPreview(summary.publication_preview),
    template_payload_preview: normalizeOfficialTemplatePayloadPreview(summary.template_payload_preview),
    binding_preview: normalizeOfficialBindingPreview(summary.binding_preview),
    provider_preview: normalizeOfficialProviderPreview(summary.provider_preview),
    total_source_papers: readNumber(summary.total_source_papers),
    warnings: readStringArray(summary.warnings),
    generated_at: readString(summary.generated_at, "2026-04-19T00:00:00Z"),
    source_context_notes: readStringArray(summary.source_context_notes),
  };
}

function normalizeDesktopNotificationItem(
  value: unknown,
  index: number,
): DesktopNotificationItemRead {
  const item = isRecord(value) ? value : {};

  return {
    paper_id: readString(item.paper_id, `desktop-item-${index + 1}`),
    title: readString(item.title, "题名待补全"),
    line: readString(item.line, "当前还没有可展示的通知摘要。"),
    reason: readString(item.reason, "当前还没有原因说明。"),
    suggested_action: readString(item.suggested_action, "先确认是否继续保留这条提醒。"),
    priority: readPriority(item.priority),
    reading_status: readString(item.reading_status, "unread"),
    research_stage: readString(item.research_stage, "inbox"),
    metadata_warnings: readStringArray(item.metadata_warnings),
    url: readNullableString(item.url),
    doi: readNullableString(item.doi),
    tags: readStringArray(item.tags),
    source_format: readNullableString(item.source_format),
  };
}

function normalizeDesktopNotificationAction(
  value: unknown,
  index: number,
): DesktopNotificationActionRead {
  const action = isRecord(value) ? value : {};

  return {
    action_id: readString(action.action_id, `desktop-action-${index + 1}`),
    label: readString(action.label, "未命名动作"),
    kind: readString(action.kind, "open"),
    deep_link: readString(action.deep_link, "research-pulse://"),
    payload: readUnknownRecord(action.payload),
  };
}

function normalizeDesktopNotification(value: unknown): DesktopNotificationRead {
  const draft = isRecord(value) ? value : {};
  const itemsRaw = Array.isArray(draft.items) ? draft.items : [];
  const actionsRaw = Array.isArray(draft.actions) ? draft.actions : [];

  return {
    draft_id: readString(draft.draft_id, "desktop-draft"),
    source_research_pulse_draft_id: readString(draft.source_research_pulse_draft_id, "mock-pulse"),
    user_id: readString(draft.user_id, "mock-user"),
    pulse_date: readString(draft.pulse_date, "2026-04-19"),
    timezone: readString(draft.timezone, "Asia/Shanghai"),
    title: readString(draft.title, "桌面通知草稿"),
    body: readString(draft.body, "当前还没有通知正文。"),
    notification_type: readString(draft.notification_type, "daily_research_pulse"),
    urgency: readString(draft.urgency, "normal"),
    badge_count: readNumber(draft.badge_count),
    items: itemsRaw.map((item, index) => normalizeDesktopNotificationItem(item, index)),
    actions: actionsRaw.map((action, index) => normalizeDesktopNotificationAction(action, index)),
    deep_link: readString(draft.deep_link, "research-pulse://pulse/daily"),
    payload_preview: readUnknownRecord(draft.payload_preview),
    total_source_papers: readNumber(draft.total_source_papers),
    total_items: readNumber(draft.total_items, itemsRaw.length),
    warnings: readStringArray(draft.warnings),
    generated_at: readString(draft.generated_at, "2026-04-19T00:00:00Z"),
    delivery_state: readString(draft.delivery_state, "draft"),
    delivery_notes: readStringArray(draft.delivery_notes),
  };
}

function normalizeMiniProgramItem(value: unknown, index: number): MiniProgramDetailItemRead {
  const item = isRecord(value) ? value : {};

  return {
    item_id: readString(item.item_id, `mini-item-${index + 1}`),
    paper_id: readNullableString(item.paper_id),
    title: readString(item.title, "题名待补全"),
    authors: readStringArray(item.authors),
    year: readNullableNumber(item.year),
    venue: readNullableString(item.venue),
    doi: readNullableString(item.doi),
    url: readNullableString(item.url),
    priority: item.priority ? readPriority(item.priority, "normal") : null,
    reading_status: readNullableString(item.reading_status),
    research_stage: readNullableString(item.research_stage),
    next_action: readNullableString(item.next_action),
    reason: readString(item.reason, "当前还没有可读说明。"),
    suggested_action: readString(item.suggested_action, "先确认是否继续保留这条详情。"),
    metadata_warnings: readStringArray(item.metadata_warnings),
    tags: readStringArray(item.tags),
    source_format: readNullableString(item.source_format),
    safe_abstract: readNullableString(item.safe_abstract),
    detail_path: readString(item.detail_path, "/pages/home/index"),
  };
}

function normalizeMiniProgramCard(value: unknown, index: number): MiniProgramDetailCardRead {
  const card = isRecord(value) ? value : {};
  const itemsRaw = Array.isArray(card.items) ? card.items : [];

  return {
    card_id: readString(card.card_id, `mini-card-${index + 1}`),
    card_type: readString(card.card_type, "summary"),
    title: readString(card.title, "未命名卡片"),
    subtitle: readNullableString(card.subtitle),
    body: readString(card.body, "当前卡片还没有补充正文。"),
    items: itemsRaw.map((item, itemIndex) => normalizeMiniProgramItem(item, itemIndex)),
    badges: readStringArray(card.badges),
    warnings: readStringArray(card.warnings),
    empty_reason:
      card.empty_reason === null ? null : readString(card.empty_reason, "当前卡片没有可展示内容。"),
  };
}

function normalizeMiniProgramAction(
  value: unknown,
  index: number,
): MiniProgramDetailActionRead {
  const action = isRecord(value) ? value : {};

  return {
    action_id: readString(action.action_id, `mini-action-${index + 1}`),
    label: readString(action.label, "未命名动作"),
    kind: readString(action.kind, "open"),
    path: readString(action.path, "/pages/home/index"),
    payload: readUnknownRecord(action.payload),
  };
}

function normalizeMiniShareCard(value: unknown): MiniProgramShareCardRead {
  const shareCard = isRecord(value) ? value : {};

  return {
    title: readString(shareCard.title, "小程序分享卡片预览"),
    summary: readString(shareCard.summary, "当前还没有分享摘要。"),
    path: readString(shareCard.path, "/pages/home/index"),
    image_placeholder: readNullableString(shareCard.image_placeholder),
    share_safe: shareCard.share_safe !== false,
    redacted_fields: readStringArray(shareCard.redacted_fields),
  };
}

function normalizeMiniNavigation(value: unknown): MiniProgramNavigationRead {
  const navigation = isRecord(value) ? value : {};

  return {
    current_path: readString(navigation.current_path, "/pages/home/index"),
    back_path: readString(navigation.back_path, "/pages/home/index"),
    related_paths: readStringArray(navigation.related_paths),
  };
}

function normalizeMiniProgramDetail(value: unknown): MiniProgramDetailRead {
  const detail = isRecord(value) ? value : {};
  const cardsRaw = Array.isArray(detail.cards) ? detail.cards : [];
  const actionsRaw = Array.isArray(detail.actions) ? detail.actions : [];

  return {
    detail_id: readString(detail.detail_id, "mini-detail"),
    detail_type: readString(detail.detail_type, "daily_pulse"),
    user_id: readString(detail.user_id, "mock-user"),
    pulse_date: readNullableString(detail.pulse_date),
    timezone: readString(detail.timezone, "Asia/Shanghai"),
    title: readString(detail.title, "小程序详情预览"),
    subtitle: readString(detail.subtitle, "当前仅为预览，不会触发真实小程序能力。"),
    summary: readString(detail.summary, "当前还没有可展示的详情摘要。"),
    cards: cardsRaw.map((card, index) => normalizeMiniProgramCard(card, index)),
    actions: actionsRaw.map((action, index) => normalizeMiniProgramAction(action, index)),
    share_card: normalizeMiniShareCard(detail.share_card),
    navigation: normalizeMiniNavigation(detail.navigation),
    source_research_pulse_draft_id: readNullableString(detail.source_research_pulse_draft_id),
    total_source_papers: readNumber(detail.total_source_papers),
    total_items: readNumber(detail.total_items),
    warnings: readStringArray(detail.warnings),
    generated_at: readString(detail.generated_at, "2026-04-19T00:00:00Z"),
    delivery_state: readString(detail.delivery_state, "preview"),
    visibility_notes: readStringArray(detail.visibility_notes),
  };
}

function normalizeMiniProgramPreviews(value: unknown): MiniProgramPreviewCollection {
  const previews = isRecord(value) ? value : {};

  return {
    daily_pulse: normalizeMiniProgramDetail(previews.daily_pulse),
    paper: normalizeMiniProgramDetail(previews.paper),
    next_actions: normalizeMiniProgramDetail(previews.next_actions),
    metadata_attention: normalizeMiniProgramDetail(previews.metadata_attention),
    triage: normalizeMiniProgramDetail(previews.triage),
  };
}

function normalizeChannelStates(values: ChannelStateHint[]) {
  return values.map((value) => ({
    ...value,
    label: readString(value.label, "未命名渠道"),
    message: readString(value.message, "当前没有额外说明。"),
  }));
}

function buildEmptyOfficialSummary(
  base: OfficialAccountDailySummaryRead,
): OfficialAccountDailySummaryRead {
  const draft = clone(base);
  draft.headline = "当前没有可整理成公众号摘要的论文";
  draft.summary = "当前 mock 场景用于验证空状态，暂时没有可展示的公众号摘要内容。";
  draft.sections = draft.sections.map((section) => ({
    ...section,
    items: [],
    empty_reason: section.empty_reason ?? "当前没有可整理成公众号摘要的内容。",
  }));
  draft.highlight_count = 0;
  draft.publication_preview.digest_highlights = [];
  draft.publication_preview.digest_subtitle = "当前为空状态，仅保留预览边界。";
  draft.template_payload_preview.payload_preview = {
    title: draft.publication_preview.digest_title,
    highlights_count: 0,
    mock_only: true,
  };
  draft.warnings = ["当前 mock 场景用于验证空状态，不会真实发送公众号摘要。"];
  return draft;
}

function buildIssueOfficialSummary(
  base: OfficialAccountDailySummaryRead,
): OfficialAccountDailySummaryRead {
  const draft = clone(base);
  draft.warnings = [
    ...draft.warnings,
    "当前模板字段和绑定都只是预览占位，请先确认文案再决定后续真实接入。",
  ];
  draft.provider_preview.notes = [
    ...draft.provider_preview.notes,
    "当前没有配置模板 ID，主动作只提供本地 copy。",
  ];
  draft.binding_preview.notes = [
    ...draft.binding_preview.notes,
    "当前绑定信息只用于说明 not_sent 边界，不代表已接入真实发送能力。",
  ];
  return draft;
}

function buildEmptyDesktopDraft(base: DesktopNotificationRead): DesktopNotificationRead {
  const draft = clone(base);
  draft.title = "当前没有可展示的桌面通知草稿";
  draft.body = "先导入论文或生成今日 Pulse，再回来查看桌面通知预览。";
  draft.items = [];
  draft.actions = [];
  draft.badge_count = 0;
  draft.total_items = 0;
  draft.payload_preview = {
    notification_title: draft.title,
    notification_body: draft.body,
    badge_count: 0,
    delivery_state: "draft",
    mock_only: true,
  };
  draft.warnings = ["当前 mock 场景用于验证空状态，不会调用系统通知。"];
  draft.delivery_notes = [
    "当前没有可展示的桌面提醒草稿。",
    "后续仍然只会保留 payload 预览，不会真实推送。",
  ];
  return draft;
}

function buildIssueDesktopDraft(base: DesktopNotificationRead): DesktopNotificationRead {
  const draft = clone(base);
  draft.warnings = [
    ...draft.warnings,
    "当前桌面提醒仍然只是本地草稿，建议先处理高优先级论文和元数据补全。",
  ];
  draft.delivery_notes = [
    ...draft.delivery_notes,
    "payload_preview 仅用于前端展示和复制，不会触发系统通知。",
  ];
  return draft;
}

function buildEmptyMiniDetail(base: MiniProgramDetailRead, summary: string): MiniProgramDetailRead {
  const detail = clone(base);
  detail.summary = summary;
  detail.cards = detail.cards.map((card) => ({
    ...card,
    items: [],
    warnings: [],
    empty_reason: card.empty_reason ?? "当前没有可展示的内容。",
  }));
  detail.total_items = 0;
  detail.warnings = ["当前 mock 场景用于验证空预览，不会触发真实小程序页面。"];
  detail.visibility_notes = [
    ...detail.visibility_notes,
    "当前只保留 preview / share_safe 边界。",
  ];
  return detail;
}

function buildIssueMiniDetail(base: MiniProgramDetailRead, warning: string): MiniProgramDetailRead {
  const detail = clone(base);
  detail.warnings = [...detail.warnings, warning];
  if (detail.cards[0]) {
    detail.cards[0].warnings = [...detail.cards[0].warnings, warning];
  }
  detail.visibility_notes = [
    ...detail.visibility_notes,
    "当前仍然只展示 preview，不代表真实小程序登录、订阅消息或支付能力。",
  ];
  return detail;
}

function buildScenarioData(scenario: MockScenario): FrontendShellData {
  if (scenario === "broken") {
    throw new Error("当前 mock 场景故意返回异常，用于验证空数据与恢复提示。");
  }

  const baseOfficial = normalizeOfficialAccountDailySummary(officialAccountDailySummaryJson);
  const baseDesktop = normalizeDesktopNotification(desktopNotificationJson);
  const baseMiniPreviews = normalizeMiniProgramPreviews({
    daily_pulse: miniProgramDailyPulseJson,
    paper: miniProgramPaperJson,
    next_actions: miniProgramNextActionsJson,
    metadata_attention: miniProgramMetadataAttentionJson,
    triage: miniProgramTriageJson,
  });

  if (scenario === "empty") {
    return {
      progressSummary: normalizeProgressSummary(emptyProgressSummaryJson),
      paperProgressItems: [],
      importPreview: normalizeImportPreview(emptyImportPreviewJson),
      importCommit: normalizeImportCommit(emptyImportCommitJson),
      researchPulse: normalizeResearchPulse(emptyResearchPulseJson),
      officialAccountDailySummary: buildEmptyOfficialSummary(baseOfficial),
      desktopNotificationDraft: buildEmptyDesktopDraft(baseDesktop),
      miniProgramPreviews: {
        daily_pulse: buildEmptyMiniDetail(
          baseMiniPreviews.daily_pulse,
          "当前没有可展示的今日 Pulse 小程序详情预览。",
        ),
        paper: buildEmptyMiniDetail(
          baseMiniPreviews.paper,
          "当前没有可展示的单篇论文详情预览。",
        ),
        next_actions: buildEmptyMiniDetail(
          baseMiniPreviews.next_actions,
          "当前没有可展示的下一步动作详情预览。",
        ),
        metadata_attention: buildEmptyMiniDetail(
          baseMiniPreviews.metadata_attention,
          "当前没有可展示的元数据待补全详情预览。",
        ),
        triage: buildEmptyMiniDetail(
          baseMiniPreviews.triage,
          "当前没有可展示的新导入待筛选详情预览。",
        ),
      },
      channelStates: normalizeChannelStates(sharedChannelStates),
    };
  }

  if (scenario === "issues") {
    return {
      progressSummary: normalizeProgressSummary(progressSummaryJson),
      paperProgressItems: (paperProgressItemsJson as unknown[]).map((item, index) =>
        normalizeProgressItem(item, index),
      ),
      importPreview: normalizeImportPreview(importPreviewWithErrorsJson),
      importCommit: normalizeImportCommit(emptyImportCommitJson),
      researchPulse: normalizeResearchPulse(researchPulseJson),
      officialAccountDailySummary: buildIssueOfficialSummary(baseOfficial),
      desktopNotificationDraft: buildIssueDesktopDraft(baseDesktop),
      miniProgramPreviews: {
        daily_pulse: buildIssueMiniDetail(
          baseMiniPreviews.daily_pulse,
          "当前仅展示 share-safe 小程序预览，请先确认卡片文案和 path。",
        ),
        paper: buildIssueMiniDetail(
          baseMiniPreviews.paper,
          "这条论文详情仍有待补全字段，当前只建议做 preview 审阅。",
        ),
        next_actions: buildIssueMiniDetail(
          baseMiniPreviews.next_actions,
          "动作列表当前仍是 preview，先确认 path 和分享卡片文案。",
        ),
        metadata_attention: buildIssueMiniDetail(
          baseMiniPreviews.metadata_attention,
          "元数据待补全仍未处理，建议先补全再考虑真实接入。",
        ),
        triage: buildIssueMiniDetail(
          baseMiniPreviews.triage,
          "当前待筛选列表仅为前端预览，不会真实同步到微信小程序。",
        ),
      },
      channelStates: normalizeChannelStates(sharedChannelStates),
    };
  }

  return {
    progressSummary: normalizeProgressSummary(progressSummaryJson),
    paperProgressItems: (paperProgressItemsJson as unknown[]).map((item, index) =>
      normalizeProgressItem(item, index),
    ),
    importPreview: normalizeImportPreview(importPreviewJson),
    importCommit: normalizeImportCommit(importCommitJson),
    researchPulse: normalizeResearchPulse(researchPulseJson),
    officialAccountDailySummary: baseOfficial,
    desktopNotificationDraft: baseDesktop,
    miniProgramPreviews: baseMiniPreviews,
    channelStates: normalizeChannelStates(sharedChannelStates),
  };
}

export async function loadShellData(
  mode: DataMode,
  scenario: MockScenario = "default",
): Promise<FrontendShellData> {
  await sleep(loadDelayMs);

  if (mode === "api") {
    throw new Error(
      "当前前端壳只启用 mock mode。real API mode 仅预留后续内部联调，不在本轮启用。",
    );
  }

  return clone(buildScenarioData(scenario));
}

export const apiModePlan = {
  progressList: "GET /papers/progress",
  importPreview: "POST /papers/import-preview",
  importCommit: "POST /papers/import-commit",
  progressSummary: "GET /papers/progress/summary",
  pulseContext: "GET /papers/progress/pulse-context",
  dailyPulse: "POST /pulse/papers/daily",
  officialAccountDailySummary: "POST /pulse/papers/official-account/daily-summary",
  desktopNotificationDraft: "POST /pulse/papers/desktop-notification/draft",
  miniProgramDetailPreview: "POST /pulse/papers/mini-program/detail/preview",
} as const;
