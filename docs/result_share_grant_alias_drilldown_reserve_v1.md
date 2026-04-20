# Result Share Grant Alias Drilldown Reserve v1

## Why Per-Share Drilldown Is Added After Global And Workspace Reads Exist
- Phase 54 already established global and workspace conversion overview reads over persisted share, invite, and collect records.
- Phase 55 and Phase 56 already made those aggregate reads visible and filterable inside `apps/group-workspace-admin-web`.
- This phase adds a narrower backend-only reserve for one `ResultShareGrant` or one `ResultShareAlias` so operators can inspect one access path without creating a new frontend app, a write path, or source-file semantics.

## Grant Drilldown Vs Alias Drilldown Semantics
- Grant drilldown is exposed through:
  - `GET /admin/result-share-grants/{grant_id}/conversion-drilldown`
- Alias drilldown is exposed through:
  - `GET /admin/result-share-aliases/{alias_id}/conversion-drilldown`
- Grant drilldown is the fuller per-share read:
  - safe share-grant summary
  - window start/end
  - direct event counts and grouped breakdowns
  - active alias summaries
  - recent safe event rows
  - direct collect rows and direct collect outcome counts
- Alias drilldown is intentionally narrower:
  - safe alias summary
  - underlying grant-safe summary
  - alias-scoped event counts and grouped breakdowns
  - recent safe event rows for that alias only
  - no invented alias-level collect section when persistence is only grant-linked

## Direct Event Attribution Vs Direct Collect Linkage
- Share-event metrics are direct when persisted ids are present on `ResultShareViewEvent`.
- Grant-level collect metrics are direct only when `GroupWorkspaceResultCollectRecord.result_share_grant_id` is present.
- Alias drilldown does not upgrade grant-linked collect rows into alias-level attribution.
- Notes and attribution-scope fields stay explicit so operators can distinguish:
  - direct event attribution
  - direct grant-level collect linkage
  - summary context that is not itself an attribution metric

## Safe Read Model
- The reserve reuses only existing persisted objects:
  - `ResultShareGrant`
  - `ResultShareAlias`
  - `ResultShareViewEvent`
  - `GroupWorkspaceResultCollectRecord`
- Safe outputs intentionally exclude:
  - plaintext share tokens
  - plaintext aliases
  - raw IP addresses
  - full referrer URLs
  - raw user-agent strings
  - openid and unionid values
  - local filesystem paths
  - local attachment paths
  - local note contents
  - source file contents

## Current Non-Goals
- No new frontend app
- No business writes
- No source-file, attachment, or note-file sharing
- No real-time collaboration
- No new login or auth system
- No browser analytics SDK
- No AI attribution or AI-generated analysis copy

## Future Work
- The existing `apps/group-workspace-admin-web` shell now consumes this reserve through a minimal read-only per-share dashboard plus a safe registry layer for quick-open operator flows
- Richer time-series drilldown and comparison controls
- Alias comparison views if later justified
- Still no source-file sharing by default
