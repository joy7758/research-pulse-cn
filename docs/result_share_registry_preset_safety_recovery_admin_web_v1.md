# Result Share Registry Preset Safety Recovery Admin Web v1

## Why Safety Recovery Is Added After Local Import Export Exists
- Phase 61 added local-only saved views for safe registry filter and sort state.
- Phase 62 let those presets optionally carry safe per-share drilldown filter context.
- Phase 63 added local JSON import/export with preview-before-apply validation.
- Operators still needed a safer way to detect corrupted browser storage, quarantine invalid entries, and recover a last-good local preset set without touching backend state.

## Local Storage Diagnostics Model
- Diagnostics stay browser-local and inspect only:
  - grant preset key presence
  - alias preset key presence
  - default preset marker presence
  - last-good backup presence
  - valid and invalid preset counts
  - warning and error counts
  - latest validation time
- Diagnostics never display:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - hash fields
  - local file paths
  - source files

## Integrity Issue Model
- Integrity checks report safe issue metadata only:
  - `severity`
  - `scope`
  - `presetId` when safe and available
  - `presetName` when safe and available
  - `code`
  - safe message
  - redacted safe details
- Supported issue codes include:
  - `invalid_json`
  - `invalid_schema_version`
  - `invalid_scope`
  - `unsafe_field_detected`
  - `invalid_filter_shape`
  - `invalid_sort_shape`
  - `invalid_drilldown_context`
  - `missing_required_field`
  - `duplicate_preset_id`
  - `dangling_default_preset`
  - `storage_key_unreadable`
  - `storage_key_not_array`

## Recovery Actions
- Operators can:
  - validate current local preset storage
  - discard invalid grant presets
  - discard invalid alias presets
  - clear a dangling default preset marker
  - reset only the grant preset scope
  - reset only the alias preset scope
  - reset all result-share registry presets
  - restore the latest last-good backup snapshot
- Recovery actions are local-only, require explicit confirmation for destructive cases, and do not call backend endpoints.

## Last-Good Backup Behavior
- A compact local backup snapshot is created before risky operations:
  - import merge
  - import replace
  - discard invalid presets
  - reset scope
  - reset all presets
- Backup content includes only safe preset fields plus the local default preset marker.
- v1 keeps only one latest backup under a browser-local storage key.
- Backup restore re-validates the snapshot before applying it.

## Import Validation-Only Behavior
- Selecting a preset JSON file stays validation-only until an operator explicitly applies merge or replace.
- Validation-only preview shows:
  - valid preset count
  - invalid preset count
  - scope counts
  - warnings
  - errors
- Invalid imports never mutate local storage.

## Safe Storage Rules
- Browser-local keys remain limited to:
  - `resultShareRegistryGrantPresets`
  - `resultShareRegistryAliasPresets`
  - `resultShareRegistryDefaultPresetId`
  - `resultShareRegistryPresetLastGoodBackup`
- Stored content is limited to safe registry filter/sort state, optional safe drilldown filter context, preset names, timestamps, default marker, and backup metadata.
- No bearer token, raw share token, raw alias, source-file path, or response payload cache is persisted.

## Current Non-Goals
- No backend or team preset persistence
- No cloud sync
- No preset signing
- No registry write actions
- No source-file, attachment, or note sharing

## Future Work
- Team preset management only if later justified
- Signed preset packages only if later justified
- Richer operator workspace recovery tools only if later justified
- Still no source-file sharing by default
