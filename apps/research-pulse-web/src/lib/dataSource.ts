import emptyImportCommitJson from "../data/mock/empty_import_commit.json";
import emptyImportPreviewJson from "../data/mock/empty_import_preview.json";
import emptyProgressSummaryJson from "../data/mock/empty_paper_progress_summary.json";
import emptyResearchPulseJson from "../data/mock/empty_research_pulse.json";
import importCommitJson from "../data/mock/import_commit.json";
import importPreviewWithErrorsJson from "../data/mock/import_preview_with_errors.json";
import importPreviewJson from "../data/mock/import_preview.json";
import paperProgressItemsJson from "../data/mock/paper_progress_items.json";
import progressSummaryJson from "../data/mock/paper_progress_summary.json";
import researchPulseJson from "../data/mock/research_pulse.json";
import type {
  ChannelStateHint,
  DataMode,
  FrontendShellData,
  ImportCommitRead,
  ImportCommitRecordResult,
  ImportPreviewRead,
  ImportPreviewRecord,
  MockScenario,
  MockScenarioOption,
  PaperProgressItemRead,
  PaperProgressSummaryRead,
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
    message: "只保留草稿入口，不触发真实微信发送。",
  },
  {
    id: "desktop",
    label: "桌面通知",
    state: "not_sent",
    message: "只保留通知草稿，不调用系统通知。",
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
    description: "验证没有论文、没有待预览记录时的引导文案。",
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
  const priority =
    item.priority === "low" ||
    item.priority === "normal" ||
    item.priority === "high" ||
    item.priority === "urgent"
      ? item.priority
      : "normal";

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
    priority_score: readNumber(item.priority_score, priority === "urgent" ? 5 : priority === "high" ? 4 : priority === "low" ? 1 : 3),
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
  const priority =
    item.priority === "low" ||
    item.priority === "normal" ||
    item.priority === "high" ||
    item.priority === "urgent"
      ? item.priority
      : "normal";

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

function normalizeChannelStates(values: ChannelStateHint[]) {
  return values.map((value) => ({
    ...value,
    label: readString(value.label, "未命名渠道"),
    message: readString(value.message, "当前没有额外说明。"),
  }));
}

function buildScenarioData(scenario: MockScenario): FrontendShellData {
  if (scenario === "broken") {
    throw new Error("当前 mock 场景故意返回异常，用于验证空数据与恢复提示。");
  }

  if (scenario === "empty") {
    return {
      progressSummary: normalizeProgressSummary(emptyProgressSummaryJson),
      paperProgressItems: [],
      importPreview: normalizeImportPreview(emptyImportPreviewJson),
      importCommit: normalizeImportCommit(emptyImportCommitJson),
      researchPulse: normalizeResearchPulse(emptyResearchPulseJson),
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
} as const;
