# Result Share Registry Preset Workspace Health Report Export Admin Web v1

## Why Health Report Export Is Added After Threshold Preferences Exist
- Phase 68 already introduced a deterministic browser-local preset workspace health score.
- Phase 69 added browser-local threshold preferences so operators can tune status interpretation without changing backend behavior.
- This phase adds local-only health report export so the same safe health summary can be reviewed, copied between local workflows, or archived outside the browser without exporting preset payloads or backend data.

## Local Report Model
- Export format stays browser-local and read-only.
- Report metadata includes:
  - `schemaVersion`
  - `generatedAt`
  - `app`
  - `source`
  - `reportKind`
  - `thresholdPreferenceSource`
  - `localOnly`
  - `safeExport`
- Report body includes only safe summary sections:
  - `health`
  - `thresholds`
  - `diagnostics`
  - `workspaceSummary`
  - `auditSummary`
  - `findings`
  - `recommendations`
  - `safetyExclusions`
  - `notes`

## JSON Export Schema
- JSON schema version:
  - `result-share-registry-preset-workspace-health-report.v1`
- Stable top-level fields:
  - `schemaVersion`
  - `generatedAt`
  - `app`
  - `source`
  - `reportKind`
  - `metadata`
  - `health`
  - `thresholds`
  - `diagnostics`
  - `workspaceSummary`
  - `auditSummary`
  - `findings`
  - `recommendations`
  - `safetyExclusions`
  - `notes`
- The JSON export is human-readable and indented.

## Markdown Export Structure
- Markdown uses compact operator-readable sections:
  - `Report Metadata`
  - `Health Summary`
  - `Thresholds`
  - `Breakdown`
  - `Findings`
  - `Recommendations`
  - `Local Diagnostics Summary`
  - `Preset Workspace Summary`
  - `Local Audit Summary`
  - `Safety Exclusions`
  - `Notes`
- The Markdown export is descriptive but does not dump raw local storage or preset payloads.

## Report Validation Rules
- Export runs deterministic validation before download.
- Validation checks:
  - required metadata fields
  - health score range `0..100`
  - valid health status values
  - non-empty threshold summary
  - stable safe field names
  - no unsafe-looking field keys such as token/hash/path/source-file names
- If validation fails, export is blocked and only a safe local audit event is recorded.

## Safety Exclusions
- Reports exclude:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - `token_hash` / `alias_hash`
  - saved preset definitions
  - raw preset workspace state objects
  - raw import/export payload bodies
  - backend response payloads
  - local file paths
  - source-file data
- Reports summarize safe counts, labels, findings, and recommendations only.

## Local-Only Boundary
- Health reports are browser-local operator hygiene exports.
- They are not:
  - backend health reports
  - security reports
  - compliance reports
  - team-shared reports
  - backend-persisted artifacts
- Export never triggers automatic repair or backend writes.

## Non-Security Compliance Caveat
- The exported report reflects browser-local preset workspace hygiene only.
- It should not be interpreted as a broader security certification, compliance control, or backend health statement.

## Current Non-Goals
- No backend report persistence
- No cloud or team-shared report sync
- No raw preset payload dump
- No source-file, attachment, or note export
- No AI-generated analysis copy

## Future Work
- Richer local operator health summaries only if later justified
- Signed local report packages only if ever needed
- Backend or team health reports only if persistence is later justified
- Clipboard-first health summary views only if later justified
- Still no source-file sharing by default
