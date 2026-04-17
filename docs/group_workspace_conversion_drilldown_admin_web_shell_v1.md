# Group Workspace Conversion Drilldown Admin Web Shell v1

## Why An Internal Drilldown Shell Is Added After Drilldown Reserve Exists
- Phase 54 already added persisted drilldown read models and admin-safe endpoints for daily buckets, recent activity, and top entities.
- This phase adds the thinnest practical browser consumer for those reads inside the existing `apps/group-workspace-admin-web`.
- The goal is operator visibility over the reserve, not a new product surface, write flow, or source-file feature.

## Global Vs Workspace Drilldown Rendering
- Global drilldown reads `GET /admin/group-workspace-conversion-drilldown`.
- Workspace drilldown reads `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown`.
- The same shell now renders:
  - a global drilldown panel alongside the existing global overview
  - a workspace drilldown panel inside workspace detail alongside the existing workspace overview
- Both drilldown surfaces now sit behind the same compact read-only filter controls used by overview:
  - `date_from`
  - `date_to`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `outcome`
  - `limit` for recent/top sections
- Both panels stay read-only and reuse the same in-memory admin bearer-token boot flow.

## Daily Buckets, Recent Activity, And Top Lists
- Daily buckets render as compact read-only tables over the returned `daily_buckets`.
- Recent activity renders as small operator-readable lists for:
  - `recent_share_events`
  - `recent_invite_claims`
  - `recent_collect_records`
- Global drilldown also renders:
  - `top_workspaces`
  - `top_result_share_grants`
- Workspace drilldown also renders:
  - `active_share_grant_snapshot`
  - `active_invite_grant_snapshot`

## Direct Vs Aggregate Attribution Notes
- The shell surfaces backend attribution scope directly instead of inventing client-side narratives.
- Direct attribution remains limited to rows where persisted share or collect links exist.
- Workspace invite claims stay clearly labeled as workspace-level aggregate-only signals in v1.
- Drilldown notes and attribution notes are shown in separate blocks so operators can distinguish data shape from interpretation limits.

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
- The app keeps admin bearer tokens in memory only and still clears query or fragment token hints from the visible URL immediately.

## Current Non-Goals
- No business writes in drilldown panels
- No new frontend app
- No new login or session system
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No browser analytics SDK
- No AI attribution or AI-written dashboard copy

## Future Work
- Saved filter presets and richer comparison controls
- Time-series charting when it becomes justified
- Share-grant drilldown UI if later operator usage warrants it
- Still no source-file sharing by default
