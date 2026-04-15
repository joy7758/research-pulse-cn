# Official-Account Provider Boundary

## Why The Provider Boundary Comes Before Real Sending
- The backend already has digest issues, publication jobs, mini landing paths, and WeChat identity bindings.
- The next safe step is to make the official-account path provider-ready without forcing real outbound traffic in local or test environments.
- This phase hardens the dispatch contract, callback ingress, and subscription-state updates before any live credential rollout.

## Settings And Modes
- `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`
  - `disabled`
  - `dry_run`
  - `real`
- `APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND`
- `APP_WECHAT_OFFICIAL_APP_ID`
- `APP_WECHAT_OFFICIAL_APP_SECRET`
- `APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID`
- `APP_WECHAT_OFFICIAL_CALLBACK_TOKEN`
- `APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY`
- `APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED`
- `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED`
- `APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS`
- `APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS`
- `APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS`
- `APP_OFFICIAL_ACCOUNT_MAX_RETRIES`
- `APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON`
- `APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID`
- `APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL`
- `APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS`

Current behavior:
- `disabled`
  - prepare is still allowed
  - dispatch is blocked with a controlled conflict
- `dry_run`
  - dispatch creates attempts and preview payloads
  - no external send occurs
- `real`
  - dispatch can use cached access tokens and a concrete outbound transport
  - real sends still require an explicit readiness gate and safety flag

## OfficialAccountCallbackEvent Model
- Stores inbound callback payloads before and after minimal processing.
- Key fields:
  - `app_id`
  - `to_user_name`
  - `from_openid`
  - `msg_type`
  - `event_type`
  - `event_key`
  - `event_time`
  - `dedupe_key`
  - `signature_valid`
  - `payload_format`
  - `raw_payload`
  - `parsed_payload`
  - `processing_status`
  - `processing_note`
  - `linked_binding_id`
  - timestamps
- Raw payload is retained even when parsing or signature validation fails.

## DigestPublicationAttempt Model
- `DigestPublicationAttempt` records one dispatch attempt for one publication job.
- Key fields:
  - `digest_publication_job_id`
  - `attempt_number`
  - `provider_name`
  - `provider_mode`
  - `status`
  - `request_payload`
  - `response_payload`
  - `error_summary`
  - timestamps
- Current statuses are:
  - `started`
  - `previewed`
  - `sent`
  - `failed`

## Dispatch Flow
1. `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
2. Eligible official-account bindings get `DigestPublicationJob` rows in `prepared` state.
3. `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
4. The service creates a `DigestPublicationAttempt`.
5. The `OfficialAccountPublisher` boundary runs.
6. In `dry_run` mode the attempt becomes `previewed` and the job becomes `previewed`.
7. In `real` mode a provider-backed attempt can become `sent` or `failed`.
8. In `disabled` mode the attempt is recorded as failed and the request returns a controlled conflict.

## Inbound Callback Flow
### GET handshake
- `GET /integrations/wechat/official-account/callback`
- Used for token-based verification and echo handshake behavior when callback handling is enabled.

### POST callback
- `POST /integrations/wechat/official-account/callback`
- Persists the raw payload.
- Verifies the signature.
- Parses only the minimum fields needed for v1.
- Dedupes repeated events with `dedupe_key`.
- Applies supported events:
  - `subscribe`
  - `unsubscribe`

### Binding updates
- Matching rule:
  - `channel_type = official_account`
  - `app_id`
  - `openid`
- If matched:
  - `subscribed`
  - `subscribed_at`
  - `unsubscribed_at`
  - `last_seen_at`
  - `bind_state`
  can be updated.
- If unmatched:
  - the callback event is stored
  - no new user binding is auto-created in v1

## Current Limitations
- This document now stops at the provider boundary and callback layer.
- Real-send activation details live in `docs/official_account_real_send_v1.md`.
- AES decryption and richer provider callback handling are deferred.
- No OAuth or end-user reconciliation flow exists for missing bindings.
- Callback processing only supports a narrow event subset in v1.
- Publication attempts are admin-visible only and are not synced to clients.

## Future Work
- binding reconciliation through future auth or OAuth flows
- official-account to mini-program landing handoff
- richer event handling and provider diagnostics
