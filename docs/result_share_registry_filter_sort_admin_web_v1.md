# Result Share Registry Filter Sort Admin Web v1

## Why Registry Filter Sort UX Is Added After The Basic Registry Exists
- Phase 59 already added a read-only result-share grant and alias registry inside `apps/group-workspace-admin-web`.
- Operators could browse safe rows and quick-open drilldown, but common review flows still required too much manual scanning.
- This phase strengthens the existing registry instead of rebuilding it:
  - applied filter chips
  - explicit sort controls
  - grant-to-alias relationship shortcuts
  - clearer filtered empty-state explanations
- The goal remains a thin internal read-only operator shell, not a new write surface, auth system, or source-file feature.

## Supported Filter Dimensions
- Share-grant registry supports:
  - `share_kind`
  - `status`
  - `workspace_id`
  - `digest_issue_id` when present in safe list rows
  - `paper_id` when present in safe list rows
- Alias registry supports:
  - `result_share_grant_id`
  - `share_kind`
  - `status`
- The UI keeps draft filters separate from applied filters so operators can adjust registry narrowing without reloading the whole shell.
- Applied filters render as compact chips so zero-result states can explain why rows disappeared.

## Supported Sort Modes
- Registry sort modes stay read-only and deterministic.
- Supported sort fields:
  - `created_at`
  - `last_used_at`
  - `expires_at`
  - `share_kind`
  - `status`
- Supported directions:
  - ascending
  - descending
- Sort is stable on the frontend over already loaded safe rows.
- Tie-breaking always falls back to `id` ascending.
- `last_used_at` and `expires_at` keep `null` values last in both directions so inactive or non-expiring rows do not jump ahead unexpectedly.

## Grant Alias Relationship Shortcuts
- Grant rows can still quick-open grant drilldown directly.
- Grant rows now also expose a `show aliases for this grant` shortcut that applies the alias registry filter immediately.
- Alias rows can quick-open alias drilldown directly.
- Alias rows can also quick-open the underlying grant drilldown without manual ID copy/paste.
- Registry relationships remain safe summaries only:
  - no plaintext share tokens
  - no plaintext aliases
  - no one-time token reveal

## Safe Data Model
- The registry continues to consume only existing admin-safe list and drilldown routes.
- It does not expose:
  - plaintext share tokens
  - plaintext aliases
  - raw IP addresses
  - full referrer URLs
  - raw user-agent strings
  - local filesystem paths
  - local note contents
  - local attachment paths
  - source file contents
- Admin bearer tokens still remain in memory only.

## Current Non-Goals
- No create / revoke / bulk operation controls in the registry
- No new frontend app
- No new login or session system
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No browser analytics SDK
- No AI-generated attribution or AI-written registry copy

## Future Work
- Saved local registry filters or operator presets
- Per-share comparison views
- Registry-level bulk operations only if later justified
- Still no source-file sharing by default
