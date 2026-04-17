# Result Share Analytics Reserve v1

## Why Analytics Reserve Is Added After Share And Alias Boundaries Exist
- Public result-share and alias boundaries already define how safe structured content is opened in a browser.
- This phase adds an internal-only analytics reserve so the repository can count share opens without changing public read-only semantics.
- Analytics stays additive over `ResultShareGrant` and `ResultShareAlias`; it does not replace them.

## ResultShareViewEvent Model
- `ResultShareViewEvent` stores:
  - `id`
  - `result_share_grant_id`
  - `result_share_alias_id`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `outcome`
  - `request_fingerprint_hash`
  - `referrer_host`
  - `user_agent_family`
  - `occurred_at`
  - `created_at`
- Supported access modes in v1:
  - `share_token`
  - `alias`
  - `alias_redirect`
- Supported event types in v1:
  - `bootstrap_view`
  - `content_view`
  - `redirect`
  - `invite_handoff_redirect`
  - `collect_handoff_redirect`
- Supported outcomes in v1:
  - `resolved`
  - `rejected`
- Optional handoff target in v1:
  - `group_workspace_invite_entry`
  - `result_share_collect_entry`

## Privacy-Aware Capture Rules
- No raw IP storage.
- No full referrer URL storage.
- No raw full user-agent storage.
- Referrer capture stores host only when enabled.
- User-agent capture stores only a coarse family/category when enabled.
- Fingerprint capture is optional and stores only a hash derived from coarse request properties plus optional salt.
- Analytics write failures must not block public share resolution or redirect behavior.

## Aggregate Summary Model
- Admin summary outputs include:
  - `total_events`
  - `resolved_events`
  - `rejected_events`
  - `bootstrap_view_count`
  - `content_view_count`
  - `redirect_count`
  - `invite_handoff_redirect_count`
  - `collect_handoff_redirect_count`
  - `distinct_fingerprint_count`
  - `by_share_kind`
  - `by_access_mode`
  - `by_handoff_target`
  - `last_event_at`
- Default lookback may be applied when no explicit date range is passed.

## Admin Analytics Endpoints
- Admin read routes:
  - `GET /admin/result-share-analytics/summary`
  - `GET /admin/result-share-analytics/events`
- The same persisted records now also feed aggregate conversion overview reads:
  - `GET /admin/group-workspace-conversion-overview`
  - `GET /admin/group-workspaces/{workspace_id}/conversion-overview`
- The same persisted records are now surfaced in the existing internal `apps/group-workspace-admin-web` shell as a compact read-only conversion dashboard.
- Those overview reads stay explicit about attribution boundaries:
  - view/handoff signals are direct persisted event counts
  - invite claims stay workspace-level aggregate signals in v1
  - collect records are direct only when `result_share_grant_id` is present
- These routes expose only safe event summaries:
  - no plaintext share tokens
  - no plaintext aliases
  - no raw IPs
  - no full referrer URLs
  - no raw full user-agents

## Current Non-Goals
- browser tracking SDKs
- third-party analytics scripts
- source-file or PDF analytics
- local attachment analytics
- generic user login/session analytics
- public analytics UI

## Future Work
- richer internal growth dashboard
- share conversion funnel analysis
- later alias-vs-token comparisons in UI
- still no source-file sharing by default
