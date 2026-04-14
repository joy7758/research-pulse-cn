# Official-Account Provider Boundary

## Why The Provider Boundary Comes Before Real Sending
- The backend already has digest issues, publication jobs, mini landing paths, and WeChat identity bindings.
- The next safe step is to make the official-account path provider-ready without forcing real outbound traffic in local or test environments.
- This phase hardens the dispatch contract, callback ingress, and subscription-state updates before any live credential rollout.

## Settings And Modes
- `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`
  - `disabled`
  - `dry_run`
- `APP_WECHAT_OFFICIAL_APP_ID`
- `APP_WECHAT_OFFICIAL_APP_SECRET`
- `APP_WECHAT_OFFICIAL_CALLBACK_TOKEN`
- `APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY`
- `APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED`
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
- In v1 statuses are:
  - `started`
  - `previewed`
  - `failed`

## Dispatch Flow
1. `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
2. Eligible official-account bindings get `DigestPublicationJob` rows in `prepared` state.
3. `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
4. The service creates a `DigestPublicationAttempt`.
5. The `OfficialAccountPublisher` boundary runs.
6. In `dry_run` mode the attempt becomes `previewed` and the job becomes `previewed`.
7. In `disabled` mode the attempt is recorded as failed and the request returns a controlled conflict.

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
- No real outbound official-account send exists yet.
- AES decryption and richer provider callback handling are deferred.
- No OAuth or end-user reconciliation flow exists for missing bindings.
- Callback processing only supports a narrow event subset in v1.
- Publication attempts are admin-visible only and are not synced to clients.

## Future Work
- real outbound provider integration
- binding reconciliation through future auth or OAuth flows
- official-account to mini-program landing handoff
- richer event handling and provider diagnostics
