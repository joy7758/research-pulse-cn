# Official Account OAuth Completion v1

## Why Real OAuth Completion Is Added After Handshake Reserve Exists
- The repository already had:
  - raw callback evidence through `OfficialAccountCallbackEvent`
  - explicit handshake sessions through `OfficialAccountBindingHandshakeSession`
  - self-service grant auth for narrow user-side initiation
- This phase adds real webpage OAuth completion on top of that reserve instead of turning OAuth into a generic app-login system.

## Authorize URL Issuance
- Self-service can now start OAuth through:
  - `POST /subscription-self-service/wechat-binding-reserve/oauth-start`
- Admin can issue an authorize URL for an existing session through:
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/oauth-authorize-url`
- The authorize URL is built against the official webpage authorization endpoint with:
  - `appid`
  - `redirect_uri`
  - `response_type=code`
  - `scope`
  - `state`
  - `#wechat_redirect`

## Callback Completion Flow
- Public callback endpoint:
  - `GET /integrations/wechat/official-account/oauth/callback`
- Completion steps:
  1. validate `code` and `state`
  2. find the active handshake session by hashed `state`
  3. exchange `code` server-side for OAuth identity data
  4. optionally fetch `userinfo` when scope is `snsapi_userinfo`
  5. create or reuse a `WeChatIdentityBinding`
  6. complete the handshake session safely
- By default the callback returns safe JSON.
- When success/failure redirect URLs are configured, the callback may redirect instead.

## Code Exchange And Optional Userinfo Path
- The backend exchanges `code` server-side against the official webpage OAuth token endpoint.
- Raw `access_token` and `refresh_token` are ephemeral:
  - used only in-process
  - never stored in database rows
  - never exposed through safe summaries
- `userinfo` fetch is optional and only attempted when:
  - authorized scope is `snsapi_userinfo`
  - `APP_OFFICIAL_ACCOUNT_OAUTH_FETCH_USERINFO_WHEN_SCOPE_USERINFO=true`

## Binding Create Or Reuse Rules
- Matching key:
  - `channel_type = official_account`
  - `app_id`
  - `openid`
- Rules:
  - same app, same openid, same user:
    - reuse existing binding
  - same app, same openid, different user:
    - fail cleanly with conflict
  - no existing binding:
    - create a new `WeChatIdentityBinding`
- OAuth completion still does not create a generic app login session.

## Callback Evidence Linking
- Existing subscribe callback evidence remains useful after real OAuth completion.
- If an eligible unmatched `OfficialAccountCallbackEvent` exists for the same `app_id + openid`:
  - link `linked_binding_id`
  - mark the binding `subscribed=true`
  - carry forward `subscribed_at` / `last_seen_at` from callback time when practical
- If no callback evidence exists:
  - binding creation/reuse can still succeed
  - new bindings default to `subscribed=false`

## Safe Summary Model
- Safe binding/session summaries may expose:
  - binding id
  - channel/app identifiers
  - display label
  - bind/subscription state
  - handshake status and timestamps
  - requested/authorized OAuth scope
  - hashed openid correlation on the session
- They do not expose:
  - raw `openid`
  - raw `unionid`
  - `access_token`
  - `refresh_token`
  - provider secrets

## Auth-Boundary Separation
- Admin auth:
  - session management
  - candidate reconciliation
  - explicit claim
  - OAuth status inspection
- Self-service grant auth:
  - OAuth start
  - OAuth status
  - narrow reserve/bootstrap/settings surfaces
  - future editor bootstrap/contract/preview surfaces that may reflect `oauth_enabled`
- Mini grant auth:
  - read-only `/mini/*`
  - no OAuth start or edit actions
- Public callback:
  - no admin auth
  - constrained by `code/state/session` validation only

## Current Non-Goals
- Mini Program auth/session exchange
- generic end-user login/session system
- new delivery channels
- desktop UI work
- campaign or broadcast behavior

## Future Work
- mini-based real OAuth handoff
- richer post-bind user flows
- optional post-bind self-service UX
- later login/session integration if ever justified
