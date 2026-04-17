# Group Workspace Conversion Overview Reserve V1

## Why An Aggregate Overview Is Added After Share/Invite/Collect Bridge Layers Exist
- The repository already persists share-view events, invite claims, and result-collect records.
- This phase adds an internal aggregate read model so operators can read one summary of:
  - public share views
  - invite handoff redirects
  - collect handoff redirects
  - invite claim outcomes
  - result collect outcomes
- The overview is admin read-only and stays outside public share, invite, and self-service write boundaries.

## Global Vs Workspace-Level Overview Semantics
- `GET /admin/group-workspace-conversion-overview` returns a windowed internal summary across persisted records.
- `GET /admin/group-workspaces/{workspace_id}/conversion-overview` returns the same family of signals narrowed to one workspace.
- Global overview is useful for cross-workspace movement and total activity.
- Workspace overview is useful for one workspace's active board shares, invite grants, claims, and collect records.

## Direct Vs Aggregate-Only Attribution Boundaries
- `ResultShareViewEvent` metrics are directly attributed because the event already stores:
  - `result_share_grant_id`
  - `result_share_alias_id`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `handoff_target_kind`
- `GroupWorkspaceResultCollectRecord` metrics are directly linked when `result_share_grant_id` is present.
- `GroupWorkspaceInviteClaim` metrics are workspace-level aggregate signals in v1:
  - they are not treated as exact per-share causal attribution
  - they are grouped by workspace and time window only
- The overview does not attempt probabilistic or AI-based attribution.

## Safe Data Model
- The overview uses only persisted internal records:
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
  - no local filesystem paths
  - no local note contents
  - no local attachment paths
  - no source file contents

## Current Non-Goals
- No new public endpoints or frontend apps
- No source-file sharing
- No generic login system
- No third-party analytics SDK
- No AI conversion scoring or attribution copy

## Future Work
- Internal read-only dashboard UI in the admin shell
- Richer workspace drilldown and trend slices
- Stronger attribution only if later justified by real persisted links
- Still no source-file sharing by default

The first consumer of these read models is now the existing internal `apps/group-workspace-admin-web` shell, which renders:

- a global conversion overview panel
- a workspace conversion overview block inside workspace detail
- direct-vs-aggregate attribution notes without adding new write flows
