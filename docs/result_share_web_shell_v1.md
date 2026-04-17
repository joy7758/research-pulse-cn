# Result Share Web Shell v1

## Why A Public Read-Only Web Shell Is Added After Result-Sharing Boundary Exists
- Phase 37 already established the backend-only boundary for safe structured result sharing.
- This phase turns those opaque share tokens into a browser-openable surface that can be demoed and forwarded.
- The shell stays strictly read-only:
  - no login
  - no editing
  - no source-file access

## Token Bootstrap Flow
- The shell lives under `apps/result-share-web`.
- It accepts raw share tokens from:
  - `/share/<token>` pathnames
  - `?share_token=...` query fallback
  - `#share_token=...` fragment fallback
  - manual paste
- It also accepts opaque share aliases from:
  - `/share-alias/<alias>` pathnames
  - `?share_alias=...` query fallback
  - `#share_alias=...` fragment fallback
  - manual paste
- It also accepts an optional self-service token from:
  - manual paste
  - local-dev `?self_service_token=...` query fallback
  - local-dev `#self_service_token=...` fragment fallback
- Query and fragment tokens or aliases are moved into in-memory state and immediately cleared from the visible URL.
- The shell then calls:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - `POST /subscription-self-service/result-shares/{share_token}/collect`
  - `GET /subscription-self-service/share-aliases/{alias}/collect-preview`
  - `POST /subscription-self-service/share-aliases/{alias}/collect`
  - `GET /subscription-self-service/workspace-result-collections`
- The backend may also record internal-only analytics events for:
  - `bootstrap_view`
  - `content_view`
  - `redirect`
  - `invite_handoff_redirect`
  - `collect_handoff_redirect`
  without adding browser trackers or changing the shell contract.

## Read-Only Result Types
- Supported share kinds in v1:
  - `digest_issue`
  - `paper_snapshot`
  - `workspace_board`
- The shell renders only structured read models already exposed by the backend.
- The shell does not derive new business logic or reconstruct hidden data.

## Collect Flow Overlay
- Public share rendering remains read-only and token-based.
- A separate self-service token may be connected in memory only for:
  - collect-preview
  - explicit manual collect
  - current workspace-result-collection history
- `paper_snapshot`
  - exposes one collectable paper summary
  - can collect without paper selection
- `digest_issue`
  - may expose multiple collectable paper summaries
  - requires explicit paper selection when more than one collectable paper is present
- `workspace_board`
  - remains non-collectable in v1
  - may also surface invite/join and result-collect handoff summaries
- Alias mode stays additive over the same underlying `ResultShareGrant` semantics and never reveals the raw share token.
- The shell keeps the current share view intact while collect actions run in parallel panels.
- Any analytics reserve remains backend-only and does not change shell state handling or token storage rules.

## Workspace-Board Invite Handoff Summary
- `workspace_board` share pages now also surface a manual invite/join handoff summary.
- That summary is informational only:
  - the page remains read-only
  - joining requires a separate invite token
  - self-service claim stays in the separate invite flow
  - source files remain excluded
- When configured, the shell may also show an `Open invite entry` CTA that points to a backend redirect boundary instead of linking directly to the invite shell entry URL.
- When configured, the shell may show an invite entry URL hint that points only to the invite shell entry page and never carries a token.

## Workspace-Board Result Collect Handoff Summary
- `workspace_board` share pages may also surface a manual result-collect handoff summary.
- That summary is informational only:
  - the page remains read-only
  - collecting papers requires a separate `digest_issue` or `paper_snapshot` share token
  - collect stays in the separate result-share plus self-service flow
  - source files remain excluded
- When configured, the shell may show an `Open result collect entry` CTA that points to a backend redirect boundary instead of linking directly to the raw result-share shell entry URL.
- When configured, the shell may show a result-share entry URL hint that points only to the existing result-share shell entry page and never carries a token.

## Structured Digest Rendering Vs Fallback Behavior
- `digest_issue` share pages prefer:
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
- If older digest rows only expose legacy compatibility fields, the shell deterministically falls back to:
  - `highlights`
  - `items`
- Fallback sections still render in the stable public order:
  1. `today_focus`
  2. `yesterday_recap`
  3. `signal_updates`
  4. `related_papers`
  5. `other_updates`

## Safety Exclusions
- This shell does not expose:
  - source files or PDFs
  - local attachment paths
  - local note contents
  - local reviewer-matrix drafts
  - openid / unionid
  - provider secrets
- Internal deep links are treated as informational unless they are already safe external URLs in backend payloads.

## Current Non-Goals
- source-file or attachment sharing
- local note-file or note-content sharing
- editing through share pages
- desktop UI or mini UI work
- campaign or referral behavior
- generic user login/session system

## Future Work
- mini handoff into collect flow
- richer workspace selection UX
- later explicit source-file opt-in flows
- workspace curation improvements

The internal admin/operator shell for creating and revoking `workspace_board` shares now lives separately under `apps/group-workspace-admin-web`, so this public shell stays strictly read-only.
Workspace invite bootstrap and self-service claim now also have their own separate thin shell under `apps/group-workspace-invite-web`, so result sharing and membership growth remain distinct browser surfaces.
