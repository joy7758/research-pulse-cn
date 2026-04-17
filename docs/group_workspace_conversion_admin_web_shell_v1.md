# Group Workspace Conversion Admin Web Shell v1

## Why An Internal Admin Dashboard Shell Is Added After Conversion Reserve Exists
- Phase 52 already added persisted aggregate read models for share, handoff, invite-claim, and collect signals.
- This phase adds a thin read-only browser shell so operators can inspect those aggregates without introducing a new app or any write flow.
- The shell stays inside the existing admin bearer-token boundary and reuses the existing `apps/group-workspace-admin-web`.

## Global Vs Workspace Overview Rendering
- Global dashboard reads `GET /admin/group-workspace-conversion-overview`.
- Workspace dashboard reads `GET /admin/group-workspaces/{workspace_id}/conversion-overview`.
- The shell renders:
  - top-level numeric cards
  - grouped count sections
  - attribution notes
  - safe window and last-activity metadata

## Direct Vs Aggregate Attribution Notes
- The shell shows attribution notes from backend read models instead of inventing new conversion claims.
- Direct view/handoff signals remain clearly separated from workspace-level aggregate invite signals.
- The dashboard does not attempt AI attribution, probabilistic matching, or conversion copywriting.

## Safe Data Model
- The dashboard consumes only existing admin-safe read models.
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

## Current Non-Goals
- No business writes
- No new frontend app
- No generic login/session system
- No source-file sharing
- No browser tracker or third-party analytics SDK
- No AI attribution or operator-facing narrative copy

## Future Work
- Richer operator dashboard layout and filtering
- Time-series slices when they are justified
- Drilldown panels backed by the separate conversion-drilldown reserve now live in the same admin shell and should stay read-only
- Share-grant-level drilldown if later needed
- Still no source-file sharing by default
