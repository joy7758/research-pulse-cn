use std::{
    fs,
    io::{BufReader, Read},
    path::{Path, PathBuf},
};

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use sha2::{Digest, Sha256};

use crate::{
    error::invalid_state,
    models::NoteTemplateRead,
    workspace::{path_to_string, WorkspaceLayoutPaths},
};

#[derive(Debug, Clone)]
pub struct NoteTemplateContext {
    pub paper_id: String,
    pub paper_title: String,
    pub stage: String,
    pub venue: Option<String>,
    pub next_action: Option<String>,
    pub blocker: Option<String>,
}

#[derive(Debug, Clone)]
pub struct PreparedNoteFile {
    pub note_id: String,
    pub title: String,
    pub file_name: String,
    pub relative_path: String,
    pub absolute_path: String,
    pub content: String,
    pub template_kind: String,
    pub source_mode: String,
    pub created_at: String,
}

#[derive(Debug, Clone)]
pub struct NoteFileStats {
    pub size_bytes: Option<i64>,
    pub sha256: Option<String>,
}

#[derive(Debug, Clone)]
struct NoteTemplateDefinition {
    kind: &'static str,
    title: &'static str,
    description: &'static str,
    default_file_name_pattern: &'static str,
}

const NOTE_TEMPLATE_DEFINITIONS: [NoteTemplateDefinition; 6] = [
    NoteTemplateDefinition {
        kind: "blank_note",
        title: "Blank Note",
        description: "Create an empty markdown note for ad-hoc local thinking.",
        default_file_name_pattern: "blank-note-{timestamp}.md",
    },
    NoteTemplateDefinition {
        kind: "research_note",
        title: "Research Note",
        description: "Capture paper context, key questions, and follow-up reading notes.",
        default_file_name_pattern: "research-note-{timestamp}.md",
    },
    NoteTemplateDefinition {
        kind: "revision_plan",
        title: "Revision Plan",
        description: "Track revision goals, blockers, and completion steps.",
        default_file_name_pattern: "revision-plan-{timestamp}.md",
    },
    NoteTemplateDefinition {
        kind: "response_letter",
        title: "Response Letter Draft",
        description: "Draft a local response letter structure before editing the final response.",
        default_file_name_pattern: "response-letter-{timestamp}.md",
    },
    NoteTemplateDefinition {
        kind: "reviewer_matrix",
        title: "Reviewer Matrix",
        description: "Map reviewer comments to actions, owners, and response status.",
        default_file_name_pattern: "reviewer-matrix-{timestamp}.md",
    },
    NoteTemplateDefinition {
        kind: "submission_checklist",
        title: "Submission Checklist",
        description: "Track local submission readiness tasks for the current paper stage.",
        default_file_name_pattern: "submission-checklist-{timestamp}.md",
    },
];

pub fn list_note_templates() -> Vec<NoteTemplateRead> {
    NOTE_TEMPLATE_DEFINITIONS
        .iter()
        .map(|template| NoteTemplateRead {
            kind: template.kind.to_string(),
            title: template.title.to_string(),
            description: template.description.to_string(),
            default_file_name_pattern: template.default_file_name_pattern.to_string(),
        })
        .collect()
}

pub fn validate_template_kind(kind: &str) -> Result<String> {
    let normalized = kind.trim().to_string();
    if NOTE_TEMPLATE_DEFINITIONS
        .iter()
        .any(|template| template.kind == normalized)
    {
        Ok(normalized)
    } else {
        Err(invalid_state(format!(
            "template_kind must be one of: {}",
            NOTE_TEMPLATE_DEFINITIONS
                .iter()
                .map(|template| template.kind)
                .collect::<Vec<_>>()
                .join(", ")
        )))
    }
}

pub fn prepare_template_note(
    layout: &WorkspaceLayoutPaths,
    template_kind: &str,
    context: &NoteTemplateContext,
    note_id: &str,
    created_at: &str,
) -> Result<PreparedNoteFile> {
    let kind = validate_template_kind(template_kind)?;
    let title = template_title(&kind).to_string();
    let file_name = build_note_file_name(&title, created_at, note_id);
    let relative_path = build_note_relative_path(layout, &file_name);
    let absolute_path = layout.notes_abs_path.join(&file_name);
    let content = render_note_template(&kind, context)?;
    Ok(PreparedNoteFile {
        note_id: note_id.to_string(),
        title,
        file_name,
        relative_path,
        absolute_path: path_to_string(&absolute_path),
        content,
        template_kind: kind,
        source_mode: "template".to_string(),
        created_at: created_at.to_string(),
    })
}

pub fn prepare_blank_note(
    layout: &WorkspaceLayoutPaths,
    title: Option<&str>,
    context: &NoteTemplateContext,
    note_id: &str,
    created_at: &str,
) -> Result<PreparedNoteFile> {
    let note_title = title
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .unwrap_or("Blank Note")
        .to_string();
    let file_name = build_note_file_name(&note_title, created_at, note_id);
    let relative_path = build_note_relative_path(layout, &file_name);
    let absolute_path = layout.notes_abs_path.join(&file_name);
    let content = render_blank_note(context);
    Ok(PreparedNoteFile {
        note_id: note_id.to_string(),
        title: note_title,
        file_name,
        relative_path,
        absolute_path: path_to_string(&absolute_path),
        content,
        template_kind: "blank_note".to_string(),
        source_mode: "blank".to_string(),
        created_at: created_at.to_string(),
    })
}

pub fn prepare_generated_note(
    layout: &WorkspaceLayoutPaths,
    template_kind: &str,
    title: &str,
    content: &str,
    note_id: &str,
    created_at: &str,
) -> Result<PreparedNoteFile> {
    let file_name = build_note_file_name(title, created_at, note_id);
    let relative_path = build_note_relative_path(layout, &file_name);
    let absolute_path = layout.notes_abs_path.join(&file_name);
    Ok(PreparedNoteFile {
        note_id: note_id.to_string(),
        title: title.trim().to_string(),
        file_name,
        relative_path,
        absolute_path: path_to_string(&absolute_path),
        content: content.to_string(),
        template_kind: template_kind.trim().to_string(),
        source_mode: "generated".to_string(),
        created_at: created_at.to_string(),
    })
}

pub fn write_note_file(path: &str, content: &str) -> Result<NoteFileStats> {
    let target = PathBuf::from(path);
    if let Some(parent) = target.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create note directory {}", parent.display()))?;
    }
    fs::write(&target, content.as_bytes())
        .with_context(|| format!("failed to write note file {}", target.display()))?;
    read_note_file_stats(&target)
}

pub fn read_note_file(path: &str) -> Result<String> {
    let target = PathBuf::from(path);
    fs::read_to_string(&target)
        .with_context(|| format!("failed to read note file {}", target.display()))
}

pub fn read_note_file_stats(path: &Path) -> Result<NoteFileStats> {
    let metadata = fs::metadata(path)
        .with_context(|| format!("failed to read note metadata {}", path.display()))?;
    Ok(NoteFileStats {
        size_bytes: i64::try_from(metadata.len()).ok(),
        sha256: Some(compute_sha256(path)?),
    })
}

pub fn note_status_for_path(path: Option<&str>) -> String {
    if path.map(PathBuf::from).is_some_and(|value| value.exists()) {
        "ready".to_string()
    } else {
        "missing".to_string()
    }
}

fn template_title(template_kind: &str) -> &'static str {
    NOTE_TEMPLATE_DEFINITIONS
        .iter()
        .find(|template| template.kind == template_kind)
        .map(|template| template.title)
        .unwrap_or("Note")
}

fn render_note_template(template_kind: &str, context: &NoteTemplateContext) -> Result<String> {
    let paper_meta = render_paper_context(context);
    let body = match template_kind {
        "blank_note" => render_blank_note(context),
        "research_note" => format!(
            "# Research Note\n\n{paper_meta}\n\n## Core Question\n- \n\n## What Changed\n- \n\n## Evidence To Revisit\n- \n\n## Follow-Up Reading\n- \n\n## Decisions\n- \n"
        ),
        "revision_plan" => format!(
            "# Revision Plan\n\n{paper_meta}\n\n## Revision Goal\n- \n\n## Required Changes\n- \n\n## Blocking Issues\n- {}\n\n## Next Submission Steps\n- {}\n",
            context.blocker.as_deref().unwrap_or("-"),
            context.next_action.as_deref().unwrap_or("-")
        ),
        "response_letter" => format!(
            "# Response Letter Draft\n\n{paper_meta}\n\n## Cover Summary\n- \n\n## Major Changes\n- \n\n## Point-By-Point Responses\n\n### Reviewer 1\n- Comment:\n- Response:\n\n### Reviewer 2\n- Comment:\n- Response:\n"
        ),
        "reviewer_matrix" => format!(
            "# Reviewer Matrix\n\n{paper_meta}\n\n| Reviewer | Comment | Action | Owner | Status |\n| --- | --- | --- | --- | --- |\n|  |  |  |  |  |\n"
        ),
        "submission_checklist" => format!(
            "# Submission Checklist\n\n{paper_meta}\n\n## Files\n- [ ] Manuscript\n- [ ] Figures\n- [ ] Supplement\n\n## Metadata\n- [ ] Venue confirmed\n- [ ] Author list confirmed\n- [ ] Cover letter ready\n\n## Final Checks\n- [ ] References checked\n- [ ] Response package checked\n- [ ] Submission portal ready\n"
        ),
        _ => return Err(invalid_state(format!("unsupported template kind {template_kind}"))),
    };
    Ok(body)
}

fn render_blank_note(context: &NoteTemplateContext) -> String {
    format!(
        "# Note\n\n{}\n\n## Notes\n- \n",
        render_paper_context(context)
    )
}

fn render_paper_context(context: &NoteTemplateContext) -> String {
    let venue = context.venue.as_deref().unwrap_or("-");
    let next_action = context.next_action.as_deref().unwrap_or("-");
    let blocker = context.blocker.as_deref().unwrap_or("-");
    format!(
        "- Paper: {}\n- Paper ID: {}\n- Stage: {}\n- Venue: {}\n- Next Action: {}\n- Blocker: {}",
        context.paper_title, context.paper_id, context.stage, venue, next_action, blocker
    )
}

fn build_note_relative_path(layout: &WorkspaceLayoutPaths, file_name: &str) -> String {
    path_to_string(&PathBuf::from(&layout.paper_rel_path).join("notes").join(file_name))
}

fn build_note_file_name(title: &str, created_at: &str, note_id: &str) -> String {
    let timestamp = DateTime::parse_from_rfc3339(created_at)
        .map(|value| value.with_timezone(&Utc).format("%Y%m%dT%H%M%SZ").to_string())
        .unwrap_or_else(|_| Utc::now().format("%Y%m%dT%H%M%SZ").to_string());
    let id_prefix = note_id.chars().take(8).collect::<String>();
    let stem = sanitize_note_stem(title);
    format!("{timestamp}-{id_prefix}-{stem}.md")
}

fn sanitize_note_stem(value: &str) -> String {
    let mut output = String::with_capacity(value.len());
    let mut last_was_separator = false;
    for character in value.chars() {
        let safe = if character.is_ascii_alphanumeric() {
            last_was_separator = false;
            character.to_ascii_lowercase()
        } else if matches!(character, '.' | '-' | '_') {
            last_was_separator = false;
            character
        } else if last_was_separator {
            continue;
        } else {
            last_was_separator = true;
            '-'
        };
        output.push(safe);
    }
    let cleaned = output.trim_matches('-');
    if cleaned.is_empty() {
        "note".to_string()
    } else {
        cleaned.chars().take(80).collect()
    }
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

#[cfg(test)]
mod tests {
    use tempfile::tempdir;
    use uuid::Uuid;

    use super::{
        list_note_templates, note_status_for_path, prepare_blank_note, prepare_generated_note,
        prepare_template_note, read_note_file, render_note_template, validate_template_kind,
        NoteTemplateContext,
    };
    use crate::workspace::build_workspace_layout;

    fn context() -> NoteTemplateContext {
        NoteTemplateContext {
            paper_id: "paper-1".to_string(),
            paper_title: "Interesting Paper".to_string(),
            stage: "revision".to_string(),
            venue: Some("JOM".to_string()),
            next_action: Some("Prepare response".to_string()),
            blocker: None,
        }
    }

    #[test]
    fn lists_all_built_in_templates() {
        let templates = list_note_templates();
        assert_eq!(templates.len(), 6);
        assert!(templates.iter().any(|template| template.kind == "response_letter"));
    }

    #[test]
    fn validates_template_kind_membership() {
        assert_eq!(validate_template_kind("research_note").unwrap(), "research_note");
        assert!(validate_template_kind("not-real").is_err());
    }

    #[test]
    fn prepares_template_note_under_notes_directory() {
        let dir = tempdir().unwrap();
        let layout = build_workspace_layout(dir.path(), "paper-1");
        std::fs::create_dir_all(&layout.notes_abs_path).unwrap();
        let prepared = prepare_template_note(
            &layout,
            "revision_plan",
            &context(),
            &Uuid::new_v4().to_string(),
            "2026-04-15T00:00:00Z",
        )
        .unwrap();

        assert!(prepared.relative_path.contains("papers/paper-1/notes/"));
        assert!(prepared.file_name.ends_with(".md"));
        assert!(prepared.content.contains("# Revision Plan"));
    }

    #[test]
    fn blank_note_is_marked_missing_before_write() {
        let dir = tempdir().unwrap();
        let layout = build_workspace_layout(dir.path(), "paper-1");
        std::fs::create_dir_all(&layout.notes_abs_path).unwrap();
        let prepared = prepare_blank_note(
            &layout,
            Some("Working Draft"),
            &context(),
            &Uuid::new_v4().to_string(),
            "2026-04-15T00:00:00Z",
        )
        .unwrap();

        assert_eq!(note_status_for_path(Some(&prepared.absolute_path)), "missing");
    }

    #[test]
    fn template_content_uses_paper_context() {
        let rendered = render_note_template("research_note", &context()).unwrap();
        assert!(rendered.contains("Interesting Paper"));
        assert!(rendered.contains("Prepare response"));
    }

    #[test]
    fn read_note_file_loads_written_content() {
        let dir = tempdir().unwrap();
        let note_path = dir.path().join("note.md");
        std::fs::write(&note_path, b"# Note\n").unwrap();
        assert_eq!(read_note_file(note_path.to_string_lossy().as_ref()).unwrap(), "# Note\n");
    }

    #[test]
    fn prepare_generated_note_marks_note_as_generated() {
        let dir = tempdir().unwrap();
        let layout = build_workspace_layout(dir.path(), "paper-1");
        std::fs::create_dir_all(&layout.notes_abs_path).unwrap();
        let prepared = prepare_generated_note(
            &layout,
            "reviewer_matrix",
            "Reviewer Matrix - Round 1",
            "# Reviewer Matrix",
            &Uuid::new_v4().to_string(),
            "2026-04-15T00:00:00Z",
        )
        .unwrap();

        assert_eq!(prepared.source_mode, "generated");
        assert!(prepared.relative_path.contains("/notes/"));
        assert!(prepared.file_name.ends_with(".md"));
    }
}
