use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct UserConnectionRead {
    pub user_id: String,
    pub name: String,
    pub email: Option<String>,
    pub field: Option<String>,
    pub base_url: String,
    pub device_id: String,
    pub device_display_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct SyncStatusRead {
    pub connected: bool,
    pub base_url: Option<String>,
    pub device_id: Option<String>,
    pub device_display_name: Option<String>,
    pub last_synced_at: Option<String>,
    pub last_event_sequence: i64,
    pub last_error: Option<String>,
    pub pending_mutation_count: i64,
    pub failed_mutation_count: i64,
    pub recent_outbox_errors: Vec<String>,
    pub current_user_summary: Option<UserConnectionRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PendingMutationRead {
    pub id: String,
    pub client_mutation_id: String,
    pub mutation_type: String,
    pub resource_type: String,
    pub resource_id: Option<String>,
    pub payload: Value,
    pub status: String,
    pub attempt_count: i64,
    pub last_error: Option<String>,
    pub resulting_event_sequence: Option<i64>,
    pub created_at: String,
    pub updated_at: String,
    pub last_attempted_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SubscriptionPolicyRead {
    pub id: String,
    pub user_id: String,
    pub channel: String,
    pub enabled: bool,
    pub frequency: String,
    pub quiet_hours: Option<Value>,
    pub frequency_cap: i64,
    pub policy: Value,
    pub updated_at: Option<String>,
    pub pending_mutation_count: i64,
    pub last_mutation_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QuietHoursWindowRead {
    pub start: String,
    pub end: String,
    pub timezone: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DeliveryControlSettingsRead {
    pub id: String,
    pub user_id: String,
    pub channel: String,
    pub enabled: bool,
    pub frequency: String,
    pub quiet_hours: Vec<QuietHoursWindowRead>,
    pub raw_quiet_hours: Option<Value>,
    pub timezone: String,
    pub allowed_weekdays: Vec<i64>,
    pub muted_until: Option<String>,
    pub minimum_selected_cards: Option<i64>,
    pub skip_if_no_today_focus: bool,
    pub frequency_cap: i64,
    pub updated_at: Option<String>,
    pub pending_mutation_count: i64,
    pub last_mutation_error: Option<String>,
    pub raw_policy: Value,
    pub local_settings_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DeliveryControlLocalHintRead {
    pub subscription_policy_id: String,
    pub channel: String,
    pub effective_timezone: String,
    pub current_local_time: String,
    pub local_weekday: i64,
    pub quiet_hours_active: bool,
    pub muted_until_active: bool,
    pub weekday_blocked: bool,
    pub next_allowed_at_approx: Option<String>,
    pub notes: Vec<String>,
    pub local_settings_error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WorkspaceStatusRead {
    pub root_path: Option<String>,
    pub status: String,
    pub layout_version: i64,
    pub last_validated_at: Option<String>,
    pub last_error: Option<String>,
    pub managed_attachment_count: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperWorkspaceRead {
    pub paper_id: String,
    pub paper_title: String,
    pub workspace_rel_path: String,
    pub workspace_abs_path: Option<String>,
    pub workspace_ready: bool,
    pub attachment_count: i64,
    pub last_imported_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperAttachmentRead {
    pub id: String,
    pub paper_id: String,
    pub attachment_kind: String,
    pub storage_mode: String,
    pub original_file_name: String,
    pub stored_file_name: String,
    pub file_extension: Option<String>,
    pub relative_path: String,
    pub absolute_path: Option<String>,
    pub source_path: String,
    pub size_bytes: Option<i64>,
    pub mime_type: Option<String>,
    pub sha256: Option<String>,
    pub status: String,
    pub imported_at: String,
    pub updated_at: String,
    pub last_opened_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct NoteTemplateRead {
    pub kind: String,
    pub title: String,
    pub description: String,
    pub default_file_name_pattern: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperNoteSummaryRead {
    pub id: String,
    pub paper_id: String,
    pub template_kind: String,
    pub title: String,
    pub file_name: String,
    pub relative_path: String,
    pub absolute_path: Option<String>,
    pub content_format: String,
    pub source_mode: String,
    pub status: String,
    pub size_bytes: Option<i64>,
    pub sha256: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub last_opened_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperNoteDetailRead {
    pub note: PaperNoteSummaryRead,
    pub content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct NoteActionResultRead {
    pub note: PaperNoteDetailRead,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReviewRoundSummaryRead {
    pub id: String,
    pub paper_id: String,
    pub round_label: String,
    pub venue: Option<String>,
    pub decision_label: Option<String>,
    pub status: String,
    pub source_mode: String,
    pub reviewer_count: i64,
    pub generated_response_note_id: Option<String>,
    pub generated_matrix_note_id: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReviewCommentItemRead {
    pub id: String,
    pub review_round_id: String,
    pub paper_id: String,
    pub reviewer_label: String,
    pub comment_code: Option<String>,
    pub sort_order: i64,
    pub comment_text: String,
    pub category: Option<String>,
    pub disposition: String,
    pub response_summary: Option<String>,
    pub action_note: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct GeneratedReviewNoteRead {
    pub kind: String,
    pub note_id: String,
    pub title: String,
    pub relative_path: String,
    pub status: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReviewRoundDetailRead {
    pub round: ReviewRoundSummaryRead,
    pub comments: Vec<ReviewCommentItemRead>,
    pub generated_response_note: Option<GeneratedReviewNoteRead>,
    pub generated_matrix_note: Option<GeneratedReviewNoteRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReviewActionResultRead {
    pub message: String,
    pub round: Option<ReviewRoundSummaryRead>,
    pub comment: Option<ReviewCommentItemRead>,
    pub detail: Option<ReviewRoundDetailRead>,
    pub generated_note: Option<GeneratedReviewNoteRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DigestHighlightRead {
    pub sort_order: i64,
    pub pulse_card_id: String,
    pub card_type: String,
    pub source_paper_id: Option<String>,
    pub title: String,
    pub summary: String,
    pub why_now: Option<String>,
    pub action_text: Option<String>,
    pub deep_link: Option<String>,
    pub paper: Option<PaperListItemRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct TodaySectionItemRead {
    pub sort_order: i64,
    pub pulse_card_id: String,
    pub card_type: String,
    pub source_paper_id: Option<String>,
    pub title: String,
    pub summary: String,
    pub why_now: Option<String>,
    pub action_text: Option<String>,
    pub deep_link: Option<String>,
    pub paper: Option<PaperListItemRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct TodaySectionRead {
    pub kind: String,
    pub title: String,
    pub item_count: i64,
    pub items: Vec<TodaySectionItemRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct TodayQuickStatsRead {
    pub selected_card_count: i64,
    pub related_paper_count: i64,
    pub signal_update_count: i64,
    pub touched_paper_count: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct TodayFocusCardRead {
    pub sort_order: i64,
    pub pulse_card_id: String,
    pub card_type: String,
    pub source_paper_id: Option<String>,
    pub title: String,
    pub summary: String,
    pub why_now: Option<String>,
    pub action_text: Option<String>,
    pub deep_link: Option<String>,
    pub paper: Option<PaperListItemRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct TodayPublicationPreviewRead {
    pub digest_title: Option<String>,
    pub digest_subtitle: Option<String>,
    pub digest_highlights: Vec<DigestHighlightRead>,
    pub primary_cta_text: Option<String>,
    pub primary_cta_path: Option<String>,
    pub mini_program_path: Option<String>,
    pub article_url: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TodayOverviewRead {
    pub state: String,
    pub issue_id: Option<String>,
    pub issue_date: Option<String>,
    pub status: Option<String>,
    pub title: Option<String>,
    pub summary: Option<String>,
    pub highlight_count: i64,
    pub selected_card_count: i64,
    pub deep_link_path: Option<String>,
    pub highlights: Vec<DigestHighlightRead>,
    pub is_structured: bool,
    pub section_order: Vec<String>,
    pub sections: Vec<TodaySectionRead>,
    pub quick_stats: Option<TodayQuickStatsRead>,
    pub focus_card: Option<TodayFocusCardRead>,
    pub publication_preview: Option<TodayPublicationPreviewRead>,
    pub fallback_mode: String,
    pub message: Option<String>,
    pub updated_at: Option<String>,
}

impl Default for TodayOverviewRead {
    fn default() -> Self {
        Self {
            state: "empty".to_string(),
            issue_id: None,
            issue_date: None,
            status: None,
            title: None,
            summary: None,
            highlight_count: 0,
            selected_card_count: 0,
            deep_link_path: None,
            highlights: Vec::new(),
            is_structured: false,
            section_order: Vec::new(),
            sections: Vec::new(),
            quick_stats: None,
            focus_card: None,
            publication_preview: None,
            fallback_mode: "empty".to_string(),
            message: Some("No digest issue is cached yet.".to_string()),
            updated_at: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperListItemRead {
    pub id: String,
    pub user_id: String,
    pub title: String,
    pub paper_type: String,
    pub stage: String,
    pub venue: Option<String>,
    pub priority: i64,
    pub next_action: Option<String>,
    pub blocker: Option<String>,
    pub last_touch_at: Option<String>,
    pub progress_percentage: i64,
    pub updated_at: Option<String>,
    pub pending_mutation_count: i64,
    pub last_mutation_error: Option<String>,
    pub attachment_count: i64,
    pub workspace_ready: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ProgressEventRead {
    pub id: String,
    pub paper_id: String,
    pub stage: String,
    pub happened_at: String,
    pub summary: String,
    pub owner: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SignalSnapshotRead {
    pub id: String,
    pub paper_id: String,
    pub source: String,
    pub citation_count: Option<i64>,
    pub download_count: Option<i64>,
    pub read_count: Option<i64>,
    pub inclusion_status: Option<String>,
    pub fetched_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperDetailRead {
    pub id: String,
    pub user_id: String,
    pub title: String,
    pub paper_type: String,
    pub stage: String,
    pub venue: Option<String>,
    pub priority: i64,
    pub next_action: Option<String>,
    pub blocker: Option<String>,
    pub last_touch_at: Option<String>,
    pub progress_percentage: i64,
    pub updated_at: Option<String>,
    pub identifiers: Value,
    pub source_links: Vec<String>,
    pub progress_events: Vec<ProgressEventRead>,
    pub signal_snapshots: Vec<SignalSnapshotRead>,
    pub pending_mutation_count: i64,
    pub last_mutation_error: Option<String>,
    pub workspace: PaperWorkspaceRead,
    pub attachments: Vec<PaperAttachmentRead>,
    pub notes: Vec<PaperNoteSummaryRead>,
    pub note_count: i64,
    pub review_rounds: Vec<ReviewRoundSummaryRead>,
    pub review_round_count: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppBootstrapRead {
    pub sync_status: SyncStatusRead,
    pub today_overview: TodayOverviewRead,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectDeviceInput {
    pub base_url: String,
    pub device_token: String,
    pub device_display_name: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectDeviceResponse {
    pub sync_status: SyncStatusRead,
    pub connection: UserConnectionRead,
    pub today_overview: TodayOverviewRead,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SyncNowResponse {
    pub sync_status: SyncStatusRead,
    pub pushed_count: i64,
    pub applied_count: i64,
    pub duplicate_count: i64,
    pub failed_count: i64,
    pub pages_fetched: i64,
    pub events_applied: i64,
    pub acknowledged_sequence: i64,
    pub pending_mutation_count: i64,
    pub failed_mutation_count: i64,
    pub today_overview: TodayOverviewRead,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct ListPapersInput {
    pub limit: Option<usize>,
    pub paper_type: Option<String>,
    pub stage: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ChooseWorkspaceRootInput {
    pub selected_path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EnsurePaperWorkspaceInput {
    pub paper_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportPaperAttachmentsInput {
    pub paper_id: String,
    pub attachment_kind: String,
    pub source_paths: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RefreshPaperWorkspaceInput {
    pub paper_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListPaperNotesInput {
    pub paper_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreatePaperNoteFromTemplateInput {
    pub paper_id: String,
    pub template_kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateBlankPaperNoteInput {
    pub paper_id: String,
    pub title: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SavePaperNoteInput {
    pub note_id: String,
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RefreshPaperNotesInput {
    pub paper_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListReviewRoundsInput {
    pub paper_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateReviewRoundInput {
    pub paper_id: String,
    pub round_label: String,
    pub venue: Option<String>,
    pub decision_label: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateReviewRoundInput {
    pub review_round_id: String,
    pub round_label: Option<String>,
    pub venue: Option<String>,
    pub decision_label: Option<String>,
    pub status: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ListReviewCommentsInput {
    pub review_round_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AddReviewCommentInput {
    pub review_round_id: String,
    pub reviewer_label: String,
    pub comment_code: Option<String>,
    pub comment_text: String,
    pub category: Option<String>,
    pub disposition: Option<String>,
    pub response_summary: Option<String>,
    pub action_note: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateReviewCommentInput {
    pub comment_id: String,
    pub reviewer_label: Option<String>,
    pub comment_code: Option<String>,
    pub comment_text: Option<String>,
    pub category: Option<String>,
    pub disposition: Option<String>,
    pub response_summary: Option<String>,
    pub action_note: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DeleteReviewCommentInput {
    pub comment_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReviewRoundLookupInput {
    pub review_round_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaperAttachmentImportResultRead {
    pub source_path: String,
    pub status: String,
    pub message: Option<String>,
    pub attachment: Option<PaperAttachmentRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportPaperAttachmentsResponse {
    pub workspace: PaperWorkspaceRead,
    pub results: Vec<PaperAttachmentImportResultRead>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueuePaperPatchInput {
    pub paper_id: String,
    pub stage: Option<String>,
    pub venue: Option<String>,
    pub next_action: Option<String>,
    pub blocker: Option<String>,
    pub priority: Option<i64>,
    pub last_touch_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueueProgressEventCreateInput {
    pub paper_id: String,
    pub stage: String,
    pub happened_at: String,
    pub summary: String,
    pub owner: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct QueueSubscriptionPolicyPatchInput {
    pub subscription_policy_id: String,
    pub enabled: Option<bool>,
    pub quiet_hours: Option<Value>,
    pub frequency_cap: Option<i64>,
    pub policy: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct DeliveryControlHintLookupInput {
    pub subscription_policy_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct WriteActionResultRead {
    pub mutation: PendingMutationRead,
    pub sync_attempted: bool,
    pub sync_succeeded: bool,
    pub sync_error: Option<String>,
    pub sync_status: SyncStatusRead,
    pub pending_mutation_count: i64,
    pub failed_mutation_count: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncUser {
    pub id: String,
    pub name: String,
    pub email: Option<String>,
    pub field: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncDevice {
    pub id: String,
    pub user_id: String,
    pub client_type: String,
    pub display_name: String,
    pub is_active: bool,
    pub last_seen_at: Option<String>,
    pub created_at: String,
    pub updated_at: String,
    pub last_event_sequence: i64,
    pub last_synced_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncMe {
    pub device: RemoteSyncDevice,
    pub user: RemoteSyncUser,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncEvent {
    pub id: String,
    pub sequence: i64,
    pub user_id: String,
    pub entity_type: String,
    pub entity_id: String,
    pub event_type: String,
    pub payload: Value,
    pub event_source: String,
    pub occurred_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncFeed {
    pub events: Vec<RemoteSyncEvent>,
    pub next_after_sequence: i64,
    pub has_more: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncAck {
    pub last_event_sequence: i64,
    pub last_synced_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncMutationRequest {
    pub client_mutation_id: String,
    pub mutation_type: String,
    pub resource_type: String,
    pub resource_id: Option<String>,
    pub payload: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncPushRequest {
    pub mutations: Vec<RemoteSyncMutationRequest>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncMutationResult {
    pub client_mutation_id: String,
    pub status: String,
    pub error_message: Option<String>,
    pub resulting_event_sequence: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteSyncPushResponse {
    pub results: Vec<RemoteSyncMutationResult>,
}
