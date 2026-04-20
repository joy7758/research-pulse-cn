# Result Share Registry Preset Workspace Import Export Admin Web v1

## Why Workspace-State Import Export Is Added After Preset Workspace Organization Exists
- Phase 66 already added a browser-local preset workspace for pinning grant and alias presets, tracking the last active preset, and summarizing storage health.
- Operators still needed a way to move that local organization state between browser profiles without re-exporting or re-importing the saved preset definitions themselves.
- This phase adds a second JSON transfer layer for workspace organization only, keeping it separate from the Phase 63 saved-preset import/export model.

## Distinction From Saved-View Preset Import Export
- Phase 63 import/export moves saved preset definitions:
  - `grantRegistry`
  - `aliasRegistry`
  - safe filter/sort state
  - optional safe drilldown context
- Phase 67 import/export moves only preset workspace organization:
  - `pinnedGrantPresetIds`
  - `pinnedAliasPresetIds`
  - `lastActivePresetScope`
  - `lastActivePresetId`
  - optional `collapsedSections`
  - `updatedAt`
- Workspace-state import/export never includes saved preset definitions in this phase.

## JSON Export Schema
- Workspace export is a human-readable local JSON document with:
  - `schemaVersion`
  - `exportedAt`
  - `app`
  - `source`
  - `workspaceState`
- `schemaVersion` is `result-share-registry-preset-workspace.v1`.
- `workspaceState` carries only safe browser-local organization fields:
  - `pinnedGrantPresetIds`
  - `pinnedAliasPresetIds`
  - `lastActivePresetScope`
  - `lastActivePresetId`
  - optional `collapsedSections`
  - `updatedAt`

## Import Validation Model
- Import validates `schemaVersion` before any browser-local workspace state is changed.
- Import validates:
  - `workspaceState` object shape
  - pinned preset id arrays
  - `lastActivePresetScope`
  - `lastActivePresetId`
  - optional `collapsedSections`
  - unsafe-looking field names such as token, secret, hash, password, raw alias, raw share token, local path, source file, or response payload
- Import preview reports:
  - `canApply`
  - `valid`
  - warnings
  - errors
  - pinned grant count
  - pinned alias count
  - stale grant pin ids
  - stale alias pin ids
  - whether the imported last-active preset exists locally
- Invalid imports never mutate browser-local state.

## Merge Vs Replace Behavior
- `Merge` preserves current pin order first, then appends imported pins that are not already present.
- `Merge` updates the last-active preset only when the imported last-active preset exists locally.
- `Merge` shallowly merges optional collapsed-section state.
- `Replace` updates only the browser-local workspace organization state.
- `Replace` never deletes saved preset definitions and never touches backend data.
- If imported last-active preset ids do not exist locally, the workspace clears that marker with a warning.

## Stale Pin Handling
- Imported workspace state is validated against the current local saved preset store.
- Preview explicitly lists:
  - stale grant pins
  - stale alias pins
- Stale pins can still be imported because the existing stale-pin cleanup UX from Phase 66 can remove them later.
- Preview and post-import notices recommend cleanup when stale pins remain.

## Backup Behavior
- Before applying workspace-state import, the shell writes one last-good workspace backup snapshot to:
  - `resultShareRegistryPresetWorkspaceLastGoodBackup`
- Backup schema is:
  - `schemaVersion`
  - `createdAt`
  - `reason`
  - `workspaceState`
- Restore validates the backup before applying it back into local workspace organization state.
- Workspace backup does not include saved preset definitions, bearer tokens, raw aliases, raw tokens, or source-file data.

## Local-Only Safe Storage Rules
- Workspace-state import/export is browser-local operator convenience only.
- It never stores or exports:
  - admin bearer tokens
  - raw share tokens
  - raw aliases
  - hashes
  - response payloads
  - local file paths
  - source files
- It does not imply backend sync, team-shared workspace settings, or cloud persistence.

## Current Non-Goals
- No backend/team workspace persistence
- No cloud sync
- No duplication of saved preset definition import/export
- No source-file, attachment, or note import/export
- No generic login surface

## Future Work
- Local workspace health scoring was added in the next phase without changing the same workspace-state JSON boundary into backend or compliance semantics.
- Shared/team workspace settings only if later justified
- Shared operator dashboards only if later justified
- Richer preset grouping only if later justified
- Still no source-file sharing by default
