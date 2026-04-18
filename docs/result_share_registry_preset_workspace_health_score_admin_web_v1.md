# Result Share Registry Preset Workspace Health Score Admin Web v1

## Why Health Score Is Added After Workspace Import Export Exists
- Phase 66 already organized browser-local preset work into one preset workspace.
- Phase 67 already added a separate local JSON transfer layer for workspace organization state.
- Operators still needed one compact browser-local summary for stale pins, backup readiness, diagnostics issues, recent failed imports or recovery attempts, and drilldown-context hygiene.
- This phase adds a deterministic local operator hygiene score instead of backend scoring, compliance language, or automatic repair.

## Local Heuristic Score Model
- The health score is a deterministic integer in the range `0..100`.
- Status bands are:
  - `healthy`: `90..100`
  - `attention`: `70..89`
  - `risk`: `40..69`
  - `critical`: `0..39`
- The score is derived only from safe browser-local state:
  - preset storage integrity
  - preset validity
  - pinned preset hygiene
  - backup readiness
  - audit reliability
  - import/export safety
  - drilldown-context completeness
- The score is always clamped to `0..100`.

## Score Breakdown Dimensions
- `storageIntegrity`
- `presetValidity`
- `pinnedPresetHygiene`
- `backupReadiness`
- `auditReliability`
- `importExportSafety`
- `drilldownContextCompleteness`

Each dimension is shown directly in the preset workspace and uses transparent penalty rules.

## Finding And Recommendation Model
- Findings are local-only safe summaries with these severities:
  - `info`
  - `warning`
  - `error`
  - `critical`
- Current finding codes include:
  - `storage_invalid_json`
  - `unsafe_field_detected`
  - `invalid_schema_version`
  - `dangling_default_preset`
  - `stale_pinned_presets`
  - `missing_last_good_backup`
  - `corrupted_audit_history`
  - `recent_failed_import`
  - `recent_failed_recovery`
  - `no_saved_presets`
  - `no_pinned_presets`
  - `invalid_drilldown_context`
  - `import_preview_has_errors`
- Recommendations only point to existing local actions such as:
  - run integrity check
  - discard invalid presets
  - clean stale pins
  - create backup
  - restore last-good backup
  - validate import before apply
  - reset workspace state
  - review recent audit failures
  - add pinned presets
- Health calculation never auto-fixes local state.

## Local-Only Boundary
- The score is browser-local operator hygiene only.
- It is not:
  - backend health
  - security scoring
  - compliance scoring
  - team-shared preset state
- The score never reads or stores:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - hashes
  - response payloads
  - source-file data

## Non-Security Compliance Caveat
- A lower score means the current browser-local preset workspace probably needs cleanup, backup, validation, or stale-pin repair.
- A higher score does not certify broader system security, policy compliance, or backend correctness.

## Current Non-Goals
- No backend health scoring
- No backend preset or workspace persistence
- No cloud sync
- No automatic repair on score calculation
- No source-file, attachment, or note sharing

## Future Work
- Local threshold preferences only if later justified
- Richer operator health dashboards only if later justified
- Team preset workspace health only if backend persistence is ever added
- Policy-driven preset validation only if later justified
- Still no source-file sharing by default
