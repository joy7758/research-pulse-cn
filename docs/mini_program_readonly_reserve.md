# Mini-Program Read-Only Reserve

## Why Mini-Program Access Starts Read-Only
- The backend already has protected admin, ops, sync, digest, and binding boundaries.
- A read-only mini layer lets future lightweight clients reuse stable domain data without reopening write-path design too early.
- This phase is for preview and contract hardening, not real WeChat login or frontend delivery.

## MiniReadGrant Model
- `MiniReadGrant` is the dedicated preview and landing authorization object for `/mini/*`.
- Key fields:
  - `user_id`
  - `binding_id`
  - `digest_issue_id`
  - `grant_type`
  - `token_hash`
  - `status`
  - `scope`
  - `expires_at`
  - `last_used_at`
  - `created_by_admin_id`
  - timestamps
- Plaintext tokens are returned only once at grant creation time.
- Only token hashes are stored at rest.

## Read-Only Auth Boundary
- Mini grant tokens are separate from:
  - admin JWT and refresh tokens
  - internal service token
  - sync device tokens
- Mini grant tokens are valid only on:
  - `GET /mini/bootstrap`
  - `GET /mini/today`
  - `GET /mini/digest-issues/{digest_issue_id}`
  - `GET /mini/subscription-reserve`
  - `GET /mini/papers`
  - `GET /mini/papers/{paper_id}`
- Mini grant tokens are rejected on `/admin/*`, `/ops/*`, `/sync/*`, and business CRUD routes.

## Compact Read Models And Endpoint Contracts
- `GET /mini/bootstrap`
  - returns grant context, linked user summary, stable landing path, and allowed resources
- `GET /mini/today`
  - returns the latest digest-backed overview when available
  - prefers `section_order`, `sections`, `quick_stats`, `focus_card`, and `publication_preview`
  - otherwise returns a valid empty state payload
- `GET /mini/digest-issues/{digest_issue_id}`
  - returns digest detail in stable `sort_order`
  - digest items may include internal cards such as `yesterday_summary` or `today_suggestion`
  - digest payloads now also tolerate sectioned daily-digest fields such as `section_order`, `sections`, `focus_card`, and `publication_preview`
- `GET /mini/subscription-reserve`
  - returns a safe official-account subscription summary
  - returns an authoritative delivery-control preview summary when digest context exists
  - returns a read-only `self_service_reserve` handoff block instead of any write affordance
  - now also returns a read-only `binding_handoff_reserve` block for future official-account binding handoff
  - reflects backend `oauth_enabled` status while still keeping mini fully read-only
- `GET /mini/papers`
  - returns compact paper summaries with stable ordering
- `GET /mini/papers/{paper_id}`
  - returns compact paper detail with recent progress events and recent signal snapshots

## Derived Progress Percentage Heuristic
- `progress_percentage` is a deterministic read-model helper, not workflow truth.
- Current mapping:
  - `published -> 100`
  - `revision -> 80`
  - `under_review -> 65`
  - `in_prep -> 35`
  - `paused -> 0`
- The value is derived at read time from `PaperProfile.type`.
- `PaperProfile` does not persist this field as a source-of-truth column.

## Preview And Testing Workflow
1. Operator or super admin creates a mini read grant under `/admin/mini-read-grants`.
2. The API returns a plaintext grant token once plus a preview landing path.
3. The token is used only against `/mini/*`.
4. Preview routes consume digest issues and paper summaries without calling real WeChat APIs.

## Current Non-Goals
- Real Mini Program login or code-to-session exchange
- Real Official Account API delivery
- Customer-facing write endpoints under `/mini/*`
- Binding self-service or OAuth flows
- Treating mini routes as the primary product surface today

## Future Work
- a separate subscription self-service reserve boundary that can later be linked from mini or official-account entry surfaces without exposing admin auth
- official-account provider-boundary handoff into mini landing routes
- real per-binding official-account sends that link into the same mini landing paths
- real mini-program auth and session exchange
- richer mobile read models and compact timeline views
- limited write actions only after permission and conflict rules are explicit
