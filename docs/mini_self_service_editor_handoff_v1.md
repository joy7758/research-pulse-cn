# Mini Self-Service Editor Handoff v1

## Why A Handoff Grant Is Added Instead Of Making Mini Directly Editable
- Mini read grants are intentionally narrow and remain read-only in this phase.
- The editor handoff grant creates a short-lived bridge from mini reserve to the existing editor reserve without turning mini auth into a write surface.
- This keeps long-lived user-side editing authority on `SubscriptionSelfServiceGrant` while allowing future mobile or WebView shells to enter the editor safely.

## SubscriptionEditorHandoffGrant Model
- `SubscriptionEditorHandoffGrant` is a derived short-lived token model for `/subscription-editor/*`.
- Key fields:
  - `user_id`
  - `channel`
  - `mini_grant_id`
  - `self_service_grant_id`
  - `binding_id`
  - `token_hash`
  - `status`
  - `display_label`
  - `issued_by`
  - `issued_by_admin_id`
  - `expires_at`
  - `last_used_at`
  - timestamps
- Plaintext tokens are returned only once when the handoff grant is created.
- Only token hashes are stored at rest.

## Mini Handoff Create And Status Flow
- Mini-protected endpoints in this phase:
  - `POST /mini/subscription-reserve/editor-handoff`
  - `GET /mini/subscription-reserve/editor-handoff-status`
- Mini can create a handoff grant only when:
  - `APP_SUBSCRIPTION_EDITOR_HANDOFF_ENABLED=true`
  - a qualifying self-service grant exists for the same user and `official_account`
  - an official-account binding exists when binding is required by settings
- The create response returns:
  - safe handoff grant summary
  - plaintext handoff token once
  - expiry
  - supported editor endpoints
  - notes
- The status response returns:
  - latest active or recent handoff summary
  - linked self-service grant summary
  - linked binding summary

## Handoff-Grant Auth Boundary
- Handoff grant auth is distinct from:
  - admin JWT auth
  - internal service auth
  - sync device-token auth
  - mini read auth
  - long-lived self-service grant auth
- Handoff grants are valid only on:
  - `GET /subscription-editor/bootstrap`
  - `GET /subscription-editor/contract`
  - `POST /subscription-editor/settings/preview`
  - `PATCH /subscription-editor/settings`
- Handoff grants are rejected on:
  - `/mini/*`
  - `/subscription-self-service/*`
  - `/admin/*`
  - `/ops/*`
  - `/sync/*`
  - business CRUD routes

## Reused Editor Contract Bootstrap Preview And Save Flows
- The new `/subscription-editor/*` route family reuses the same underlying editor logic already used by:
  - `GET /subscription-self-service/editor-bootstrap`
  - `GET /subscription-self-service/editor-contract`
  - `POST /subscription-self-service/settings/preview`
  - `PATCH /subscription-self-service/settings`
- Supported editable fields stay identical:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- Preview remains authoritative and non-persistent.
- Save still preserves unknown existing `SubscriptionPolicy.policy` keys.

## Safe Summary Model
- Safe handoff grant summaries expose:
  - `id`
  - `user_id`
  - `channel`
  - `binding_id`
  - `mini_grant_id`
  - `self_service_grant_id`
  - `status`
  - `display_label`
  - `issued_by`
  - `expires_at`
  - `last_used_at`
  - timestamps
- Safe linked self-service summaries expose:
  - `id`
  - `channel`
  - `binding_id`
  - `status`
  - `display_label`
  - `expires_at`
  - `last_used_at`
  - `created_at`
- Safe binding summaries still exclude:
  - `openid`
  - `unionid`
  - raw provider payloads
  - secrets
  - plaintext tokens except at creation time

## Current Non-Goals
- new delivery channels
- real mini editing UI
- full browser/web shell polish beyond the thin testable shell
- desktop UI work
- generic user login/session system
- campaign or broadcast behavior

## Future Work
- real mini editing UI on top of the current handoff contract
- tighter handoff into the current `apps/subscription-editor-web` shell
- richer mobile self-service UX
- optional direct OAuth-backed editor handoff
- unified user self-service surface if it is ever justified
