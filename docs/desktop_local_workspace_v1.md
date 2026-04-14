# Desktop Local Workspace v1

## Why Local Workspace Comes Before Cloud File Sync
- The desktop shell needs a stable local paper workspace before file upload, cross-device attachment sync, or AI-assisted organization are safe to add.
- Keeping attachments local in v1 avoids prematurely freezing a cloud file model that would be expensive to unwind later.
- This phase focuses on deterministic structure, managed copies, and metadata indexing only.

## Local-Only Attachment Model
- Attachment metadata lives only in the desktop local SQLite database.
- Imported files are managed copies under a user-chosen workspace root.
- Original source files are never modified or deleted.
- `clearLocalCache` and `disconnectDevice` do not delete managed workspace files.

## Workspace Root Model
- The workspace root is chosen locally from the desktop shell.
- The root is validated on the Rust side for:
  - existence
  - directory shape
  - writability
- Root state is persisted in `workspace_settings`.
- Changing the root does not migrate old managed files in v1.

## Per-Paper Folder Layout
- Each paper gets a stable path keyed by `paper_id`.
- Current layout:
  - `papers/<paper_id>/`
  - `papers/<paper_id>/attachments/`
  - `papers/<paper_id>/notes/`
  - `papers/<paper_id>/exports/`
- A `workspace.json` placeholder is created in the paper root with compact paper identity and layout metadata.

## Managed-Copy Import Model
- Attachment import is always `managed_copy`.
- The desktop UI can open native file dialogs, but the Rust command layer performs:
  - path validation
  - duplicate detection
  - destination path generation
  - file copy
  - metadata indexing
- Supported attachment kinds:
  - `manuscript`
  - `review`
  - `response_letter`
  - `figure`
  - `dataset`
  - `supplement`
  - `note`
  - `other`

## Duplicate Handling
- Duplicate detection is best-effort within one paper workspace.
- v1 uses:
  - `sha256` when available
  - file size fallback heuristics when needed
- Duplicate imports return a clear `duplicate` result and do not silently create another managed copy.

## Local Read Models
- `WorkspaceStatusRead`
- `PaperWorkspaceRead`
- `PaperAttachmentRead`

Existing paper read models are extended with local-only workspace state:
- `PaperListItemRead`
  - `attachmentCount`
  - `workspaceReady`
- `PaperDetailRead`
  - `workspace`
  - `attachments`

## Current Non-Goals
- no cloud attachment sync
- no OCR or text extraction
- no PDF parsing or citation extraction
- no AI file classification or organization
- no automatic filesystem watching
- no rich previewers
- no drag-and-drop workflow

## Future Work
- cloud attachment sync and server-side attachment models
- OCR and text extraction
- local previewers
- drag-and-drop import
- richer note/export templates inside each paper workspace
