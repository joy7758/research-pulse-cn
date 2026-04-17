# Official-Account Real Send v1

## Why This Phase Is Per-Binding Real Send
- The backend already models digest issues, publication jobs, and WeChat bindings per user.
- This phase keeps outbound sending scoped to one binding and one recipient at a time.
- It deliberately avoids turning official-account publishing into a broadcast or campaign engine.

## Provider Modes And Transport Kind
- `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`
  - `disabled`
  - `dry_run`
  - `real`
- `APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND`
  - `template_notice`
- Real sends require both:
  - `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE=real`
  - `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED=true`

## Token Service And Cache Strategy
- `OfficialAccountAccessTokenService` uses the client-credential token flow.
- Tokens are cached outside the database and never written to publication tables.
- Cache strategy:
  - prefer Redis when it is available cleanly
  - fall back to in-memory cache for test/local or Redis failures
- Safe status fields exposed through provider status:
  - `token_cached`
  - `token_expires_at`
  - `last_refresh_at`
  - `cache_backend`

## Template Payload Builder And Field Mapping
- The real transport uses `template_notice`.
- When digest orchestration has populated `content_payload.publication_preview`, the provider-neutral payload prefers that sectioned daily-digest preview over older loose highlight text.
- Default logical digest fields:
  - `issue_title`
  - `issue_date`
  - `highlight_count`
  - `summary`
  - `primary_action`
  - `remark`
- Default template field mapping:
  - `issue_title -> first`
  - `issue_date -> keyword1`
  - `highlight_count -> keyword2`
  - `summary -> keyword3`
  - `remark -> remark`
- Optional override:
  - `APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON`

## Dispatch State Machine
1. Admin prepares `DigestPublicationJob` rows.
2. Admin dispatches one job through `/admin/digest-publication-jobs/{publication_job_id}/dispatch`.
3. A `DigestPublicationAttempt` row is created.
4. Provider mode decides the path:
   - `disabled -> conflict`
   - `dry_run -> previewed`
   - `real -> sent` or `failed`
5. Already sent jobs do not resend by default unless a future forced retry is introduced explicitly.

## Issue-Level Dispatch Layer
- A later issue-level orchestration layer can now batch multiple prepared official-account jobs under one `DigestDispatchRun`.
- That layer still reuses the same per-job provider semantics:
  - `disabled -> blocked`
  - `dry_run -> previewed`
  - `real -> sent` or `failed`
- `DigestPublicationAttempt.dispatch_run_id` links each per-job attempt back to the issue-level run when dispatch happens through the batch path.
- User-side delivery policy is a separate boundary on top of this:
  - issue-level dispatch may still be skipped before provider invocation because of quiet hours, mute windows, weekday rules, or digest-content thresholds
  - those policy decisions are recorded through `DigestDeliveryDecision`

## Readiness Model
- Provider readiness is true only when:
  - mode is not `disabled`
  - transport kind is supported
  - for `real` mode:
    - app id exists
    - app secret exists
    - digest template id exists
    - real send is explicitly enabled
- `GET /admin/official-account/provider-status` reports:
  - readiness
  - readiness checks
  - readiness failures
  - timeout and retry configuration
  - token-cache summary

## Dry-Run Vs Real Behavior
- `dry_run`
  - creates preview attempts
  - never performs outbound HTTP sends
  - keeps jobs in `previewed`
- `real`
  - refreshes or reuses an access token
  - builds a template payload
  - sends one request per binding
  - marks the job `sent` or `failed`

## Security And Secrets Handling
- No secrets are committed to the repo.
- Provider status never returns app secret or raw access token values.
- Publication attempts never store raw access tokens.
- Logs and error summaries avoid leaking secrets or token-bearing URLs.

## Current Non-Goals
- WeChat OAuth login
- Mini Program frontend code
- broadcast or campaign orchestration
- generic `DeliveryJob` integration for official-account sends
- customer-facing UI

## Future Work
- richer outbound strategies beyond `template_notice`
- broadcast and campaign workflow on top of the same provider boundary
- OAuth-driven binding reconciliation
- tighter official-account to mini-program landing handoff
