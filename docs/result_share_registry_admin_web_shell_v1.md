# Result Share Registry Admin Web Shell v1

## Why An Internal Share Alias Registry Shell Is Added After Per-Share Drilldown Exists
- Phase 57 already added admin-safe per-share drilldown reserve reads for one `ResultShareGrant` and one `ResultShareAlias`.
- Phase 58 already made those reads visible inside the existing `apps/group-workspace-admin-web` shell.
- This phase removes the common operator need to paste `grant_id` or `alias_id` manually for every inspection flow.
- The goal is still a thin internal read-only browser consumer, not a new write surface, auth boundary, or source-file feature.

## Grant Registry Vs Alias Registry Rendering
- The shell now renders a global share-grant registry with:
  - safe grant summary
  - share kind and status
  - workspace / digest / paper scope hints
  - last-used and expiry timestamps
  - linked alias counts
  - quick open grant drilldown
- The shell now also renders a global alias registry with:
  - safe alias summary
  - alias prefix
  - linked grant summary
  - last-used and expiry timestamps
  - quick open alias drilldown
  - quick open linked grant drilldown
- Grant and alias sections stay visually separate so operators can see whether they are reviewing a grant object or an alias access-path object.

## Safe Data Model
- The shell consumes only existing admin-safe list and drilldown reads.
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
- Admin bearer tokens still stay in memory only, and query / fragment token hints are still removed from the visible URL immediately.

## Quick Open Drilldown Behavior
- Registry rows do not add new business mutations.
- Opening a grant row reuses the existing read-only per-share drilldown panel inside the same admin shell.
- Opening an alias row reuses the same drilldown panel with alias-scoped reads.
- Alias rows also expose the linked grant relationship so operators can move from alias behavior back to the underlying grant when needed.
- The later filter/sort follow-up keeps this behavior and adds:
  - applied filter/sort chips
  - stable sort controls for timestamps, share kind, and status
  - a direct `show aliases for this grant` shortcut from grant rows
- Registry filters narrow safe list reads only; they do not change attribution semantics inside the downstream drilldown.

## Current Non-Goals
- No create / revoke / bulk action controls in the registry
- No new frontend app
- No new login or session system
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No browser analytics SDK
- No AI attribution or AI-written dashboard copy

## Future Work
- Saved/local filter presets on top of the stronger filter/sort shell
- Per-share comparison views across grants or aliases
- Registry-level bulk operations only if later justified
- Still no source-file sharing by default
