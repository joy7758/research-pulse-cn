use std::path::PathBuf;

use anyhow::{Context, Result};

pub fn invalid_state(message: impl Into<String>) -> anyhow::Error {
    anyhow::anyhow!(message.into())
}

pub fn ensure_parent_dir(path: &PathBuf) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("failed to create directory {}", parent.display()))?;
    }
    Ok(())
}
