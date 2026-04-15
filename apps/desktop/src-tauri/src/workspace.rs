use std::{
    fs::{self, OpenOptions},
    io::{BufReader, Read},
    path::{Path, PathBuf},
};

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde_json::json;
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::error::invalid_state;

pub const WORKSPACE_LAYOUT_VERSION: i64 = 1;
const WORKSPACE_ROOT_ROW_ID: &str = "workspace";
const WORKSPACE_METADATA_FILE: &str = "workspace.json";
const WORKSPACE_PAPERS_DIR: &str = "papers";
const WORKSPACE_ATTACHMENTS_DIR: &str = "attachments";
const WORKSPACE_NOTES_DIR: &str = "notes";
const WORKSPACE_EXPORTS_DIR: &str = "exports";

#[derive(Debug, Clone)]
pub struct WorkspaceRootRecord {
    pub id: String,
    pub root_path: Option<String>,
    pub status: String,
    pub layout_version: i64,
    pub last_validated_at: Option<String>,
    pub last_error: Option<String>,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone)]
pub struct WorkspaceValidation {
    pub root_path: Option<String>,
    pub status: String,
    pub last_error: Option<String>,
    pub last_validated_at: String,
}

#[derive(Debug, Clone)]
pub struct WorkspaceLayoutPaths {
    pub root_path: PathBuf,
    pub paper_rel_path: String,
    pub paper_abs_path: PathBuf,
    pub attachments_abs_path: PathBuf,
    pub notes_abs_path: PathBuf,
    pub exports_abs_path: PathBuf,
    pub metadata_abs_path: PathBuf,
}

#[derive(Debug, Clone)]
pub struct FileImportMetadata {
    pub source_path: String,
    pub original_file_name: String,
    pub file_extension: Option<String>,
    pub size_bytes: Option<i64>,
    pub mime_type: Option<String>,
    pub sha256: Option<String>,
}

#[derive(Debug, Clone)]
pub struct AttachmentImportPrepared {
    pub attachment_id: String,
    pub relative_path: String,
    pub absolute_path: String,
    pub stored_file_name: String,
    pub metadata: FileImportMetadata,
}

pub fn workspace_root_row_id() -> &'static str {
    WORKSPACE_ROOT_ROW_ID
}

pub fn attachment_kinds() -> &'static [&'static str] {
    &[
        "manuscript",
        "review",
        "response_letter",
        "figure",
        "dataset",
        "supplement",
        "note",
        "other",
    ]
}

pub fn validate_attachment_kind(kind: &str) -> Result<String> {
    let normalized = kind.trim().to_string();
    if attachment_kinds().contains(&normalized.as_str()) {
        Ok(normalized)
    } else {
        Err(invalid_state(format!(
            "attachment_kind must be one of: {}",
            attachment_kinds().join(", ")
        )))
    }
}

pub fn default_workspace_root_record() -> WorkspaceRootRecord {
    let now = timestamp_now();
    WorkspaceRootRecord {
        id: workspace_root_row_id().to_string(),
        root_path: None,
        status: "unconfigured".to_string(),
        layout_version: WORKSPACE_LAYOUT_VERSION,
        last_validated_at: None,
        last_error: None,
        created_at: now.clone(),
        updated_at: now,
    }
}

pub fn validate_workspace_root(root_path: Option<&str>) -> WorkspaceValidation {
    let validated_at = timestamp_now();
    let Some(raw_path) = root_path.map(str::trim).filter(|value| !value.is_empty()) else {
        return WorkspaceValidation {
            root_path: None,
            status: "unconfigured".to_string(),
            last_error: None,
            last_validated_at: validated_at,
        };
    };

    match canonicalize_existing_dir(raw_path)
        .and_then(|path| ensure_writable_dir(&path).map(|_| path))
    {
        Ok(path) => WorkspaceValidation {
            root_path: Some(path_to_string(&path)),
            status: "ready".to_string(),
            last_error: None,
            last_validated_at: validated_at,
        },
        Err(error) => {
            let status = match canonicalize_existing_dir(raw_path) {
                Ok(_) => "invalid",
                Err(_) => "missing",
            };
            WorkspaceValidation {
                root_path: Some(raw_path.to_string()),
                status: status.to_string(),
                last_error: Some(format!("{error:#}")),
                last_validated_at: validated_at,
            }
        }
    }
}

pub fn build_workspace_layout(root_path: &Path, paper_id: &str) -> WorkspaceLayoutPaths {
    let paper_rel_path = PathBuf::from(WORKSPACE_PAPERS_DIR).join(paper_id);
    let paper_abs_path = root_path.join(&paper_rel_path);
    WorkspaceLayoutPaths {
        root_path: root_path.to_path_buf(),
        paper_rel_path: path_to_string(&paper_rel_path),
        attachments_abs_path: paper_abs_path.join(WORKSPACE_ATTACHMENTS_DIR),
        notes_abs_path: paper_abs_path.join(WORKSPACE_NOTES_DIR),
        exports_abs_path: paper_abs_path.join(WORKSPACE_EXPORTS_DIR),
        metadata_abs_path: paper_abs_path.join(WORKSPACE_METADATA_FILE),
        paper_abs_path,
    }
}

pub fn ensure_paper_workspace_layout(
    root_path: &Path,
    paper_id: &str,
    paper_title: &str,
) -> Result<WorkspaceLayoutPaths> {
    let layout = build_workspace_layout(root_path, paper_id);
    fs::create_dir_all(&layout.attachments_abs_path).with_context(|| {
        format!(
            "failed to create attachments directory {}",
            layout.attachments_abs_path.display()
        )
    })?;
    fs::create_dir_all(&layout.notes_abs_path).with_context(|| {
        format!(
            "failed to create notes directory {}",
            layout.notes_abs_path.display()
        )
    })?;
    fs::create_dir_all(&layout.exports_abs_path).with_context(|| {
        format!(
            "failed to create exports directory {}",
            layout.exports_abs_path.display()
        )
    })?;
    write_workspace_metadata(&layout, paper_id, paper_title)?;
    Ok(layout)
}

pub fn collect_file_import_metadata(source_path: &str) -> Result<FileImportMetadata> {
    let canonical = canonicalize_existing_file(source_path)?;
    let metadata = fs::metadata(&canonical)
        .with_context(|| format!("failed to read file metadata {}", canonical.display()))?;
    let file_name = canonical
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| invalid_state("source file name is not valid unicode"))?
        .to_string();
    let file_extension = canonical
        .extension()
        .and_then(|value| value.to_str())
        .map(|value| value.to_ascii_lowercase());
    let mime_type = mime_guess::from_path(&canonical)
        .first_raw()
        .map(str::to_string);
    let sha256 = Some(compute_sha256(&canonical)?);
    let size_bytes = i64::try_from(metadata.len()).ok();

    Ok(FileImportMetadata {
        source_path: path_to_string(&canonical),
        original_file_name: file_name,
        file_extension,
        size_bytes,
        mime_type,
        sha256,
    })
}

pub fn prepare_attachment_import(
    layout: &WorkspaceLayoutPaths,
    metadata: &FileImportMetadata,
    imported_at: &str,
) -> Result<AttachmentImportPrepared> {
    let attachment_id = Uuid::new_v4().to_string();
    let stored_file_name = build_stored_file_name(metadata, imported_at, &attachment_id);
    let relative_path = PathBuf::from(&layout.paper_rel_path)
        .join(WORKSPACE_ATTACHMENTS_DIR)
        .join(&stored_file_name);
    let absolute_path = layout.root_path.join(&relative_path);
    Ok(AttachmentImportPrepared {
        attachment_id,
        relative_path: path_to_string(&relative_path),
        absolute_path: path_to_string(&absolute_path),
        stored_file_name,
        metadata: metadata.clone(),
    })
}

pub fn copy_managed_attachment(prepared: &AttachmentImportPrepared) -> Result<()> {
    let source_path = PathBuf::from(&prepared.metadata.source_path);
    let destination = PathBuf::from(&prepared.absolute_path);
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create directory {}", parent.display()))?;
    }
    fs::copy(&source_path, &destination).with_context(|| {
        format!(
            "failed to copy managed attachment {} -> {}",
            source_path.display(),
            destination.display()
        )
    })?;
    Ok(())
}

pub fn file_exists(path: Option<&str>) -> bool {
    path.map(PathBuf::from).is_some_and(|path| path.exists())
}

pub fn path_to_string(path: &Path) -> String {
    path.to_string_lossy().into_owned()
}

pub fn attachment_status_for_path(path: Option<&str>) -> String {
    if file_exists(path) {
        "ready".to_string()
    } else {
        "missing".to_string()
    }
}

pub fn paper_workspace_ready_for_path(path: Option<&str>) -> bool {
    path.map(PathBuf::from)
        .is_some_and(|path| path.is_dir() && path.exists())
}

pub fn timestamp_now() -> String {
    Utc::now().to_rfc3339()
}

pub fn workspace_root_rebind_path(root_path: Option<&str>, relative_path: &str) -> Option<String> {
    root_path
        .map(PathBuf::from)
        .map(|root| path_to_string(&root.join(relative_path)))
}

pub fn should_treat_as_duplicate(
    existing_sha256: Option<&str>,
    existing_size_bytes: Option<i64>,
    existing_original_file_name: &str,
    metadata: &FileImportMetadata,
) -> bool {
    if let (Some(existing), Some(incoming)) = (existing_sha256, metadata.sha256.as_deref()) {
        return existing == incoming;
    }

    existing_size_bytes == metadata.size_bytes
        && existing_original_file_name == metadata.original_file_name
}

fn write_workspace_metadata(
    layout: &WorkspaceLayoutPaths,
    paper_id: &str,
    paper_title: &str,
) -> Result<()> {
    let content = json!({
        "layout_version": WORKSPACE_LAYOUT_VERSION,
        "paper_id": paper_id,
        "paper_title": paper_title,
        "paper_rel_path": layout.paper_rel_path,
        "managed_copy_model": true,
        "notes_dir": WORKSPACE_NOTES_DIR,
        "exports_dir": WORKSPACE_EXPORTS_DIR,
        "attachments_dir": WORKSPACE_ATTACHMENTS_DIR,
        "generated_at": timestamp_now(),
    });
    fs::write(
        &layout.metadata_abs_path,
        serde_json::to_vec_pretty(&content)?,
    )
    .with_context(|| {
        format!(
            "failed to write workspace metadata {}",
            layout.metadata_abs_path.display()
        )
    })?;
    Ok(())
}

fn canonicalize_existing_dir(path: &str) -> Result<PathBuf> {
    let canonical =
        fs::canonicalize(path).with_context(|| format!("workspace root does not exist: {path}"))?;
    if !canonical.is_dir() {
        return Err(invalid_state(format!(
            "workspace root must be a directory: {}",
            canonical.display()
        )));
    }
    Ok(canonical)
}

fn canonicalize_existing_file(path: &str) -> Result<PathBuf> {
    let canonical =
        fs::canonicalize(path).with_context(|| format!("source file does not exist: {path}"))?;
    if !canonical.is_file() {
        return Err(invalid_state(format!(
            "source path must be a file: {}",
            canonical.display()
        )));
    }
    Ok(canonical)
}

fn ensure_writable_dir(path: &Path) -> Result<()> {
    let probe_name = format!(".research-pulse-write-check-{}", Uuid::new_v4().simple());
    let probe_path = path.join(probe_name);
    OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&probe_path)
        .with_context(|| format!("workspace root is not writable: {}", path.display()))?;
    fs::remove_file(&probe_path).with_context(|| {
        format!(
            "failed to remove workspace root probe file {}",
            probe_path.display()
        )
    })?;
    Ok(())
}

fn compute_sha256(path: &Path) -> Result<String> {
    let file = fs::File::open(path)
        .with_context(|| format!("failed to open {} for hashing", path.display()))?;
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 8192];
    loop {
        let bytes_read = reader
            .read(&mut buffer)
            .with_context(|| format!("failed to read {}", path.display()))?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }
    let digest = hasher.finalize();
    Ok(digest
        .iter()
        .map(|value| format!("{value:02x}"))
        .collect::<String>())
}

fn build_stored_file_name(
    metadata: &FileImportMetadata,
    imported_at: &str,
    attachment_id: &str,
) -> String {
    let timestamp = DateTime::parse_from_rfc3339(imported_at)
        .map(|value| {
            value
                .with_timezone(&Utc)
                .format("%Y%m%dT%H%M%SZ")
                .to_string()
        })
        .unwrap_or_else(|_| Utc::now().format("%Y%m%dT%H%M%SZ").to_string());
    let hash_prefix = metadata
        .sha256
        .as_deref()
        .map(|value| value.chars().take(8).collect::<String>())
        .unwrap_or_else(|| attachment_id.chars().take(8).collect::<String>());
    let base_name = sanitize_stem(
        Path::new(&metadata.original_file_name)
            .file_stem()
            .and_then(|value| value.to_str())
            .unwrap_or("attachment"),
    );
    match metadata.file_extension.as_deref() {
        Some(extension) if !extension.is_empty() => {
            format!("{timestamp}-{hash_prefix}-{base_name}.{extension}")
        }
        _ => format!("{timestamp}-{hash_prefix}-{base_name}"),
    }
}

fn sanitize_stem(value: &str) -> String {
    let mut output = String::with_capacity(value.len());
    let mut last_was_separator = false;
    for character in value.chars() {
        let safe = if character.is_ascii_alphanumeric() {
            last_was_separator = false;
            character
        } else if matches!(character, '.' | '-' | '_') {
            last_was_separator = false;
            character
        } else if last_was_separator {
            continue;
        } else {
            last_was_separator = true;
            '_'
        };
        output.push(safe);
    }
    let cleaned = output.trim_matches('_');
    if cleaned.is_empty() {
        "attachment".to_string()
    } else {
        cleaned.chars().take(80).collect()
    }
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use super::{
        attachment_status_for_path, build_workspace_layout, collect_file_import_metadata,
        ensure_paper_workspace_layout, prepare_attachment_import, validate_attachment_kind,
        validate_workspace_root, WORKSPACE_LAYOUT_VERSION,
    };

    #[test]
    fn validates_attachment_kind() {
        assert_eq!(
            validate_attachment_kind("manuscript").unwrap(),
            "manuscript"
        );
        assert!(validate_attachment_kind("weird").is_err());
    }

    #[test]
    fn workspace_validation_reports_missing_root() {
        let result = validate_workspace_root(Some("/tmp/not-real-research-pulse-workspace"));
        assert_eq!(result.status, "missing");
    }

    #[test]
    fn ensure_workspace_layout_creates_expected_structure() {
        let dir = tempdir().unwrap();
        let layout = ensure_paper_workspace_layout(dir.path(), "paper-1", "Paper One").unwrap();
        assert!(layout.paper_abs_path.exists());
        assert!(layout.attachments_abs_path.exists());
        assert!(layout.notes_abs_path.exists());
        assert!(layout.exports_abs_path.exists());
        assert!(layout.metadata_abs_path.exists());
    }

    #[test]
    fn managed_import_preparation_generates_copy_path() {
        let dir = tempdir().unwrap();
        let source = dir.path().join("draft.pdf");
        std::fs::write(&source, b"hello").unwrap();
        let layout = build_workspace_layout(dir.path(), "paper-1");
        std::fs::create_dir_all(&layout.attachments_abs_path).unwrap();
        let metadata = collect_file_import_metadata(source.to_string_lossy().as_ref()).unwrap();
        let prepared =
            prepare_attachment_import(&layout, &metadata, "2026-04-15T00:00:00Z").unwrap();

        assert!(prepared
            .relative_path
            .contains("papers/paper-1/attachments/"));
        assert!(prepared.stored_file_name.ends_with(".pdf"));
        assert_eq!(
            attachment_status_for_path(Some(&prepared.absolute_path)),
            "missing"
        );
        assert_eq!(WORKSPACE_LAYOUT_VERSION, 1);
    }
}
