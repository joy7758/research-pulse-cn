use std::path::PathBuf;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

use crate::error::ensure_parent_dir;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SecretEnvelope {
    device_token: Option<String>,
    updated_at: Option<String>,
}

#[derive(Debug, Clone)]
pub struct FileSecretStore {
    path: PathBuf,
}

impl FileSecretStore {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    pub fn load_device_token(&self) -> Result<Option<String>> {
        if !self.path.exists() {
            return Ok(None);
        }
        let raw = std::fs::read_to_string(&self.path)
            .with_context(|| format!("failed to read secret store {}", self.path.display()))?;
        let envelope: SecretEnvelope =
            serde_json::from_str(&raw).context("failed to decode secret store")?;
        Ok(envelope.device_token)
    }

    pub fn save_device_token(&self, token: &str) -> Result<()> {
        ensure_parent_dir(&self.path)?;
        let envelope = SecretEnvelope {
            device_token: Some(token.to_string()),
            updated_at: Some(timestamp_now()),
        };
        let raw = serde_json::to_string_pretty(&envelope)?;
        std::fs::write(&self.path, raw)
            .with_context(|| format!("failed to write secret store {}", self.path.display()))?;
        Ok(())
    }

    pub fn clear(&self) -> Result<()> {
        if self.path.exists() {
            std::fs::remove_file(&self.path)
                .with_context(|| format!("failed to remove secret store {}", self.path.display()))?;
        }
        Ok(())
    }
}

fn timestamp_now() -> String {
    chrono::Utc::now().to_rfc3339()
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use super::FileSecretStore;

    #[test]
    fn secret_store_round_trip_and_clear() {
        let dir = tempdir().unwrap();
        let store = FileSecretStore::new(dir.path().join("secret.json"));

        assert_eq!(store.load_device_token().unwrap(), None);

        store.save_device_token("device-token").unwrap();
        assert_eq!(
            store.load_device_token().unwrap(),
            Some("device-token".to_string())
        );

        store.clear().unwrap();
        assert_eq!(store.load_device_token().unwrap(), None);
    }
}
