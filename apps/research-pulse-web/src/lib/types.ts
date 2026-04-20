export type AppPage = "home" | "import" | "pulse" | "progress";

export type DataMode = "mock" | "api";

export type MockScenario = "default" | "empty" | "issues" | "broken";

export type DeliveryState = "draft" | "preview" | "not_sent";

export type Priority = "low" | "normal" | "high" | "urgent";

export interface ImportPreviewRecord {
  source_index: number;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  keywords: string[];
  warnings: string[];
  errors: string[];
  can_commit: boolean;
  selected: boolean;
}

export interface ImportPreviewRead {
  preview_id: string;
  source_format: string;
  created_at: string;
  total_records: number;
  valid_records_count: number;
  warning_records_count: number;
  error_records_count: number;
  records: ImportPreviewRecord[];
}

export interface ImportCommitRecordResult {
  source_index: number;
  status: "committed" | "skipped" | "failed";
  reason: string;
  warnings?: string[];
  errors?: string[];
}

export interface ImportCommitRead {
  preview_id: string;
  user_id: string;
  source_format: string;
  dry_run: boolean;
  committed_at: string;
  total_selected: number;
  committed_count: number;
  skipped_count: number;
  failed_count: number;
  record_results: ImportCommitRecordResult[];
}

export interface PaperProgressSummaryRead {
  total_papers: number;
  unread_count: number;
  reading_count: number;
  read_count: number;
  high_priority_count: number;
  urgent_count: number;
  with_next_action_count: number;
  by_reading_status: Record<string, number>;
  by_research_stage: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface PaperProgressItemRead {
  paper_id: string;
  user_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  source_format: string;
  reading_status: string;
  research_stage: string;
  priority: Priority;
  priority_score: number;
  next_action: string | null;
  user_note: string | null;
  research_note: string | null;
  tags: string[];
  keywords: string[];
  imported_at: string;
  created_at: string;
  updated_at: string;
  last_touch_at: string;
  warnings: string[];
}

export interface ResearchPulseItem {
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  priority: Priority;
  reading_status: string;
  research_stage: string;
  next_action: string | null;
  reason: string;
  suggested_action: string;
  metadata_warnings: string[];
  tags: string[];
  source_format: string;
}

export interface ResearchPulseSection {
  section_id: string;
  title: string;
  description: string;
  empty_reason: string | null;
  items: ResearchPulseItem[];
}

export interface ResearchPulseRead {
  draft_id: string;
  user_id: string;
  pulse_date: string;
  timezone: string;
  dry_run: boolean;
  generated_at: string;
  title: string;
  summary: string;
  warnings: string[];
  source_context_notes: string[];
  sections: ResearchPulseSection[];
}

export interface ChannelStateHint {
  id: string;
  label: string;
  state: DeliveryState;
  message: string;
}

export interface MockScenarioOption {
  id: MockScenario;
  label: string;
  description: string;
}

export interface FrontendShellData {
  progressSummary: PaperProgressSummaryRead;
  paperProgressItems: PaperProgressItemRead[];
  importPreview: ImportPreviewRead;
  importCommit: ImportCommitRead;
  researchPulse: ResearchPulseRead;
  channelStates: ChannelStateHint[];
}
