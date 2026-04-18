# Result Share Registry Preset Import Export Admin Web v1

## Why Local Import Export Is Added After Local Saved Views And Drilldown-Linked Presets
- Phase 61 already added local-only saved views for safe registry filter and sort state.
- Phase 62 already let those presets optionally carry safe per-share drilldown filter context.
- Operators still could not move their local preset sets between browser profiles or stage a larger local cleanup safely.
- This phase adds local JSON import/export on top of the same browser-only preset layer instead of adding backend preset storage or a new app.

## JSON Export Schema
- Export is a human-readable local JSON document with:
  - `schemaVersion`
  - `exportedAt`
  - `app`
  - `source`
  - `presets.grantRegistry`
  - `presets.aliasRegistry`
- `schemaVersion` is `result-share-registry-presets.v1`.
- Export includes only safe preset fields:
  - `id`
  - `name`
  - `scope`
  - `filters`
  - `sort`
  - optional `drilldownContext`
  - `createdAt`
  - `updatedAt`

## Import Validation Model
- Import validates `schemaVersion` before any local state is changed.
- Import validates:
  - supported scopes
  - preset field names
  - filter/sort/drilldown value shape
  - unsafe-looking field names such as token, secret, hash, password, raw alias, raw share token, or local/source paths
- Old presets without `drilldownContext` remain valid and normalize into the current model.
- Invalid imports produce preview errors and warnings without mutating local storage.

## Merge Vs Replace Behavior
- `Merge` keeps existing presets and appends valid imported presets.
- If an imported preset ID already exists locally, the shell generates a safe new local ID and imported-copy name suffix.
- `Replace` updates only scopes present in the import payload:
  - imported `grantRegistry` replaces local grant presets
  - imported `aliasRegistry` replaces local alias presets
- Absent scopes are preserved.
- Unsupported imported default markers are ignored.
- If a current local default preset no longer exists after replace, the local default marker is cleared.

## Local-Only Safe Storage Rules
- Import/export is local operator convenience only.
- Preset JSON never includes:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - response payload caches
  - local file paths
  - source files
- Browser storage still uses the same local keys:
  - `resultShareRegistryGrantPresets`
  - `resultShareRegistryAliasPresets`
  - `resultShareRegistryDefaultPresetId`

## Current Non-Goals
- No backend/team preset persistence
- No cloud sync
- No preset signing
- No write actions in registry or drilldown panels
- No source-file, attachment, or note sharing

## Future Work
- Local diagnostics and last-good recovery was added in the next phase without changing the export schema or adding backend preset storage.
- Backend/team presets only if later justified
- Preset signing or provenance metadata if later justified
- Shared operator workspaces only if later justified
- Still no source-file sharing by default
