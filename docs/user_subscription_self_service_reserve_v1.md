# User Subscription Self-Service Reserve v1

## Why Self-Service Reserve Is Added Before Real WeChat OAuth
- The system already has:
  - admin-managed `SubscriptionPolicy`
  - official-account digest orchestration and dispatch
  - user-side delivery-control evaluation
- This phase adds a narrow self-service boundary before real WeChat OAuth:
  - admin-issued grant token
  - safe read/update access to official-account subscription settings
  - authoritative delivery-control preview
- The goal is to harden data and interface boundaries first without mixing them with provider login flows.

## SubscriptionSelfServiceGrant Model
- `SubscriptionSelfServiceGrant` is the dedicated auth object for `/subscription-self-service/*`.
- Key fields:
  - `user_id`
  - `binding_id`
  - `channel`
  - `grant_scope`
  - `token_hash`
  - `status`
  - `display_label`
  - `issued_by_admin_id`
  - `expires_at`
  - `last_used_at`
  - timestamps
- Plaintext tokens are returned only once at grant creation time.
- Only token hashes are stored at rest.

## Self-Service Auth Boundary
- Self-service grant tokens are separate from:
  - admin auth
  - internal service auth
  - sync device-token auth
  - mini read auth
- Tokens are valid only on:
  - `GET /subscription-self-service/bootstrap`
  - `GET /subscription-self-service/settings`
  - `PATCH /subscription-self-service/settings`
  - `GET /subscription-self-service/delivery-control-preview`
  - `GET /subscription-self-service/wechat-binding-reserve/bootstrap`
  - `POST /subscription-self-service/wechat-binding-reserve/session`
  - `GET /subscription-self-service/wechat-binding-reserve/session`
  - `POST /subscription-self-service/wechat-binding-reserve/session/cancel`
  - `POST /subscription-self-service/wechat-binding-reserve/oauth-start`
  - `GET /subscription-self-service/wechat-binding-reserve/oauth-status`
- Tokens are rejected on:
  - `/admin/*`
  - `/ops/*`
  - `/sync/*`
  - `/mini/*`
  - business CRUD routes

## Supported Editable Policy Fields
- Self-service still reuses `SubscriptionPolicy` as the source of truth.
- Supported editable fields in v1:
  - `enabled`
  - `quiet_hours`
  - `policy.timezone`
  - `policy.allowed_weekdays`
  - `policy.muted_until`
  - `policy.minimum_selected_cards`
  - `policy.skip_if_no_today_focus`
- Self-service cannot change:
  - `channel`
  - `user_id`
  - binding identity
  - provider settings
  - other admin-only fields
- Unknown existing `policy` keys are preserved when patching the supported subset.

## Bootstrap, Settings, And Preview Endpoints
- Admin grant management:
  - `GET /admin/subscription-self-service-grants`
  - `POST /admin/subscription-self-service-grants`
  - `POST /admin/subscription-self-service-grants/{grant_id}/revoke`
- Self-service endpoints:
  - `GET /subscription-self-service/bootstrap`
  - `GET /subscription-self-service/settings`
  - `PATCH /subscription-self-service/settings`
  - `GET /subscription-self-service/delivery-control-preview`
  - `GET /subscription-self-service/editor-bootstrap`
  - `GET /subscription-self-service/editor-contract`
  - `POST /subscription-self-service/settings/preview`
  - `GET /subscription-self-service/wechat-binding-reserve/bootstrap`
  - `POST /subscription-self-service/wechat-binding-reserve/session`
  - `GET /subscription-self-service/wechat-binding-reserve/session`
  - `POST /subscription-self-service/wechat-binding-reserve/session/cancel`
  - `POST /subscription-self-service/wechat-binding-reserve/oauth-start`
  - `GET /subscription-self-service/wechat-binding-reserve/oauth-status`
- `bootstrap` returns:
  - safe grant summary
  - safe user summary
  - safe binding summary when linked
  - current official-account subscription settings
  - latest digest issue summary when available
- A later editor-reserve layer can now sit on top of the same grant boundary:
  - machine-readable field/section contract
  - authoritative preview-before-save
  - structured save result for future mobile/web editing pages
- The handshake-reserve sub-boundary is still read-limited for self-service:
  - self-service can create/read/cancel its own reserve session
  - self-service can issue an official-account authorize URL and inspect safe OAuth progress
  - self-service cannot claim a callback event into a binding
  - admin claim remains explicit in v1

## Authoritative Preview Vs Desktop Local Hint Distinction
- `/subscription-self-service/delivery-control-preview` uses the backend delivery-control evaluator and is authoritative for current backend state.
- Desktop Settings local hints remain best-effort and cache-based only.
- Mini read-only subscription reserve may now also expose an authoritative preview, but mini grant auth still cannot patch settings.
- Mini read-only reserve may now also expose a `self_service_entry` handoff summary so future clients know editor contract and preview APIs exist without gaining edit rights.
- Future binding handoff also stays separate:
  - self-service handshake reserve can show active reserve state
  - self-service OAuth start/status can drive real webpage authorization completion
  - mini only gets an informational handoff summary
  - mini still does not implement real OAuth completion itself
- The authoritative preview does not create `DigestDeliveryDecision` rows in this phase.

## Current Non-Goals
- real WeChat Official Account OAuth
- real Mini Program auth/session exchange
- new delivery channels
- automatic WeChat binding creation
- desktop UI work
- richer user portal flows

## Future Work
- real WeChat auth and binding handoff
- mini-program self-service UI
- user-facing snooze actions
- richer preference controls
