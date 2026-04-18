# Result Share Grant Alias Admin Web Shell v1

## Why An Internal Per-Share Dashboard Shell Is Added After Per-Share Drilldown Reserve Exists
- Phase 57 already added admin-safe per-share drilldown reserve reads for one `ResultShareGrant` and one `ResultShareAlias`.
- This phase reuses the existing `apps/group-workspace-admin-web` shell instead of creating a new app.
- The goal is a thin operator-readable browser consumer for those reads, not a new write flow, auth surface, or source-file feature.
- A later registry phase can build on the same shell so common operator flows no longer require manual `grant_id` or `alias_id` lookup.

## Grant Drilldown Vs Alias Drilldown Rendering
- Grant drilldown renders:
  - safe share-grant summary
  - direct event counts
  - aliases list
  - recent events
  - direct collect records
  - attribution scope and notes
- Alias drilldown renders:
  - safe alias summary
  - underlying grant summary
  - alias-scoped event counts
  - recent events
  - attribution scope and notes
- Alias rows inside grant drilldown can open the corresponding alias drilldown in the same shell.

## Direct Event Attribution Vs Direct Collect Linkage
- Grant drilldown keeps direct event counts and direct collect linkage separate in the UI.
- Alias drilldown stays explicit about its narrower scope:
  - it is about access-path behavior for one alias
  - it does not invent alias-level collect attribution when persistence is only grant-linked
- The shell renders backend attribution notes directly instead of generating client-side narratives.

## Safe Data Model
- The shell consumes only existing admin-safe read models.
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
- Admin bearer tokens stay in memory only and query/fragment hints are still cleared from the visible URL immediately.

## Current Non-Goals
- No business writes in per-share panels
- No new frontend app
- No new login or session system
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No browser analytics SDK
- No AI attribution or AI-written dashboard copy

## Future Work
- Richer per-share operator dashboard and comparison flows
- Time-series per-share views when justified
- Alias comparison UI if later justified
- Still no source-file sharing by default
