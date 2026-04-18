# Result Share Registry Preset Workspace Health Thresholds Admin Web v1

## Why Local Health Threshold Preferences Are Added After Health Score Exists
- Phase 68 already added a deterministic local preset workspace health score with transparent findings and recommendations.
- Operators still needed a browser-local way to adjust how the same raw score maps into `healthy`, `attention`, `risk`, and `critical` for their own working style.
- This phase adds local threshold preferences and draft validation without turning health scoring into backend policy or shared team configuration.

## Default Threshold Model
- Default status thresholds remain:
  - `healthy`: `90..100`
  - `attention`: `70..89`
  - `risk`: `40..69`
  - `critical`: `0..39`
- When no local preference exists, the health score behaves exactly like Phase 68.

## Local Threshold Preference Model
- Browser-local storage key:
  - `resultShareRegistryPresetWorkspaceHealthThresholdPreferences`
- Stored fields are non-sensitive only:
  - `statusThresholds`
  - optional `findingPenaltyOverrides`
  - `recommendationVisibility`
  - `updatedAt`
- `statusThresholds` contains:
  - `healthyMin`
  - `attentionMin`
  - `riskMin`
  - `criticalMin`
- `criticalMin` stays fixed at `0` in v1.
- `findingPenaltyOverrides` is local-only and limited to supported preset-workspace hygiene rules.
- `recommendationVisibility` controls which local finding severities stay visible in the health panel.

## Validation Rules
- Threshold values must be integers.
- Threshold values must stay within `0..100`.
- Threshold order must satisfy:
  - `healthyMin > attentionMin > riskMin > criticalMin`
- Status ranges must remain contiguous and non-overlapping.
- Penalty overrides must be non-negative integers within a safe local cap.
- Unsupported penalty keys are ignored with warnings.
- Invalid drafts never replace the current valid stored preferences.
- Corrupted stored preferences fall back safely to defaults.

## Status Classification Vs Raw Score
- The raw health score is still computed deterministically from existing local preset diagnostics, audit history, backup presence, pin hygiene, and import/export preview state.
- Threshold preferences primarily affect status classification for that raw score.
- Local penalty overrides may also adjust raw score when an operator explicitly sets them, but this remains browser-local and never changes backend state.
- Preview shows the current health result and the draft result before apply.

## Local-Only Boundary
- Threshold preferences are browser-local operator display preferences.
- They are not:
  - backend health policy
  - security scoring
  - compliance scoring
  - team-wide or shared thresholds
- They never store:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - hashes
  - response payloads
  - source-file data

## Non-Security Compliance Caveat
- Threshold preferences only affect local interpretation of the browser-local hygiene score.
- They do not certify broader system correctness, security posture, or regulatory compliance.

## Current Non-Goals
- No backend threshold persistence
- No team-shared threshold policy
- No automatic recovery based on threshold preferences
- No source-file, attachment, or note sharing

## Future Work
- Local health summary export only if later justified
- Team-wide thresholds only if backend persistence is ever justified
- Policy-driven preset validation only if later justified
- Richer operator health dashboards only if later justified
- Still no source-file sharing by default
