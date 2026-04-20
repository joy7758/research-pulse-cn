# Result Share Registry Drilldown Linked Presets Admin Web v1

## Why Drilldown-Linked Presets Are Added After Local Saved Views
- Phase 61 already added local-only saved views for result-share registry filter and sort state.
- Operators still had to re-enter the same per-share drilldown time window, event filters, and recent-row limit after opening a grant or alias from the registry.
- This phase extends the same local preset layer instead of changing backend contracts or adding a new app.

## Local-Only Preset Model Extension
- Presets remain browser-local only.
- Each preset may now optionally carry a compact drilldown context block containing:
  - `dateFrom`
  - `dateTo`
  - `accessMode`
  - `eventType`
  - `outcome`
  - `limit`
- Old presets without drilldown context remain valid and load as registry-only presets.

## Registry-Only Vs Registry-Plus-Drilldown Apply Behavior
- `Apply registry only` restores saved registry filters and sort without touching current per-share drilldown filters.
- `Apply registry + drilldown` restores saved registry filters and sort plus the saved per-share drilldown context.
- Restoring the default preset follows the same rule:
  - registry-only if no drilldown context is stored
  - registry-plus-drilldown if drilldown context is stored

## Grant Vs Alias Preset Scope Separation
- Grant-registry presets still affect only grant-registry filter and sort state.
- Alias-registry presets still affect only alias-registry filter and sort state.
- Optional drilldown context is shared only as read-only per-share filter state and does not overwrite unrelated registry scope fields.

## Safe Storage Rules
- Allowed in local storage:
  - safe registry filter state
  - safe registry sort state
  - safe per-share drilldown filter state
  - local preset names
  - default preset marker
- Not allowed in local storage:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - response payload caches
  - source-file, attachment, or note content

## Current Non-Goals
- No backend/team preset persistence
- No backend-synced preset exchange
- No write actions in registry or drilldown panels
- No new frontend app
- No source-file, attachment, or note sharing

## Future Work
- Local preset diagnostics, last-good backup snapshots, and validation-only recovery UX was added later without changing the same safe drilldown-context model.
- Backend/team presets only if later justified
- Shared operator workspaces only if later justified
- Preset signing or provenance checks only if later justified
- Still no source-file sharing by default
