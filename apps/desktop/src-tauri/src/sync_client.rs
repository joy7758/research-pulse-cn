use anyhow::{Context, Result};
use reqwest::blocking::{Client, Response};
use reqwest::StatusCode;
use serde_json::json;

use crate::models::{
    RemoteSyncAck, RemoteSyncFeed, RemoteSyncMe, RemoteSyncPushRequest, RemoteSyncPushResponse,
};

pub trait SyncBackendApi {
    fn sync_me(&self) -> Result<RemoteSyncMe>;
    fn push(&self, payload: &RemoteSyncPushRequest) -> Result<RemoteSyncPushResponse>;
    fn feed(&self, after_sequence: i64, limit: usize) -> Result<RemoteSyncFeed>;
    fn ack(&self, last_event_sequence: i64) -> Result<RemoteSyncAck>;
}

#[derive(Debug, Clone)]
pub struct ReqwestSyncBackendApi {
    base_url: String,
    token: String,
    client: Client,
}

impl ReqwestSyncBackendApi {
    pub fn new(base_url: String, token: String) -> Result<Self> {
        let client = Client::builder()
            .user_agent("research-pulse-desktop/0.1")
            .build()
            .context("failed to build desktop sync HTTP client")?;
        Ok(Self {
            base_url: base_url.trim_end_matches('/').to_string(),
            token,
            client,
        })
    }

    fn get(&self, path: &str, query: &[(&str, String)]) -> Result<Response> {
        let response = self
            .client
            .get(format!("{}{}", self.base_url, path))
            .bearer_auth(&self.token)
            .query(query)
            .send()
            .with_context(|| format!("request to {}{} failed", self.base_url, path))?;
        ensure_success(response)
    }

    fn post_json(&self, path: &str, body: serde_json::Value) -> Result<Response> {
        let response = self
            .client
            .post(format!("{}{}", self.base_url, path))
            .bearer_auth(&self.token)
            .json(&body)
            .send()
            .with_context(|| format!("request to {}{} failed", self.base_url, path))?;
        ensure_success(response)
    }
}

impl SyncBackendApi for ReqwestSyncBackendApi {
    fn sync_me(&self) -> Result<RemoteSyncMe> {
        Ok(self
            .get("/sync/me", &[])?
            .json::<RemoteSyncMe>()
            .context("failed to decode /sync/me response")?)
    }

    fn push(&self, payload: &RemoteSyncPushRequest) -> Result<RemoteSyncPushResponse> {
        Ok(self
            .post_json(
                "/sync/push",
                serde_json::to_value(payload).context("failed to encode /sync/push body")?,
            )?
            .json::<RemoteSyncPushResponse>()
            .context("failed to decode /sync/push response")?)
    }

    fn feed(&self, after_sequence: i64, limit: usize) -> Result<RemoteSyncFeed> {
        Ok(self
            .get(
                "/sync/feed",
                &[
                    ("after_sequence", after_sequence.to_string()),
                    ("limit", limit.to_string()),
                ],
            )?
            .json::<RemoteSyncFeed>()
            .context("failed to decode /sync/feed response")?)
    }

    fn ack(&self, last_event_sequence: i64) -> Result<RemoteSyncAck> {
        Ok(self
            .post_json(
                "/sync/ack",
                json!({ "last_event_sequence": last_event_sequence }),
            )?
            .json::<RemoteSyncAck>()
            .context("failed to decode /sync/ack response")?)
    }
}

fn ensure_success(response: Response) -> Result<Response> {
    let status = response.status();
    if status.is_success() {
        return Ok(response);
    }
    let body = response.text().unwrap_or_default();
    let message = match status {
        StatusCode::UNAUTHORIZED => "sync authentication failed".to_string(),
        StatusCode::FORBIDDEN => "sync authorization failed".to_string(),
        _ => format!("sync request failed with status {status}: {body}"),
    };
    Err(anyhow::anyhow!(message))
}
