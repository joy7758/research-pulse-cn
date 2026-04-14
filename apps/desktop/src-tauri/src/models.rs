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
pub struct DigestHighlightRead {
    pub sort_order: i64,
    pub pulse_card_id: String,
    pub card_type: String,
    pub source_paper_id: Option<String>,
    pub title: String,
    pub summary: String,
    pub why_now: Option<String>,
    pub paper: Option<PaperListItemRead>,
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
