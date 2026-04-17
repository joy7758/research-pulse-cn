# Group Workspace Conversion Filter Admin Web v1

## Why Time-Window Filtering Is Added After Overview And Drilldown Shells Exist
- Phase 53 already added the read-only conversion overview shell inside `apps/group-workspace-admin-web`.
- Phase 55 already added the read-only drilldown shell for daily buckets, recent activity, and top entities.
- This phase adds compact operator filters on top of those existing reads so the same shell can narrow time windows and activity dimensions without creating a new app, a write path, or a second auth surface.

## Supported Filter Dimensions
- The shell keeps using the existing read-only admin endpoints:
  - `GET /admin/group-workspace-conversion-overview`
  - `GET /admin/group-workspace-conversion-drilldown`
  - `GET /admin/group-workspaces/{workspace_id}/conversion-overview`
  - `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown`
- The filter bar now supports:
  - `date_from`
  - `date_to`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `outcome`
  - `limit` for drilldown recent/top sections
- Query shaping stays deterministic and continues to attach the admin bearer token from in-memory state only.
- When operators leave `date_from` and `date_to` empty, the shell reuses the backend default analytics window instead of inventing a frontend-only fallback.

## Global Vs Workspace Filter Scope
- The global filter bar narrows the global overview plus global drilldown panels together.
- The workspace filter bar narrows the selected workspace overview plus workspace drilldown panels together.
- `limit` applies only to drilldown recent/top sections and does not alter overview totals.
- Filters apply without a page reload and can be reset back to the shell defaults.
- Workspace filters remain scoped to the currently selected workspace and do not leak into the workspace list itself.

## Attribution Semantics Remain Unchanged
- Filtering narrows the read model only.
- Filtering does not upgrade workspace-level aggregate invite signals into strict per-share attribution.
- Direct share and collect attribution remain direct only when persisted links exist in the backend reserve.
- The shell keeps direct-attribution notes and aggregate-only notes explicit so operators do not confuse narrower slices with stronger causal evidence.

## Safe Data Model
- The shell still consumes only existing admin-safe read models.
- It does not expose:
  - plaintext share tokens
  - plaintext aliases
  - raw IP addresses
  - full referrer URLs
  - raw user-agent strings
  - local filesystem paths
  - local attachments
  - local note contents
  - source file contents
- Admin bearer tokens remain in memory only and query/fragment token hints are still removed from the visible URL immediately after bootstrap.

## Current Non-Goals
- No business writes
- No new frontend app
- No new login or session system
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No browser analytics SDK
- No AI attribution or AI-written dashboard copy

## Future Work
- Saved operator filter presets
- Richer time-series controls and comparisons
- Per-share or per-alias drilldown filters if later justified
- Still no source-file sharing by default
