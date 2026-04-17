# Result Share Collect Conversion Bridge v1

## Why An Observable Bridge Is Added Before A True Integrated Share-To-Collect Flow
- `workspace_board` shares already expose safe read-only workspace summaries.
- The repository already has a separate result collect reserve and a separate result-share shell entry.
- This phase adds only a redirect bridge plus aggregate observation so the share page can point users toward collect without mixing board-share auth and collect auth.

## Collect Handoff Redirect Semantics
- New public redirect routes:
  - `GET /result-shares/{share_token}/collect-handoff`
  - `GET /share-aliases/{alias}/collect-handoff`
- In v1 they are allowed only for `workspace_board` shares.
- They validate the share normally, then redirect to the configured result-share shell entry.
- They never perform collect directly.

## Redirect Safety Rules
- Redirect targets never include:
  - raw share tokens
  - raw aliases
  - self-service tokens
  - invite tokens
- The redirect may append only a non-sensitive context hint such as `from=workspace_board_collect_handoff`.
- If collect handoff is disabled or the result-share shell entry URL is missing, the redirect fails cleanly.

## Analytics Reuse Via ResultShareViewEvent
- This phase reuses `ResultShareViewEvent` instead of introducing a new analytics stack.
- `collect_handoff_redirect` is recorded as a new `event_type`.
- Access mode still reflects how the share was opened:
  - `share_token`
  - `alias`
- Optional `handoff_target_kind` may be recorded as `result_share_collect_entry`.
- Analytics capture remains privacy-aware:
  - no raw IP storage
  - no full referrer URL storage
  - no raw full user-agent storage
  - analytics failures must not block the redirect
- These redirect events now also feed admin-only aggregate conversion overview reads; collect counts remain direct only when `GroupWorkspaceResultCollectRecord.result_share_grant_id` is present.

## Bootstrap Handoff URL Enrichment
- `workspace_board` share bootstrap now extends `result_collect_handoff_reserve` with:
  - `handoff_redirect_supported`
  - `collect_handoff_url`
- `collect_handoff_url` points to the new public redirect endpoint when available.
- When redirect support is unavailable, `collect_handoff_url` remains `null`.

## Current Non-Goals
- direct collect from share pages
- generic login/session behavior
- source-file or PDF sharing
- local attachment or note sharing
- new browser tracking scripts
- mini or desktop collect UX

## Future Work
- true integrated board-to-collect UX
- aggregate collect conversion dashboards
- later board-to-collect onboarding polish
- still no source-file sharing by default
