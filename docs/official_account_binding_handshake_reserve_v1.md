# Official Account Binding Handshake Reserve v1

## Why Binding Handshake Reserve Is Added Before Real OAuth Completion
- The system already has three separate evidence/control layers:
  - provider callback ingress through `OfficialAccountCallbackEvent`
  - admin-managed `WeChatIdentityBinding`
  - user-scoped `SubscriptionSelfServiceGrant`
- This phase adds a reserve handshake boundary before real WeChat OAuth so the repository can:
  - issue a limited handshake session
  - reconcile unmatched callback evidence safely
  - claim a callback into a binding explicitly
  - expose future-facing handoff summaries without creating login state
- Real OAuth completion is now layered on top of this reserve in `docs/official_account_oauth_completion_v1.md`.
- This document still focuses on the reserve/session/reconciliation boundary itself.

## OfficialAccountBindingHandshakeSession Model
- `OfficialAccountBindingHandshakeSession` is the reserve object for future user-side official-account binding handoff.
- Key fields:
  - `user_id`
  - `channel`
  - `app_id`
  - `display_label`
  - `self_service_grant_id`
  - `issued_by_admin_id`
  - `state_token_hash`
  - `status`
  - `matched_callback_event_id`
  - `claimed_binding_id`
  - `expires_at`
  - `last_viewed_at`
  - `matched_at`
  - `claimed_at`
  - timestamps
- Plaintext state tokens are returned only once at session creation time.
- Only hashed state tokens are stored at rest.
- Session statuses in v1:
  - `pending`
  - `matched`
  - `claimed`
  - `expired`
  - `cancelled`
  - `failed`
  - `conflicted`

## Reconciliation Candidate Rules
- Reconciliation candidates come only from persisted `OfficialAccountCallbackEvent` rows.
- Safe candidate rules in v1:
  - `app_id` matches the requested app
  - `from_openid` is present
  - `linked_binding_id` is null
  - `processing_status` is in `accepted` or `processed`
  - `event_type = subscribe`
  - event falls inside the configured lookback window
  - when `APP_OFFICIAL_ACCOUNT_BINDING_REQUIRE_SIGNATURE_VALID=true`, `signature_valid` must be true
- Admin candidate responses use `masked_openid` only and do not expose raw `openid`.

## Admin Claim Flow
- Admin/operator endpoints:
  - `GET /admin/official-account-binding-handshake-sessions`
  - `POST /admin/official-account-binding-handshake-sessions`
  - `GET /admin/official-account-binding-handshake-sessions/{session_id}`
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/cancel`
  - `GET /admin/official-account-binding-reconciliation/candidates`
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/claim`
- Claim remains explicit in v1:
  1. validate the session state
  2. validate callback-event eligibility
  3. reuse an existing binding when the same user already owns the same `app_id + openid`
  4. fail cleanly on cross-user conflict
  5. otherwise create a new `WeChatIdentityBinding`
  6. link the callback event and session to the claimed binding
- Unknown subscribe callbacks are now preserved as claimable evidence instead of auto-creating bindings.

## Self-Service Handshake Reserve Endpoints
- Self-service grant auth stays separate from admin and mini auth.
- New self-service reserve endpoints:
  - `GET /subscription-self-service/wechat-binding-reserve/bootstrap`
  - `POST /subscription-self-service/wechat-binding-reserve/session`
  - `GET /subscription-self-service/wechat-binding-reserve/session`
  - `POST /subscription-self-service/wechat-binding-reserve/session/cancel`
- Self-service can:
  - bootstrap current reserve state
  - create a handshake session
  - read its own current session
  - cancel its own current session
  - start OAuth and inspect safe OAuth status through dedicated self-service endpoints
- Self-service cannot claim a binding in this phase.

## Mini Handoff Reserve Summary
- `GET /mini/subscription-reserve` now also includes a compact `binding_handoff_reserve` block.
- This block is read-only and informational only.
- Fields:
  - `supported`
  - `oauth_enabled`
  - `active_session_status`
  - `separate_self_service_grant_required`
  - `notes`
- Mini still cannot create or cancel handshake sessions in this phase.

## Auth-Boundary Separation
- Admin/operator auth can manage sessions, candidate listing, and claim.
- Self-service grant auth can access only `/subscription-self-service/wechat-binding-reserve/*`.
- Mini grant auth can access only `/mini/*`, including the read-only handoff summary.
- Raw callback/provider ingress remains separate from both admin and user-facing reserve boundaries.
- No token from one boundary becomes valid on another boundary in this phase.

## Current Non-Goals
- real WeChat Official Account OAuth redirect flow
- real code exchange or token exchange
- real mini login/session exchange
- automatic binding creation from unmatched callback events
- desktop UI work
- campaign or broadcast behavior

## Future Work
- real WeChat OAuth redirect and code exchange
- automatic post-auth handshake completion
- mini-based handoff completion
- later user-facing binding self-service UI
