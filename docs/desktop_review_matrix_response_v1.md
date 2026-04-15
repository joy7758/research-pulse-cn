# Desktop Review Matrix And Structured Response Templates v1

## Why Review Matrix Stays Local-Only In v1
- Review rounds and reviewer comments are still personal working-state, not stable backend business entities.
- Keeping them local avoids freezing a cloud schema before import, collaboration, or sync rules are clear.
- This phase is about deterministic local structure and repeatable markdown outputs, not AI-assisted extraction or shared workflows.

## Review Round Model
- `paper_review_round_cache` stores per-paper local review rounds.
- Fields:
  - `id`, `paper_id`
  - `round_label`
  - `venue`
  - `decision_label`
  - `status`
  - `source_mode`
  - `reviewer_count`
  - `generated_response_note_id`
  - `generated_matrix_note_id`
  - `created_at`, `updated_at`
- Rounds are manual-entry-first in v1 and do not sync to the backend.

## Comment Matrix Model
- `review_comment_item_cache` stores structured reviewer comments under one round.
- Fields:
  - `id`, `review_round_id`, `paper_id`
  - `reviewer_label`
  - `comment_code`
  - `sort_order`
  - `comment_text`
  - `category`
  - `disposition`
  - `response_summary`
  - `action_note`
  - `created_at`, `updated_at`
- Ordering is deterministic:
  - `reviewer_label` ascending
  - `sort_order` ascending
  - `created_at` ascending
- Delete operations do not renumber remaining comments.

## Built-In Generated Outputs
- `reviewer_matrix` note:
  - grouped by reviewer
  - includes comment text, disposition, response summary, and action note
- `response_letter` note:
  - grouped by reviewer
  - includes a simple editor-facing opening and close
  - uses `response_summary` as the main response body
  - shows a visible placeholder when no response summary has been entered
- Both outputs are plain markdown rendered in Rust with no AI generation.

## Generated Note Linkage Model
- Generated markdown files live under:
  - `papers/<paper_id>/notes/`
- Generated files are indexed in the existing `paper_note_cache`.
- Review rounds link to generated note rows through:
  - `generated_matrix_note_id`
  - `generated_response_note_id`
- Deterministic strategy in v1:
  - if the round already links to a generated note, regenerate by updating that same note file and note-cache row in place
  - otherwise create a new generated note and store the link on the round

## Local-Only Consistency Model
- Review round metadata is local-only in v1.
- Generated review notes are local-only files.
- The local SQLite DB is the source of truth for round/comment metadata.
- The markdown file on disk is the source of truth for generated note content.
- `clearLocalCache` and `disconnectDevice` do not delete generated review notes.
- If the workspace root is missing or invalid, generation fails clearly instead of faking success.

## Current Non-Goals
- no AI reviewer comment extraction
- no OCR or PDF / DOCX parsing
- no cloud sync for rounds, comments, or generated notes
- no collaboration, sharing, or commenting
- no rich text editor
- no automatic journal-email import

## Future Work
- import helpers from pasted reviewer text
- note sync and cross-device review-matrix metadata
- richer response-drafting tools
- template customization
- review analytics and revision progress summaries
