# Mini Structured Today And Subscription Reserve v1

## Why Mini Stays Read-Only While Self-Service Reserve Is Added
- The mini surface is now allowed to read more authoritative digest and subscription state, but it still does not own any write path.
- This keeps mini grant auth narrow while the separate self-service grant boundary handles future user-side editing.
- Real WeChat OAuth and real mini login remain out of scope in this phase.

## Structured Digest Rendering In Mini
- `GET /mini/today` and `GET /mini/digest-issues/{digest_issue_id}` now prefer the orchestrated digest structure when present:
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
- Supported section kinds:
  - `today_focus`
  - `yesterday_recap`
  - `signal_updates`
  - `related_papers`
  - `other_updates`
- `source_paper_id = null` is supported for items such as `yesterday_summary`.

## Fallback Behavior For Older Digests
- If a cached digest only has legacy `highlights` / `items`, mini derives a compatible read-only section view locally.
- The fallback stays deterministic:
  - `today_suggestion`, `next_action`, `stalled_progress`, `deadline_risk` -> `today_focus`
  - `yesterday_summary` -> `yesterday_recap`
  - `signal_change` -> `signal_updates`
  - `related_paper` -> `related_papers`
  - everything else -> `other_updates`
- Missing structured fields do not crash mini responses.

## Mini Subscription Reserve Endpoint
- `GET /mini/subscription-reserve` is the new read-only reserve endpoint for mini grants.
- It returns:
  - safe user summary
  - safe current mini grant summary
  - safe official-account binding summary if available
  - current official-account subscription settings summary
  - authoritative delivery-control preview summary
  - latest digest issue summary when available
  - `self_service_reserve` informational block
  - `self_service_entry` handoff block for future editor clients
  - `binding_handoff_reserve` informational block
  - `editor_handoff_reserve` informational block for future editor-token minting
  - `workspace_invite_reserve` informational block for future invite-join handoff
- Safe binding summary excludes:
  - `openid`
  - `unionid`
  - raw provider payloads
  - secrets

## Authoritative Preview Vs Desktop Local Hint Vs Self-Service Edit Boundary
- Mini delivery preview is authoritative because it reuses the backend delivery-control evaluator.
- Desktop Settings still shows a local-only hint derived from cached policy data.
- Self-service grant endpoints remain the only future-safe place for user-side edits.
- `self_service_entry` now makes the next-step editor boundary explicit:
  - editor contract is available
  - preview-before-save is available
  - mini grant still cannot call either endpoint
- Mini grant auth does not become valid on `/subscription-self-service/*`, and self-service grant auth does not become valid on `/mini/*`.
- `binding_handoff_reserve` now makes the next-step boundary explicit:
  - mini grant cannot initiate or complete binding handoff
  - a separate self-service grant is still required
  - `oauth_enabled` may now reflect real backend OAuth capability, but mini still stays read-only
- `editor_handoff_reserve` now makes the editor bridge explicit:
  - mini grant still cannot call editor endpoints directly
  - a short-lived handoff grant is required
  - future mini or WebView clients can mint that token through mini reserve without replacing self-service grant auth
- `workspace_invite_reserve` now makes the membership-join bridge explicit:
  - mini grant still cannot claim workspace membership directly
  - a separate self-service grant is required
  - invite claim remains self-service-only in this phase

## Current Non-Goals
- real WeChat OAuth or mini session exchange
- mini write/update actions
- new delivery channels
- campaign or broadcast logic
- desktop work

## Future Work
- real WeChat auth and binding handoff
- mini self-service editing with a separate grant exchange
- richer issue history browsing
- later mobile notification UX
