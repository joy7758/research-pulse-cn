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
- Safe binding summary excludes:
  - `openid`
  - `unionid`
  - raw provider payloads
  - secrets

## Authoritative Preview Vs Desktop Local Hint Vs Self-Service Edit Boundary
- Mini delivery preview is authoritative because it reuses the backend delivery-control evaluator.
- Desktop Settings still shows a local-only hint derived from cached policy data.
- Self-service grant endpoints remain the only future-safe place for user-side edits.
- Mini grant auth does not become valid on `/subscription-self-service/*`, and self-service grant auth does not become valid on `/mini/*`.

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
