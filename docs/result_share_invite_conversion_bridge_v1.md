# Result Share Invite Conversion Bridge v1

## Why An Observable Bridge Is Added Before A True Integrated Share-To-Join Flow
- `workspace_board` shares already expose a safe read-only workspace summary.
- The repository already has a separate invite/join reserve and a separate invite shell entry.
- This phase adds only a redirect bridge plus aggregate observation so the share page can point users toward invite/join without mixing share auth and invite auth.

## Invite Handoff Redirect Semantics
- New public redirect routes:
  - `GET /result-shares/{share_token}/invite-handoff`
  - `GET /share-aliases/{alias}/invite-handoff`
- In v1 they are allowed only for `workspace_board` shares.
- They validate the share normally, then redirect to the configured invite shell entry.
- They never perform invite claim directly.

## Redirect Safety Rules
- Redirect targets never include:
  - raw share tokens
  - raw aliases
  - self-service tokens
  - invite tokens
- The redirect may append only a non-sensitive context hint such as `from=workspace_board_share`.
- If invite handoff is disabled or the invite shell entry URL is missing, the redirect fails cleanly.

## Analytics Reuse Via ResultShareViewEvent
- This phase reuses `ResultShareViewEvent` instead of introducing a new analytics stack.
- `invite_handoff_redirect` is recorded as a new `event_type`.
- Access mode still reflects how the share was opened:
  - `share_token`
  - `alias`
- Optional `handoff_target_kind` may be recorded as `group_workspace_invite_entry`.
- Analytics capture remains privacy-aware:
  - no raw IP storage
  - no full referrer URL storage
  - no raw full user-agent storage
  - analytics failures must not block the redirect
- These redirect events now also feed admin-only aggregate conversion overview reads; invite-claim outcomes remain workspace-level aggregates instead of strict per-share attribution in v1.
- The first operator-facing consumer of those aggregates is the existing internal `apps/group-workspace-admin-web` shell.

## Bootstrap Handoff URL Enrichment
- `workspace_board` share bootstrap now extends `workspace_invite_handoff_reserve` with:
  - `handoff_redirect_supported`
  - `invite_handoff_url`
- `invite_handoff_url` points to the new public redirect endpoint when available.
- When redirect support is unavailable, `invite_handoff_url` remains `null`.

## Current Non-Goals
- direct invite claim from share pages
- generic login/session behavior
- source-file or PDF sharing
- local attachment or note sharing
- new browser tracking scripts
- mini or desktop invite UX

## Future Work
- true integrated share-to-invite UX
- aggregate conversion dashboards
- later board-to-join onboarding polish
- still no source-file sharing by default
