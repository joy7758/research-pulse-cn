## Why An Internal Admin Operator Shell Is Added After Workspace Share Backend Exists

Phase 37 established the backend boundary for admin-managed group workspaces and read-only result sharing. This phase adds a thin internal browser shell so operators can exercise that boundary without introducing a generic end-user login system or any source-file sharing semantics.

The shell is intentionally narrow:

- it consumes existing admin workspace and share-grant endpoints
- it keeps admin bearer tokens only in memory
- it remains focused on structured workspace results instead of raw files
- it now sits alongside a separate read-only user workbench shell for user/paper/watch-profile drilldown, keeping workspace management concerns isolated

## Token Bootstrap Flow

The shell accepts an admin/operator bearer token through:

- manual paste into the connect form
- optional `#admin_bearer=...` fragment ingestion
- optional `?admin_bearer=...` query ingestion for local/dev use

When a token is sourced from the URL, the shell immediately moves it into in-memory React state and clears the visible URL via `history.replaceState`. The token is never persisted to:

- `localStorage`
- `sessionStorage`
- cookies

The API base URL comes from:

- `VITE_GROUP_WORKSPACE_ADMIN_API_BASE_URL`
- an optional manual override input for local development

## Supported Workspace Management Actions

The shell currently supports:

- listing `GroupWorkspace` rows
- creating workspaces with `slug`, `name`, and `description`
- updating workspace `name`, `description`, and `status`
- loading the read-only workspace board
- adding/removing `GroupWorkspaceMember`
- adding/removing `GroupWorkspacePaper`
- loading existing `workspace_board` share grants for the current workspace

For v1 usability, the shell reuses existing admin-safe reads:

- `GET /users`
- `GET /papers`

These lookups remain read-only and are used only to help operators choose user IDs and paper IDs.

## Workspace Board Share Grant UI Scope

The share-grant UI is intentionally limited to `workspace_board` grants in this phase.

Supported actions:

- list existing `workspace_board` share grants for the selected workspace
- create a new `workspace_board` share grant
- revoke an existing `workspace_board` share grant

When a share grant is created, the plaintext token is shown once with explicit copy-now messaging. After dismissal, the shell retains only safe grant metadata and never persists the token.

Digest-issue and paper-snapshot share creation remain out of scope for this shell in v1.

## Read-Only Conversion Dashboard Scope

The same shell may now also render admin-safe conversion overview reads on top of the existing workspace list/detail UI:

- `GET /admin/group-workspace-conversion-overview`
- `GET /admin/group-workspaces/{workspace_id}/conversion-overview`

The dashboard remains read-only and focuses on:

- global share / handoff / invite / collect aggregates
- per-workspace invite and collect movement
- explicit direct-vs-aggregate attribution notes from the backend

It does not add:

- new mutations
- new token types
- probabilistic attribution
- source-file semantics

The same backend reserve now also exposes deeper read-only drilldown APIs for a later shell phase:
- `GET /admin/group-workspace-conversion-drilldown`
- `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown`
- daily buckets
- recent share / invite / collect rows
- top workspaces and top result-share grants

The shell now also includes a minimal read-only drilldown consumer on top of those existing reserve endpoints:

- global drilldown under the main dashboard area
- workspace drilldown inside workspace detail
- explicit direct-attribution vs workspace-level aggregate-only notes
- compact global and workspace filter bars for `date_from`, `date_to`, `share_kind`, `access_mode`, `event_type`, `outcome`, and drilldown `limit`
- reset-to-default filtering that reuses the backend default analytics window and keeps recent rows compact
- no new write paths, auth surfaces, or source-file semantics

The same shell now also includes a minimal read-only per-share dashboard over the existing reserve:

- open one `ResultShareGrant` drilldown from the selected workspace share-grant list or by manual `grant_id`
- open one `ResultShareAlias` drilldown by manual `alias_id` or from alias rows returned by a grant drilldown
- render direct event counts grouped by access mode, event type, and outcome
- render direct collect records only on grant drilldown
- keep alias drilldown explicitly access-path scoped with no invented collect attribution
- reuse the same in-memory admin bearer-token flow and compact filter-bar pattern

The same shell now also includes a minimal read-only result-share registry layer:

- a global share-grant registry with safe scope/status/timestamp summaries
- a global alias registry with safe prefix/status/timestamp summaries
- explicit grant-to-alias relationship hints in registry rows
- quick-open actions that reuse the existing per-share drilldown panel
- stronger filter chips and stable sort controls for registry rows
- cross-link affordances such as `show aliases for this grant` and `open underlying grant`
- local-only saved views over safe registry filter/sort state, with optional safe per-share drilldown context
- optional drilldown-linked preset application so quick-opened grant/alias rows can reuse safe per-share time-window and event filters
- local-only preset JSON export/import with schema validation, merge-or-replace preview, and no backend/team preset sync
- local-only preset diagnostics, last-good backup snapshots, validation-only import preview, and safe recovery/reset actions for corrupted browser storage
- local-only preset activity history with safe action summaries, recent operations, and clear-audit controls that stay browser-local
- no new create/revoke/bulk actions in the registry itself

## Safety Exclusions

The shell must not expose or reconstruct:

- local filesystem paths
- local attachment paths
- local note contents
- PDF/source-file payloads
- source-file sharing semantics
- end-user login/session flows

The workspace board stays read-only and renders only structured workspace/member/paper summaries that already pass through backend safety filtering.

## Current Non-Goals

This phase does not add:

- source-file or attachment sharing
- live collaboration
- bulk workspace import
- digest/paper share management UI
- desktop UI
- mini UI
- campaign/referral flows
- AI-generated share copy

## Future Work

- richer internal admin UX for search, filtering presets, and validation
- user-managed workspace membership and invitation flows
- digest-issue and paper-snapshot share management UI
- richer per-share operator dashboard and comparison controls
- richer time-series charting and comparison controls if operator demand justifies it
- later invite/handoff flows if justified
