export type AppPage =
  | "home"
  | "import"
  | "pulse"
  | "progress"
  | "officialDraft"
  | "desktopDraft"
  | "miniPreview";

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

export interface OfficialAccountDailySummaryItem {
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
  summary_line: string;
  metadata_warnings: string[];
  tags: string[];
  source_format: string | null;
}

export interface OfficialAccountDailySummarySection {
  section_id: string;
  title: string;
  description: string;
  items: OfficialAccountDailySummaryItem[];
  empty_reason: string | null;
}

export interface OfficialAccountDailySummaryHighlight {
  sort_order: number;
  section_id: string;
  section_title: string;
  paper_id: string;
  title: string;
  summary: string;
  why_now: string;
  suggested_action: string;
}

export interface OfficialAccountPublicationPreview {
  digest_title: string;
  digest_subtitle: string;
  digest_highlights: OfficialAccountDailySummaryHighlight[];
  primary_cta_text: string;
  primary_cta_path: string | null;
  mini_program_path: string | null;
  article_url: string | null;
}

export interface OfficialAccountTemplatePayloadPreview {
  template_id_configured: boolean;
  field_mapping: Record<string, string>;
  logical_fields: Record<string, string>;
  payload_preview: Record<string, unknown>;
}

export interface OfficialAccountBindingTargetPreview {
  binding_id: string;
  channel_type: string;
  bind_state: string;
  display_label: string | null;
  subscribed: boolean;
  digest_enabled: boolean;
  masked_openid: string;
}

export interface OfficialAccountBindingPreview {
  active_binding_count: number;
  selected_binding: OfficialAccountBindingTargetPreview | null;
  notes: string[];
}

export interface OfficialAccountProviderPreview {
  provider_mode: string;
  transport_kind: string;
  template_id_configured: boolean;
  template_field_mapping_configured: boolean;
  article_base_url_configured: boolean;
  mini_program_app_id_configured: boolean;
  callback_enabled: boolean;
  real_send_enabled: boolean;
  notes: string[];
}

export interface OfficialAccountDailySummaryRead {
  draft_id: string;
  source_research_pulse_draft_id: string;
  user_id: string;
  pulse_date: string;
  timezone: string;
  dry_run: boolean;
  title: string;
  headline: string;
  summary: string;
  sections: OfficialAccountDailySummarySection[];
  highlight_count: number;
  publication_preview: OfficialAccountPublicationPreview;
  template_payload_preview: OfficialAccountTemplatePayloadPreview;
  binding_preview: OfficialAccountBindingPreview;
  provider_preview: OfficialAccountProviderPreview;
  total_source_papers: number;
  warnings: string[];
  generated_at: string;
  source_context_notes: string[];
}

export interface DesktopNotificationItemRead {
  paper_id: string;
  title: string;
  line: string;
  reason: string;
  suggested_action: string;
  priority: Priority;
  reading_status: string;
  research_stage: string;
  metadata_warnings: string[];
  url: string | null;
  doi: string | null;
  tags: string[];
  source_format: string | null;
}

export interface DesktopNotificationActionRead {
  action_id: string;
  label: string;
  kind: string;
  deep_link: string;
  payload: Record<string, unknown>;
}

export interface DesktopNotificationRead {
  draft_id: string;
  source_research_pulse_draft_id: string;
  user_id: string;
  pulse_date: string;
  timezone: string;
  title: string;
  body: string;
  notification_type: string;
  urgency: string;
  badge_count: number;
  items: DesktopNotificationItemRead[];
  actions: DesktopNotificationActionRead[];
  deep_link: string;
  payload_preview: Record<string, unknown>;
  total_source_papers: number;
  total_items: number;
  warnings: string[];
  generated_at: string;
  delivery_state: DeliveryState | string;
  delivery_notes: string[];
}

export interface MiniProgramDetailItemRead {
  item_id: string;
  paper_id: string | null;
  title: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  doi: string | null;
  url: string | null;
  priority: Priority | null;
  reading_status: string | null;
  research_stage: string | null;
  next_action: string | null;
  reason: string;
  suggested_action: string;
  metadata_warnings: string[];
  tags: string[];
  source_format: string | null;
  safe_abstract: string | null;
  detail_path: string;
}

export interface MiniProgramDetailCardRead {
  card_id: string;
  card_type: string;
  title: string;
  subtitle: string | null;
  body: string;
  items: MiniProgramDetailItemRead[];
  badges: string[];
  warnings: string[];
  empty_reason: string | null;
}

export interface MiniProgramDetailActionRead {
  action_id: string;
  label: string;
  kind: string;
  path: string;
  payload: Record<string, unknown>;
}

export interface MiniProgramShareCardRead {
  title: string;
  summary: string;
  path: string;
  image_placeholder: string | null;
  share_safe: boolean;
  redacted_fields: string[];
}

export interface MiniProgramNavigationRead {
  current_path: string;
  back_path: string;
  related_paths: string[];
}

export interface MiniProgramDetailRead {
  detail_id: string;
  detail_type: string;
  user_id: string;
  pulse_date: string | null;
  timezone: string;
  title: string;
  subtitle: string;
  summary: string;
  cards: MiniProgramDetailCardRead[];
  actions: MiniProgramDetailActionRead[];
  share_card: MiniProgramShareCardRead;
  navigation: MiniProgramNavigationRead;
  source_research_pulse_draft_id: string | null;
  total_source_papers: number;
  total_items: number;
  warnings: string[];
  generated_at: string;
  delivery_state: DeliveryState | string;
  visibility_notes: string[];
}

export interface MiniProgramPreviewCollection {
  daily_pulse: MiniProgramDetailRead;
  paper: MiniProgramDetailRead;
  next_actions: MiniProgramDetailRead;
  metadata_attention: MiniProgramDetailRead;
  triage: MiniProgramDetailRead;
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
  officialAccountDailySummary: OfficialAccountDailySummaryRead;
  desktopNotificationDraft: DesktopNotificationRead;
  miniProgramPreviews: MiniProgramPreviewCollection;
  channelStates: ChannelStateHint[];
}
