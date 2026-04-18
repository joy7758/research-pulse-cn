# Result Share Registry Saved Views Admin Web v1

## Why Saved Views Are Added After Filter Sort UX Exists
- Phase 60 already made the result-share registry substantially more usable with:
  - stronger filters
  - deterministic stable sort
  - filter chips
  - grant-to-alias relationship shortcuts
- Operators still had to rebuild common registry setups manually for repeated review flows.
- This phase adds local-only saved views on top of the existing registry shell instead of changing backend contracts or creating a new app.

## Local-Only Preset Model
- Saved views are stored in browser `localStorage` only.
- Presets are read-only operator conveniences, not backend-owned objects.
- A saved view contains only:
  - preset `id`
  - local `name`
  - `scope`
  - safe registry filter state
  - safe registry sort state
  - `createdAt`
  - `updatedAt`
- The shell may optionally mark one preset as the local default restore target.

## Grant Vs Alias Preset Scope Separation
- Grant presets and alias presets stay logically separate.
- Grant-scope presets save and restore:
  - `share_kind`
  - grant status
  - workspace ID
  - grant sort mode
- Alias-scope presets save and restore:
  - `share_kind`
  - alias status
  - linked grant ID
  - alias sort mode
- Applying one preset does not overwrite unrelated scope-specific fields or sort state.

## Safe Storage Rules
- Allowed in local storage:
  - non-sensitive registry filter state
  - non-sensitive registry sort state
  - local preset names
  - local default preset marker
- Not allowed in local storage:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - API response payload caches
  - source-file or attachment data
- The shell continues to keep admin bearer tokens in memory only.

## Current Non-Goals
- No backend-saved or team-shared presets
- No import/export for presets
- No business write actions in the registry
- No source-file, attachment, or note-file sharing
- No new frontend app
- No new auth system

## Future Work
- Team/shared presets only if later justified
- Preset import/export only if later justified
- Richer operator workspaces across multiple admin views
- Still no source-file sharing by default
