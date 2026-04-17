# Group Workspace Conversion Drilldown Reserve V1

## Why Drilldown Is Added After Overview Exists
- Phase 52 already established aggregate overview reads for persisted share, invite, and collect signals.
- This phase adds deeper admin-only drilldown reads so operators can inspect:
  - daily buckets
  - recent share events
  - recent invite claims
  - recent collect records
  - top workspaces
  - top result-share grants
- The drilldown stays read-only and reuses the same persisted records instead of creating a new attribution layer.

## Global Vs Workspace Drilldown Semantics
- `GET /admin/group-workspace-conversion-drilldown` returns a global windowed drilldown across persisted activity.
- `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown` returns the same family of reads narrowed to one workspace.
- Global drilldown is intended for cross-workspace operator review and ranking.
- Workspace drilldown is intended for recent activity inspection plus active grant snapshots inside one workspace.

## Direct Vs Aggregate Attribution Boundaries
- `ResultShareViewEvent` drilldown rows remain direct when persisted ids are present:
  - `result_share_grant_id`
  - `result_share_alias_id`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `handoff_target_kind`
- `GroupWorkspaceResultCollectRecord` drilldown rows remain direct when `result_share_grant_id` is present.
- `GroupWorkspaceInviteClaim` drilldown rows remain workspace-level aggregate signals in v1:
  - they are useful for recent operational review
  - they are not treated as strict per-share causal attribution
- No probabilistic, inferred, or AI-generated attribution is introduced.

## Safe Read Model
- Drilldown uses only existing persisted records:
  - `ResultShareViewEvent`
  - `ResultShareGrant`
  - `ResultShareAlias`
  - `GroupWorkspaceInviteGrant`
  - `GroupWorkspaceInviteClaim`
  - `GroupWorkspaceResultCollectRecord`
  - `GroupWorkspace`
- Safe exclusions remain in place:
  - no plaintext share tokens
  - no plaintext aliases
  - no raw IP addresses
  - no full referrer URLs
  - no raw user-agent strings
  - no openid or unionid values
  - no local filesystem paths
  - no local note contents
  - no local attachment paths
  - no source file contents

## Current Non-Goals
- No new public endpoints or frontend apps
- No source-file sharing
- No business writes
- No generic login system
- No third-party analytics SDK
- No AI attribution or analysis copy

## Future Work
- Richer operator dashboard UI for those drilldown reads
- Time-series charting if later justified
- Share-grant drilldown if later justified by operator need
- Still no source-file sharing by default
