# Result Share Registry Preset Workspace Health Report Copy Admin Web v1

## Why Clipboard Summaries Are Added After Report Export Exists
- Phase 70 already added safe browser-local JSON and Markdown health report export.
- Operators still need a faster browser-only path for sharing short local hygiene summaries into tickets, chat, or notes without downloading files.
- This phase adds clipboard-first summaries on top of the same safe report model instead of inventing a second health-report system.

## Clipboard Summary Formats
- Supported browser-local clipboard formats:
  - `health_summary`
  - `findings_summary`
  - `recommendations_summary`
  - `compact_markdown`
  - `compact_json`
- All formats are derived from the existing safe health report preview.
- Clipboard summaries are compact operator-readable views, not new persisted report objects.

## Copy Safety Validation
- Copy runs deterministic validation before clipboard write.
- Validation checks:
  - required metadata
  - valid score and status shape
  - safe field names
  - rejection of unsafe-looking identifiers such as token/hash/path/source-file names
  - optional large-payload warning
- Validation failure blocks copy and surfaces only safe error text.

## Local Audit Action Types
- Copy actions record safe browser-local audit events only:
  - `preset_workspace_health_report_copied_summary`
  - `preset_workspace_health_report_copied_findings`
  - `preset_workspace_health_report_copied_recommendations`
  - `preset_workspace_health_report_copied_markdown`
  - `preset_workspace_health_report_copied_json`
  - `preset_workspace_health_report_copy_validation_failed`
  - `preset_workspace_health_report_copy_failed`
- Audit events never include copied payload bodies.

## Safety Exclusions
- Clipboard summaries exclude:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - `token_hash` / `alias_hash`
  - saved preset definitions
  - raw workspace state objects
  - raw import/export payload bodies
  - backend response payloads
  - local file paths
  - source-file data
- Clipboard output is limited to safe score, threshold, findings, recommendation, and diagnostics summaries.

## Local-Only Boundary
- Clipboard summaries are browser-local operator hygiene conveniences.
- They are not:
  - backend reports
  - team-shared reports
  - security reports
  - compliance reports
  - backend-persisted artifacts
- Copying never triggers backend writes or recovery actions.

## Non-Security Compliance Caveat
- Copied text reflects browser-local preset workspace hygiene only.
- It should not be interpreted as broader system security posture, backend correctness, or compliance evidence.

## Current Non-Goals
- No backend report persistence
- No cloud or team-shared clipboard sync
- No raw preset payload copy
- No source-file, attachment, or note copying
- No AI-generated interpretation

## Future Work
- Richer local operator copy snippets only if later justified
- Signed local summary packages only if ever needed
- Backend or team report sharing only if persistence is later justified
- Print-friendly local views only if later justified
- Still no source-file sharing by default
