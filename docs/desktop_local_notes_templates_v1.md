# Desktop Local Notes And Templates v1

## Why Notes/Templates Are Local-Only In v1
- The desktop shell needs a practical local note workflow before cloud sync, sharing, or richer collaboration models are safe to freeze.
- Keeping notes local avoids prematurely locking the backend into a note schema that may not fit later workspace and collaboration needs.
- Note content stays file-backed on disk while note metadata stays indexed in desktop SQLite.

## Built-In Template Kinds
- `blank_note`
- `research_note`
- `revision_plan`
- `response_letter`
- `reviewer_matrix`
- `submission_checklist`

Each template is rendered on the Rust side from deterministic markdown generators. Templates receive paper context such as title, id, stage, venue, next action, and blocker.

## Note Metadata Model
- `paper_note_cache` is the local metadata index for per-paper notes.
- Stored fields include:
  - identity: `id`, `paper_id`, `template_kind`, `title`
  - file linkage: `file_name`, `relative_path`, `absolute_path`
  - local state: `content_format`, `source_mode`, `status`
  - file metadata: `size_bytes`, `sha256`
  - timestamps: `created_at`, `updated_at`, `last_opened_at`
- The local database is the source of truth for note metadata only.

## Note File Layout
- Notes live under the existing local workspace tree:
  - `papers/<paper_id>/notes/`
- File names are deterministic, safe markdown file names keyed by timestamp, note id prefix, and sanitized title.
- Paper title changes from sync do not move existing note files because the folder path stays anchored on `paper_id`.

## Create/Read/Save Flow
- `listNoteTemplates` returns built-in template metadata for the desktop UI.
- `createPaperNoteFromTemplate` ensures the paper workspace exists, renders markdown, writes the file under `notes/`, and indexes metadata in `paper_note_cache`.
- `createBlankPaperNote` creates a blank markdown note under the same directory and indexes it the same way.
- `getPaperNote` loads indexed metadata plus current markdown content from disk.
- `savePaperNote` writes markdown to disk and refreshes size/hash/timestamps in local metadata.
- `refreshPaperNotes` rebinds paths against the current workspace root and marks notes `missing` when files disappear.

## Local-Only Consistency Model
- Note metadata is local-only in v1.
- Note content is file-backed local state.
- Backend sync does not upload or download note files or note metadata.
- `clearLocalCache` and `disconnectDevice` do not delete note files under the workspace root.
- If the workspace root is missing or invalid, note creation and save commands fail clearly rather than faking success.

## Current Non-Goals
- no note sync to the backend
- no AI note generation
- no OCR or text extraction
- no rich text editor or markdown WYSIWYG
- no collaboration, sharing, or comments
- no markdown preview pane
- no automatic filesystem watching

## Future Work
- note sync and cross-device note metadata
- richer revision-response tooling built on note templates
- per-user template customization
- markdown preview and richer note navigation
- local backlinks, search, and indexing across notes
