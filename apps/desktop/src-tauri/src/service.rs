use std::path::PathBuf;

use anyhow::{Context, Result};

use crate::cache::LocalCache;
use crate::error::invalid_state;
use crate::models::{
    AppBootstrapRead, ConnectDeviceInput, ConnectDeviceResponse, ListPapersInput, PaperDetailRead,
    PaperListItemRead, SyncNowResponse, SyncStatusRead, TodayOverviewRead,
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
        let mut state = cache.sync_state_record()?;
        if !state.connected {
            return Err(invalid_state("desktop is not connected"));
        }

        let sync_outcome = (|| -> Result<(i64, i64, i64)> {
            let mut pages_fetched = 0_i64;
            let mut events_applied = 0_i64;
            let mut acknowledged_sequence = state.last_event_sequence;

            loop {
                let page = api.feed(acknowledged_sequence, FEED_PAGE_LIMIT)?;
                if page.events.is_empty() {
                    break;
                }
                cache.apply_event_batch(&page.events)?;
                events_applied += page.events.len() as i64;
                pages_fetched += 1;
                let ack = api.ack(page.next_after_sequence)?;
                cache.update_after_ack(ack.last_event_sequence, ack.last_synced_at.as_deref())?;
                acknowledged_sequence = ack.last_event_sequence;
                if !page.has_more {
                    break;
                }
            }
            Ok((pages_fetched, events_applied, acknowledged_sequence))
        })();

        let (pages_fetched, events_applied, _acknowledged_sequence) = match sync_outcome {
            Ok(result) => result,
            Err(error) => {
                let message = format!("{error:#}");
                let _ = cache.mark_sync_error(&message);
                return Err(error);
            }
        };

        cache.clear_sync_error()?;
        state = cache.sync_state_record()?;
        let token_present = self.secret_store().load_device_token()?.is_some();
        Ok(SyncNowResponse {
            sync_status: self.cache().sync_status(token_present)?,
            pages_fetched,
            events_applied,
            acknowledged_sequence: state.last_event_sequence,
            today_overview: cache.read_today_overview()?,
        })
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

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, rc::Rc};

    use tempfile::tempdir;

    use super::{ConnectDeviceInput, DesktopPaths, DesktopService};
    use crate::models::{RemoteSyncAck, RemoteSyncDevice, RemoteSyncEvent, RemoteSyncFeed, RemoteSyncMe, RemoteSyncUser};
    use crate::sync_client::SyncBackendApi;

    #[derive(Clone, Default)]
    struct FakeApi {
        sync_me_result: Rc<RefCell<Option<anyhow::Result<RemoteSyncMe>>>>,
        feed_results: Rc<RefCell<Vec<anyhow::Result<RemoteSyncFeed>>>>,
        ack_calls: Rc<RefCell<Vec<i64>>>,
    }

    impl SyncBackendApi for FakeApi {
        fn sync_me(&self) -> anyhow::Result<RemoteSyncMe> {
            self.sync_me_result
                .borrow_mut()
                .take()
                .unwrap_or_else(|| Err(anyhow::anyhow!("missing sync_me result")))
        }

        fn feed(&self, _after_sequence: i64, _limit: usize) -> anyhow::Result<RemoteSyncFeed> {
            if self.feed_results.borrow().is_empty() {
                return Ok(RemoteSyncFeed {
                    events: Vec::new(),
                    next_after_sequence: 0,
                    has_more: false,
                });
            }
            self.feed_results.borrow_mut().remove(0)
        }

        fn ack(&self, last_event_sequence: i64) -> anyhow::Result<RemoteSyncAck> {
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
    fn repeated_sync_only_acks_after_successful_apply() {
        let service = service();
        let api = FakeApi {
            sync_me_result: Rc::new(RefCell::new(Some(Ok(RemoteSyncMe {
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
            })))),
            feed_results: Rc::new(RefCell::new(vec![
                Ok(RemoteSyncFeed {
                    events: vec![RemoteSyncEvent {
                        id: "evt-1".to_string(),
                        sequence: 1,
                        user_id: "user-1".to_string(),
                        entity_type: "paper_profile".to_string(),
                        entity_id: "paper-1".to_string(),
                        event_type: "created".to_string(),
                        event_source: "api".to_string(),
                        occurred_at: "2026-04-15T00:00:00Z".to_string(),
                        payload: serde_json::json!({
                            "id": "paper-1",
                            "user_id": "user-1",
                            "title": "Desktop Paper",
                            "type": "published",
                            "stage": "published",
                            "priority": 4,
                            "identifiers": {},
                            "source_links": []
                        }),
                    }],
                    next_after_sequence: 1,
                    has_more: false,
                }),
            ])),
            ..FakeApi::default()
        };

        let connected = service
            .connect_with(
                ConnectDeviceInput {
                    base_url: "http://localhost:8000".to_string(),
                    device_token: "good-token".to_string(),
                    device_display_name: Some("Primary Desktop".to_string()),
                },
                &api,
            )
            .unwrap();

        assert!(connected.sync_status.connected);
        assert_eq!(*api.ack_calls.borrow(), vec![1]);
    }

    #[test]
    fn clear_local_cache_resets_status() {
        let service = service();
        let api = FakeApi {
            sync_me_result: Rc::new(RefCell::new(Some(Ok(RemoteSyncMe {
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
            })))),
            ..FakeApi::default()
        };
        service
            .connect_with(
                ConnectDeviceInput {
                    base_url: "http://localhost:8000".to_string(),
                    device_token: "good-token".to_string(),
                    device_display_name: Some("Primary Desktop".to_string()),
                },
                &api,
            )
            .unwrap();

        let status = service.clear_local_cache().unwrap();
        assert_eq!(status.last_event_sequence, 0);
        assert_eq!(service.list_papers(None).unwrap().len(), 0);
    }

    #[test]
    fn get_paper_detail_returns_derived_progress_percentage() {
        let service = service();
        let api = FakeApi {
            sync_me_result: Rc::new(RefCell::new(Some(Ok(RemoteSyncMe {
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
            })))),
            feed_results: Rc::new(RefCell::new(vec![Ok(RemoteSyncFeed {
                events: vec![RemoteSyncEvent {
                    id: "evt-1".to_string(),
                    sequence: 1,
                    user_id: "user-1".to_string(),
                    entity_type: "paper_profile".to_string(),
                    entity_id: "paper-1".to_string(),
                    event_type: "created".to_string(),
                    event_source: "api".to_string(),
                    occurred_at: "2026-04-15T00:00:00Z".to_string(),
                    payload: serde_json::json!({
                        "id": "paper-1",
                        "user_id": "user-1",
                        "title": "Desktop Paper",
                        "type": "revision",
                        "stage": "revision",
                        "priority": 4,
                        "identifiers": {},
                        "source_links": []
                    }),
                }],
                next_after_sequence: 1,
                has_more: false,
            })])),
            ..FakeApi::default()
        };
        service
            .connect_with(
                ConnectDeviceInput {
                    base_url: "http://localhost:8000".to_string(),
                    device_token: "good-token".to_string(),
                    device_display_name: Some("Primary Desktop".to_string()),
                },
                &api,
            )
            .unwrap();

        let detail = service.get_paper_detail("paper-1").unwrap();
        assert_eq!(detail.progress_percentage, 80);
    }
}
