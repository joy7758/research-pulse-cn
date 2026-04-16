## Why An Internal User Workbench Shell Is Added After Core User Paper Watch-Profile Data Exists

The backend already stores stable structured data for:

- `UserProfile`
- `PaperProfile`
- `ResearchWatchProfile`
- digest issues and group-workspace membership links

This phase adds a thin internal browser shell so support and operator workflows can navigate those relationships quickly without introducing any new end-user login surface or file-sharing behavior.

## Token Bootstrap Flow

The shell accepts an admin bearer token through:

- manual paste
- optional `#admin_bearer=...` fragment ingestion
- optional `?admin_bearer=...` query ingestion for local/dev use

When a token is sourced from the URL, the shell moves it into in-memory state and clears the visible URL via `history.replaceState`. The token is never persisted to:

- `localStorage`
- `sessionStorage`
- cookies

The API base URL comes from:

- `VITE_USER_WORKBENCH_ADMIN_API_BASE_URL`
- an optional manual override input for local development

## Supported Drilldown Paths

The shell stays read-only and supports:

- user search/list
- user detail
- paper search/detail
- watch-profile explorer

Supported navigation paths in v1:

- user -> papers
- user -> watch profiles
- paper -> watch profiles
- watch profile -> linked user or paper

## Safe Data Model

The workbench consumes safe admin read models only. Typical fields include:

- user summary counts
- latest digest issue summary
- paper priority / stage / venue / next action
- watch profile label / enabled / source mode / topics / keywords / venues / authors_of_interest
- workspace membership summaries

The shell explicitly excludes:

- openid / unionid
- provider secrets
- raw callback payloads
- local filesystem paths
- local note contents
- local attachment paths
- source file contents

## Current Non-Goals

This phase does not add:

- business writes for users, papers, or watch profiles
- source-file sharing
- mini UI
- desktop UI
- AI search, ranking, or recommendations
- live collaboration
- end-user login or editing

## Future Work

- richer support tooling and saved filters
- safe edit affordances if ever justified
- cross-linking to group workspaces and result shares
- later unified internal operator console if justified
