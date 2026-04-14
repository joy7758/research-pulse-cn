use std::path::PathBuf;

use anyhow::{Context, Result};
use serde_json::{json, Value};
use uuid::Uuid;

use crate::cache::{LocalCache, PushOutcomeSummary};
use crate::error::invalid_state;
use crate::models::{
    AppBootstrapRead, ConnectDeviceInput, ConnectDeviceResponse, ListPapersInput,
    PaperDetailRead, PaperListItemRead, PendingMutationRead, QueuePaperPatchInput,
    QueueProgressEventCreateInput, QueueSubscriptionPolicyPatchInput, RemoteSyncMutationRequest,
    RemoteSyncPushRequest, SubscriptionPolicyRead, SyncNowResponse, SyncStatusRead,
    TodayOverviewRead, UserConnectionRead, WriteActionResultRead,
};
use crate::secret_store::FileSecretStore;
use crate::sync_client::{ReqwestSyncBackendApi, SyncBackendApi};

const FEED_PAGE_LIMIT: usize = 100;

#[derive(Debug, Clone)]
pub struct DesktopPaths {
    pub app_data_dir: PathBuf,
    pub cache_db_path: PathBuf,
    pub secret_store_path: PathBuf,
}

#[derive(Debug, Clone)]
pub struct DesktopService {
    pub paths: DesktopPaths,
}

impl DesktopService {
    pub fn new(paths: DesktopPaths) -> Result<Self> {
        std::fs::create_dir_all(&paths.app_data_dir)
            .with_context(|| format!("failed to create {}", paths.app_data_dir.display()))?;
        let cache = LocalCache::new(paths.cache_db_path.clone());
        cache.initialize()?;
        Ok(Self { paths })
    }

    pub fn app_bootstrap(&self) -> Result<AppBootstrapRead> {
        Ok(AppBootstrapRead {
            sync_status: self.get_sync_status()?,
            today_overview: self.get_today_overview()?,
        })
    }

    pub fn get_sync_status(&self) -> Result<SyncStatusRead> {
        let cache = self.cache();
        let token_present = self.secret_store().load_device_token()?.is_some();
        cache.sync_status(token_present)
    }

    pub fn get_today_overview(&self) -> Result<TodayOverviewRead> {
        self.cache().read_today_overview()
    }

    pub fn list_papers(&self, filters: Option<ListPapersInput>) -> Result<Vec<PaperListItemRead>> {
        let filters = filters.unwrap_or_default();
        self.cache().list_papers(
            filters.paper_type.as_deref(),
            filters.stage.as_deref(),
            filters.limit,
        )
    }

    pub fn get_paper_detail(&self, paper_id: &str) -> Result<PaperDetailRead> {
        self.cache().get_paper_detail(paper_id)
    }

    pub fn list_subscription_policies(&self) -> Result<Vec<SubscriptionPolicyRead>> {
        self.cache().list_subscription_policies()
    }

    pub fn list_pending_mutations(&self) -> Result<Vec<PendingMutationRead>> {
        self.cache().list_pending_mutations()
    }

    pub fn connect_with<A: SyncBackendApi>(
        &self,
        input: ConnectDeviceInput,
        api: &A,
    ) -> Result<ConnectDeviceResponse> {
        let base_url = normalize_base_url(&input.base_url)?;
        let remote = api.sync_me()?;

        let cache = self.cache();
        let current = cache.sync_state_record()?;
        let should_reset = current.device_id.as_deref() != Some(remote.device.id.as_str())
            || current.base_url.as_deref() != Some(base_url.as_str())
            || current.user_id.as_deref() != Some(remote.user.id.as_str());

        if should_reset {
            cache.reset_local_cache()?;
        }

        self.secret_store().save_device_token(input.device_token.trim())?;
        let effective_display_name = input
            .device_display_name
            .filter(|value| !value.trim().is_empty())
            .unwrap_or_else(|| remote.device.display_name.clone());
        cache.upsert_connection(
            &base_url,
            &remote.device.id,
            &effective_display_name,
            &remote.user.id,
            &remote.user.name,
            remote.user.email.as_deref(),
            remote.user.field.as_deref(),
        )?;
        let sync = self.sync_with(api)?;
        let connection = sync
            .sync_status
            .current_user_summary
            .clone()
            .ok_or_else(|| invalid_state("connected desktop state is missing user summary"))?;
        Ok(ConnectDeviceResponse {
            sync_status: sync.sync_status,
            connection,
            today_overview: sync.today_overview,
        })
    }

    pub fn sync_now(&self) -> Result<SyncNowResponse> {
        let (base_url, token) = self.load_connection()?;
        let api = ReqwestSyncBackendApi::new(base_url, token)?;
        self.sync_with(&api)
    }

    pub fn queue_paper_patch(&self, input: QueuePaperPatchInput) -> Result<WriteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        if input.priority.is_some_and(|value| value < 1) {
            return Err(invalid_state("priority must be at least 1"));
        }

        let mut payload = serde_json::Map::new();
        if let Some(stage) = input.stage.and_then(non_empty) {
            payload.insert("stage".to_string(), Value::String(stage));
        }
        if let Some(venue) = input.venue {
            payload.insert("venue".to_string(), value_or_null(venue));
        }
        if let Some(next_action) = input.next_action {
            payload.insert("next_action".to_string(), value_or_null(next_action));
        }
        if let Some(blocker) = input.blocker {
            payload.insert("blocker".to_string(), value_or_null(blocker));
        }
        if let Some(priority) = input.priority {
            payload.insert("priority".to_string(), Value::from(priority));
        }
        if let Some(last_touch_at) = input.last_touch_at {
            payload.insert("last_touch_at".to_string(), value_or_null(last_touch_at));
        }
        if payload.is_empty() {
            return Err(invalid_state("paper.patch requires at least one field"));
        }

        self.cache().get_paper_detail(&input.paper_id)?;
        self.queue_mutation_and_maybe_sync(
            "paper.patch",
            "paper_profile",
            Some(input.paper_id),
            Value::Object(payload),
        )
    }

    pub fn queue_progress_event_create(
        &self,
        input: QueueProgressEventCreateInput,
    ) -> Result<WriteActionResultRead> {
        if input.paper_id.trim().is_empty() {
            return Err(invalid_state("paper_id is required"));
        }
        if input.stage.trim().is_empty() {
            return Err(invalid_state("stage is required"));
        }
        if input.happened_at.trim().is_empty() {
            return Err(invalid_state("happened_at is required"));
        }
        if input.summary.trim().is_empty() {
            return Err(invalid_state("summary is required"));
        }

        self.cache().get_paper_detail(&input.paper_id)?;
        self.queue_mutation_and_maybe_sync(
            "progress_event.create",
            "progress_event",
            Some(input.paper_id),
            json!({
                "stage": input.stage.trim(),
                "happened_at": input.happened_at.trim(),
                "summary": input.summary.trim(),
                "owner": input.owner.and_then(non_empty),
            }),
        )
    }

    pub fn queue_subscription_policy_patch(
        &self,
        input: QueueSubscriptionPolicyPatchInput,
    ) -> Result<WriteActionResultRead> {
        if input.subscription_policy_id.trim().is_empty() {
            return Err(invalid_state("subscription_policy_id is required"));
        }
        if input.frequency_cap.is_some_and(|value| value < 1) {
            return Err(invalid_state("frequencyCap must be at least 1"));
        }

        let mut payload = serde_json::Map::new();
        if let Some(enabled) = input.enabled {
            payload.insert("enabled".to_string(), Value::Bool(enabled));
        }
        if let Some(quiet_hours) = input.quiet_hours {
            if !quiet_hours.is_object() && !quiet_hours.is_null() {
                return Err(invalid_state("quietHours must be an object or null"));
            }
            payload.insert("quiet_hours".to_string(), quiet_hours);
        }
        if let Some(frequency_cap) = input.frequency_cap {
            payload.insert("frequency_cap".to_string(), Value::from(frequency_cap));
        }
        if let Some(policy) = input.policy {
            if !policy.is_object() && !policy.is_null() {
                return Err(invalid_state("policy must be an object or null"));
            }
            payload.insert("policy".to_string(), policy);
        }
        if payload.is_empty() {
            return Err(invalid_state(
                "subscription_policy.patch requires at least one field",
            ));
        }

        let policy_exists = self
            .cache()
            .list_subscription_policies()?
            .into_iter()
            .any(|policy| policy.id == input.subscription_policy_id);
        if !policy_exists {
            return Err(invalid_state(format!(
                "subscription policy {} is not cached",
                input.subscription_policy_id
            )));
        }

        self.queue_mutation_and_maybe_sync(
            "subscription_policy.patch",
            "subscription_policy",
            Some(input.subscription_policy_id),
            Value::Object(payload),
        )
    }

    pub fn disconnect_device(&self) -> Result<SyncStatusRead> {
        self.secret_store().clear()?;
        self.cache().disconnect()?;
        self.get_sync_status()
    }

    pub fn clear_local_cache(&self) -> Result<SyncStatusRead> {
        self.cache().reset_local_cache()?;
        self.get_sync_status()
    }

    pub fn sync_with<A: SyncBackendApi>(&self, api: &A) -> Result<SyncNowResponse> {
        let cache = self.cache();
        let state = cache.sync_state_record()?;
        if !state.connected {
            return Err(invalid_state("desktop is not connected"));
        }

        let sync_outcome = (|| -> Result<(PushOutcomeSummary, i64, i64, i64)> {
            cache.recover_inflight_mutations()?;

            let pending_mutations = cache.pending_outbox_batch()?;
            let push_summary = if pending_mutations.is_empty() {
                PushOutcomeSummary::default()
            } else {
                let client_mutation_ids = pending_mutations
                    .iter()
                    .map(|mutation| mutation.client_mutation_id.clone())
                    .collect::<Vec<_>>();
                cache.mark_mutations_sending(&client_mutation_ids)?;
                let response = api.push(&RemoteSyncPushRequest {
                    mutations: pending_mutations
                        .iter()
                        .map(|mutation| RemoteSyncMutationRequest {
                            client_mutation_id: mutation.client_mutation_id.clone(),
                            mutation_type: mutation.mutation_type.clone(),
                            resource_type: mutation.resource_type.clone(),
                            resource_id: mutation.resource_id.clone(),
                            payload: mutation.payload.clone(),
                        })
                        .collect(),
                })?;
                cache.apply_push_results(&response.results)?
            };

            let mut pages_fetched = 0_i64;
            let mut events_applied = 0_i64;
            let mut next_after_sequence = state.last_event_sequence;
            let mut final_sequence = state.last_event_sequence;

            loop {
                let page = api.feed(next_after_sequence, FEED_PAGE_LIMIT)?;
                if page.events.is_empty() {
                    break;
                }
                cache.apply_event_batch(&page.events)?;
                events_applied += page.events.len() as i64;
                pages_fetched += 1;
                final_sequence = page.next_after_sequence;
                next_after_sequence = page.next_after_sequence;
                if !page.has_more {
                    break;
                }
            }

            let acknowledged_sequence = if final_sequence > state.last_event_sequence {
                let ack = api.ack(final_sequence)?;
                cache.update_after_ack(ack.last_event_sequence, ack.last_synced_at.as_deref())?;
                ack.last_event_sequence
            } else {
                state.last_event_sequence
            };

            Ok((push_summary, pages_fetched, events_applied, acknowledged_sequence))
        })();

        let (push_summary, pages_fetched, events_applied, acknowledged_sequence) = match sync_outcome
        {
            Ok(result) => result,
            Err(error) => {
                let message = format!("{error:#}");
                let _ = cache.recover_inflight_mutations();
                let _ = cache.mark_sync_error(&message);
                return Err(error);
            }
        };

        cache.clear_sync_error()?;
        let outbox_stats = cache.outbox_stats()?;
        let token_present = self.secret_store().load_device_token()?.is_some();
        Ok(SyncNowResponse {
            sync_status: cache.sync_status(token_present)?,
            pushed_count: push_summary.pushed_count,
            applied_count: push_summary.applied_count,
            duplicate_count: push_summary.duplicate_count,
            failed_count: push_summary.failed_count,
            pages_fetched,
            events_applied,
            acknowledged_sequence,
            pending_mutation_count: outbox_stats.pending_count,
            failed_mutation_count: outbox_stats.failed_count,
            today_overview: cache.read_today_overview()?,
        })
    }

    fn queue_mutation_and_maybe_sync(
        &self,
        mutation_type: &str,
        resource_type: &str,
        resource_id: Option<String>,
        payload: Value,
    ) -> Result<WriteActionResultRead> {
        self.ensure_local_connection_ready()?;
        let mutation_id = Uuid::new_v4().to_string();
        let client_mutation_id = format!("desktop-{mutation_id}");
        let cache = self.cache();
        cache.enqueue_mutation(
            &mutation_id,
            &client_mutation_id,
            mutation_type,
            resource_type,
            resource_id.as_deref(),
            &payload,
        )?;

        let sync_attempt = self.try_sync_immediately();
        let mutation = cache.get_mutation(&client_mutation_id)?;
        let outbox_stats = cache.outbox_stats()?;
        let sync_status = self.get_sync_status()?;
        let (sync_attempted, sync_succeeded, sync_error) = match sync_attempt {
            Ok(Some(_)) => (true, true, None),
            Ok(None) => (false, false, None),
            Err(error) => (true, false, Some(error)),
        };

        Ok(WriteActionResultRead {
            mutation,
            sync_attempted,
            sync_succeeded,
            sync_error,
            sync_status,
            pending_mutation_count: outbox_stats.pending_count,
            failed_mutation_count: outbox_stats.failed_count,
        })
    }

    fn try_sync_immediately(&self) -> Result<Option<SyncNowResponse>, String> {
        match self.load_connection() {
            Ok((base_url, token)) => {
                let api = ReqwestSyncBackendApi::new(base_url, token).map_err(error_to_string)?;
                self.sync_with(&api).map(Some).map_err(error_to_string)
            }
            Err(_) => Ok(None),
        }
    }

    fn ensure_local_connection_ready(&self) -> Result<UserConnectionRead> {
        self.get_sync_status()?
            .current_user_summary
            .ok_or_else(|| invalid_state("desktop must be connected before queueing writes"))
    }

    fn load_connection(&self) -> Result<(String, String)> {
        let state = self.cache().sync_state_record()?;
        let base_url = state
            .base_url
            .ok_or_else(|| invalid_state("desktop base URL is not configured"))?;
        let token = self
            .secret_store()
            .load_device_token()?
            .ok_or_else(|| invalid_state("desktop device token is not configured"))?;
        Ok((base_url, token))
    }

    fn cache(&self) -> LocalCache {
        LocalCache::new(self.paths.cache_db_path.clone())
    }

    fn secret_store(&self) -> FileSecretStore {
        FileSecretStore::new(self.paths.secret_store_path.clone())
    }
}

fn normalize_base_url(value: &str) -> Result<String> {
    let trimmed = value.trim().trim_end_matches('/');
    if trimmed.is_empty() {
        return Err(invalid_state("backend base URL is required"));
    }
    Ok(trimmed.to_string())
}

fn non_empty(value: impl Into<String>) -> Option<String> {
    let value = value.into();
    let trimmed = value.trim();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed.to_string())
    }
}

fn value_or_null(value: String) -> Value {
    match non_empty(value) {
        Some(text) => Value::String(text),
        None => Value::Null,
    }
}

fn error_to_string(error: anyhow::Error) -> String {
    format!("{error:#}")
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, rc::Rc};

    use serde_json::json;
    use tempfile::tempdir;

    use super::{ConnectDeviceInput, DesktopPaths, DesktopService, ListPapersInput};
    use crate::models::{
        QueuePaperPatchInput, QueueProgressEventCreateInput, QueueSubscriptionPolicyPatchInput,
        RemoteSyncAck, RemoteSyncDevice, RemoteSyncEvent, RemoteSyncFeed, RemoteSyncMe,
        RemoteSyncMutationResult, RemoteSyncPushRequest, RemoteSyncPushResponse, RemoteSyncUser,
    };
    use crate::sync_client::SyncBackendApi;

    #[derive(Clone, Default)]
    struct FakeApi {
        sync_me_result: Rc<RefCell<Option<anyhow::Result<RemoteSyncMe>>>>,
        push_results: Rc<RefCell<Vec<anyhow::Result<RemoteSyncPushResponse>>>>,
        feed_results: Rc<RefCell<Vec<anyhow::Result<RemoteSyncFeed>>>>,
        ack_calls: Rc<RefCell<Vec<i64>>>,
        call_log: Rc<RefCell<Vec<String>>>,
        pushed_batches: Rc<RefCell<Vec<RemoteSyncPushRequest>>>,
    }

    impl SyncBackendApi for FakeApi {
        fn sync_me(&self) -> anyhow::Result<RemoteSyncMe> {
            self.call_log.borrow_mut().push("sync_me".to_string());
            self.sync_me_result
                .borrow_mut()
                .take()
                .unwrap_or_else(|| Err(anyhow::anyhow!("missing sync_me result")))
        }

        fn push(&self, payload: &RemoteSyncPushRequest) -> anyhow::Result<RemoteSyncPushResponse> {
            self.call_log.borrow_mut().push("push".to_string());
            self.pushed_batches.borrow_mut().push(payload.clone());
            if self.push_results.borrow().is_empty() {
                return Ok(RemoteSyncPushResponse { results: Vec::new() });
            }
            self.push_results.borrow_mut().remove(0)
        }

        fn feed(&self, after_sequence: i64, _limit: usize) -> anyhow::Result<RemoteSyncFeed> {
            self.call_log
                .borrow_mut()
                .push(format!("feed:{after_sequence}"));
            if self.feed_results.borrow().is_empty() {
                return Ok(RemoteSyncFeed {
                    events: Vec::new(),
                    next_after_sequence: after_sequence,
                    has_more: false,
                });
            }
            self.feed_results.borrow_mut().remove(0)
        }

        fn ack(&self, last_event_sequence: i64) -> anyhow::Result<RemoteSyncAck> {
            self.call_log.borrow_mut().push("ack".to_string());
            self.ack_calls.borrow_mut().push(last_event_sequence);
            Ok(RemoteSyncAck {
                last_event_sequence,
                last_synced_at: Some("2026-04-15T00:00:00Z".to_string()),
            })
        }
    }

    fn service() -> DesktopService {
        let dir = tempdir().unwrap();
        let root = dir.path().to_path_buf();
        std::mem::forget(dir);
        DesktopService::new(DesktopPaths {
            app_data_dir: root.clone(),
            cache_db_path: root.join("desktop.sqlite3"),
            secret_store_path: root.join("device-secret.json"),
        })
        .unwrap()
    }

    fn connect(service: &DesktopService, api: &FakeApi, feed_results: Vec<anyhow::Result<RemoteSyncFeed>>) {
        api.sync_me_result.replace(Some(Ok(RemoteSyncMe {
            device: RemoteSyncDevice {
                id: "device-1".to_string(),
                user_id: "user-1".to_string(),
                client_type: "desktop".to_string(),
                display_name: "Primary Desktop".to_string(),
                is_active: true,
                last_seen_at: None,
                created_at: "2026-04-15T00:00:00Z".to_string(),
                updated_at: "2026-04-15T00:00:00Z".to_string(),
                last_event_sequence: 0,
                last_synced_at: None,
            },
            user: RemoteSyncUser {
                id: "user-1".to_string(),
                name: "Desktop User".to_string(),
                email: Some("desktop@example.com".to_string()),
                field: Some("Materials".to_string()),
            },
        })));
        api.feed_results.replace(feed_results);
        service
            .connect_with(
                ConnectDeviceInput {
                    base_url: "http://localhost:8000".to_string(),
                    device_token: "good-token".to_string(),
                    device_display_name: Some("Primary Desktop".to_string()),
                },
                api,
            )
            .unwrap();
    }

    fn paper_event(stage: &str, sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-paper-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "paper_profile".to_string(),
            entity_id: "paper-1".to_string(),
            event_type: "updated".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": "paper-1",
                "user_id": "user-1",
                "title": "Desktop Paper",
                "type": "revision",
                "stage": stage,
                "venue": "JOM",
                "priority": 4,
                "next_action": "Prepare response",
                "blocker": null,
                "last_touch_at": "2026-04-15T00:00:00Z",
                "updated_at": "2026-04-15T00:00:00Z",
                "identifiers": {},
                "source_links": []
            }),
        }
    }

    fn policy_event(enabled: bool, frequency_cap: i64, sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-policy-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "subscription_policy".to_string(),
            entity_id: "policy-1".to_string(),
            event_type: "updated".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": "policy-1",
                "user_id": "user-1",
                "channel": "in_app",
                "enabled": enabled,
                "frequency": "daily",
                "quiet_hours": {"start": "22:00", "end": "07:00"},
                "frequency_cap": frequency_cap,
                "policy": {"stale_days": 10},
                "updated_at": "2026-04-15T00:00:00Z"
            }),
        }
    }

    fn progress_event(sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-progress-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "progress_event".to_string(),
            entity_id: format!("progress-{sequence}"),
            event_type: "created".to_string(),
            event_source: "sync_push".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": format!("progress-{sequence}"),
                "paper_id": "paper-1",
                "stage": "revision",
                "happened_at": "2026-04-15T00:00:00Z",
                "summary": "Submitted revision",
                "owner": "desktop",
                "evidence_links": []
            }),
        }
    }

    fn digest_event(sequence: i64) -> RemoteSyncEvent {
        RemoteSyncEvent {
            id: format!("evt-digest-{sequence}"),
            sequence,
            user_id: "user-1".to_string(),
            entity_type: "pulse_digest_issue".to_string(),
            entity_id: "digest-1".to_string(),
            event_type: "updated".to_string(),
            event_source: "worker".to_string(),
            occurred_at: "2026-04-15T00:00:00Z".to_string(),
            payload: serde_json::json!({
                "id": "digest-1",
                "user_id": "user-1",
                "issue_date": "2026-04-15",
                "status": "ready",
                "title": "Digest",
                "summary": "Summary",
                "highlight_count": 1,
                "selected_card_count": 1,
                "deep_link_path": "/mini/pulse-digests/user-1/2026-04-15",
                "highlights": [{
                    "sort_order": 1,
                    "pulse_card_id": "card-1",
                    "card_type": "signal_change",
                    "source_paper_id": "paper-1",
                    "title": "Signal update",
                    "summary": "Summary",
                    "why_now": "Why now"
                }],
                "items": [{
                    "sort_order": 1,
                    "pulse_card_id": "card-1",
                    "card_type": "signal_change",
                    "source_paper_id": "paper-1",
                    "title": "Signal update",
                    "summary": "Summary",
                    "why_now": "Why now"
                }],
                "updated_at": "2026-04-15T00:00:00Z"
            }),
        }
    }

    #[test]
    fn connect_device_rejects_invalid_token_path_with_mocked_backend() {
        let service = service();
        let api = FakeApi {
            sync_me_result: Rc::new(RefCell::new(Some(Err(anyhow::anyhow!(
                "sync authentication failed"
            ))))),
            ..FakeApi::default()
        };

        let result = service.connect_with(
            ConnectDeviceInput {
                base_url: "http://localhost:8000".to_string(),
                device_token: "bad-token".to_string(),
                device_display_name: Some("Primary Desktop".to_string()),
            },
            &api,
        );

        assert!(result.is_err());
    }

    #[test]
    fn queue_paper_patch_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_paper_patch(QueuePaperPatchInput {
                paper_id: "paper-1".to_string(),
                stage: Some("under_review".to_string()),
                venue: None,
                next_action: None,
                blocker: None,
                priority: None,
                last_touch_at: None,
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "paper.patch");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn queue_progress_event_create_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_progress_event_create(QueueProgressEventCreateInput {
                paper_id: "paper-1".to_string(),
                stage: "revision".to_string(),
                happened_at: "2026-04-15T00:00:00Z".to_string(),
                summary: "Queued from desktop".to_string(),
                owner: Some("desktop".to_string()),
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "progress_event.create");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn queue_subscription_policy_patch_creates_outbox_row() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![policy_event(true, 3, 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let result = service
            .queue_subscription_policy_patch(QueueSubscriptionPolicyPatchInput {
                subscription_policy_id: "policy-1".to_string(),
                enabled: Some(false),
                quiet_hours: None,
                frequency_cap: Some(5),
                policy: None,
            })
            .unwrap();

        assert_eq!(result.mutation.mutation_type, "subscription_policy.patch");
        assert_eq!(service.list_pending_mutations().unwrap().len(), 1);
    }

    #[test]
    fn sync_now_pushes_before_pulling_feed() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "applied".to_string(),
                    error_message: None,
                    resulting_event_sequence: Some(2),
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![paper_event("under_review", 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let response = service.sync_with(&api).unwrap();

        assert_eq!(response.pushed_count, 1);
        assert_eq!(
            api.call_log.borrow().last().map(String::as_str),
            Some("ack")
        );
        let log = api.call_log.borrow().clone();
        let push_idx = log.iter().rposition(|entry| entry == "push").unwrap();
        let feed_idx = log.iter().rposition(|entry| entry.starts_with("feed:1")).unwrap();
        let ack_idx = log.iter().rposition(|entry| entry == "ack").unwrap();
        assert!(push_idx < feed_idx);
        assert!(feed_idx < ack_idx);
    }

    #[test]
    fn duplicate_mutation_result_is_not_fatal() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "duplicate".to_string(),
                    error_message: None,
                    resulting_event_sequence: Some(1),
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();
        api.feed_results.replace(vec![]);

        let response = service.sync_with(&api).unwrap();

        assert_eq!(response.duplicate_count, 1);
        assert_eq!(response.failed_count, 0);
        assert!(service.list_pending_mutations().unwrap().is_empty());
    }

    #[test]
    fn failed_mutation_keeps_error_state_visible() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncPushResponse {
                results: vec![RemoteSyncMutationResult {
                    client_mutation_id: "desktop-seeded".to_string(),
                    status: "failed".to_string(),
                    error_message: Some("validation failed".to_string()),
                    resulting_event_sequence: None,
                }],
            })])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();

        let response = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();

        assert_eq!(response.failed_count, 1);
        assert_eq!(paper.last_mutation_error.as_deref(), Some("validation failed"));
        assert_eq!(service.get_sync_status().unwrap().failed_mutation_count, 1);
    }

    #[test]
    fn successful_paper_patch_roundtrip_updates_cache_after_sync_event_apply() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_paper_patch(QueuePaperPatchInput {
                paper_id: "paper-1".to_string(),
                stage: Some("under_review".to_string()),
                venue: None,
                next_action: None,
                blocker: None,
                priority: None,
                last_touch_at: None,
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![paper_event("under_review", 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let result = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();

        assert_eq!(result.applied_count, 1);
        assert_eq!(paper.stage, "under_review");
        assert_eq!(paper.pending_mutation_count, 0);
    }

    #[test]
    fn successful_progress_event_roundtrip_updates_progress_cache() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_progress_event_create(QueueProgressEventCreateInput {
                paper_id: "paper-1".to_string(),
                stage: "revision".to_string(),
                happened_at: "2026-04-15T00:00:00Z".to_string(),
                summary: "Queued from desktop".to_string(),
                owner: Some("desktop".to_string()),
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![progress_event(2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let _ = service.sync_with(&api).unwrap();
        let paper = service.get_paper_detail("paper-1").unwrap();
        assert_eq!(paper.progress_events.len(), 1);
    }

    #[test]
    fn successful_subscription_policy_roundtrip_updates_cache() {
        let service = service();
        let api = FakeApi {
            push_results: Rc::new(RefCell::new(vec![Err(anyhow::anyhow!("network down"))])),
            ..FakeApi::default()
        };
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![policy_event(true, 3, 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        let result = service
            .queue_subscription_policy_patch(QueueSubscriptionPolicyPatchInput {
                subscription_policy_id: "policy-1".to_string(),
                enabled: Some(false),
                quiet_hours: Some(json!({"start": "23:00", "end": "07:00"})),
                frequency_cap: Some(5),
                policy: None,
            })
            .unwrap();
        api.push_results.replace(vec![Ok(RemoteSyncPushResponse {
            results: vec![RemoteSyncMutationResult {
                client_mutation_id: result.mutation.client_mutation_id.clone(),
                status: "applied".to_string(),
                error_message: None,
                resulting_event_sequence: Some(2),
            }],
        })]);
        api.feed_results.replace(vec![Ok(RemoteSyncFeed {
            events: vec![policy_event(false, 5, 2)],
            next_after_sequence: 2,
            has_more: false,
        })]);

        let _ = service.sync_with(&api).unwrap();
        let policies = service.list_subscription_policies().unwrap();
        assert!(!policies[0].enabled);
        assert_eq!(policies[0].frequency_cap, 5);
    }

    #[test]
    fn clear_local_cache_resets_cache_and_outbox_state() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1), digest_event(2)],
                next_after_sequence: 2,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "seeded",
                "desktop-seeded",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "revision"}),
            )
            .unwrap();

        let status = service.clear_local_cache().unwrap();
        assert_eq!(status.last_event_sequence, 0);
        assert_eq!(status.pending_mutation_count, 0);
        assert!(service.list_papers(None).unwrap().is_empty());
        assert!(service.list_pending_mutations().unwrap().is_empty());
    }

    #[test]
    fn get_sync_status_includes_pending_and_failed_counts() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "queued",
                "desktop-queued",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        service
            .cache()
            .enqueue_mutation(
                "failed",
                "desktop-failed",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();
        service
            .cache()
            .apply_push_results(&[RemoteSyncMutationResult {
                client_mutation_id: "desktop-failed".to_string(),
                status: "failed".to_string(),
                error_message: Some("boom".to_string()),
                resulting_event_sequence: None,
            }])
            .unwrap();

        let status = service.get_sync_status().unwrap();
        assert_eq!(status.pending_mutation_count, 1);
        assert_eq!(status.failed_mutation_count, 1);
        assert_eq!(status.recent_outbox_errors, vec!["boom".to_string()]);
    }

    #[test]
    fn get_paper_detail_exposes_pending_mutation_state() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );
        service
            .cache()
            .enqueue_mutation(
                "queued",
                "desktop-queued",
                "paper.patch",
                "paper_profile",
                Some("paper-1"),
                &json!({"stage": "under_review"}),
            )
            .unwrap();

        let detail = service.get_paper_detail("paper-1").unwrap();
        assert_eq!(detail.pending_mutation_count, 1);
    }

    #[test]
    fn list_papers_keeps_stable_ordering_contract() {
        let service = service();
        let api = FakeApi::default();
        connect(
            &service,
            &api,
            vec![Ok(RemoteSyncFeed {
                events: vec![paper_event("revision", 1)],
                next_after_sequence: 1,
                has_more: false,
            })],
        );

        let papers = service
            .list_papers(Some(ListPapersInput {
                paper_type: Some("revision".to_string()),
                ..ListPapersInput::default()
            }))
            .unwrap();
        assert_eq!(papers.len(), 1);
    }
}
