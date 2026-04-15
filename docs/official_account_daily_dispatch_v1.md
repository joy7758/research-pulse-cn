# Official-Account Daily Dispatch v1

## Why Issue-Level Dispatch Is Added After Digest Orchestration
- The system already had:
  - selected `PulseCard` rows
  - sectioned `PulseDigestIssue.content_payload`
  - per-binding `DigestPublicationJob` preparation
  - per-job provider-boundary dispatch
- This phase adds one layer above that:
  - dispatch one digest issue as one batch
  - keep per-job provider semantics unchanged
  - aggregate outcomes without turning the system into a campaign engine

## DigestDispatchRun Model
- `DigestDispatchRun` records one issue-level official-account dispatch attempt.
- Key fields:
  - `digest_issue_id`
  - `user_id`
  - `publish_target`
  - `dispatch_mode`
  - `provider_mode`
  - `status`
  - `total_jobs`
  - `eligible_jobs`
  - `previewed_jobs`
  - `sent_jobs`
  - `failed_jobs`
  - `skipped_jobs`
  - `started_at`
  - `finished_at`
  - `last_error`
- One digest issue can accumulate multiple dispatch runs over time.

## Dispatch-Preview And Dispatch Behavior
- `GET /admin/digest-issues/{digest_issue_id}/dispatch-preview` returns:
  - digest issue summary
  - provider status summary
  - delivery-control preview
  - `eligible_jobs`
  - `already_sent_jobs`
  - `failed_jobs`
  - `would_prepare`
  - skip reasons when nothing would run
- `POST /admin/digest-issues/{digest_issue_id}/dispatch`:
  - optionally prepares jobs first when allowed
  - dispatches eligible `official_account` jobs one by one
  - links resulting `DigestPublicationAttempt` rows back to `dispatch_run_id`
  - aggregates one final run status:
    - `completed`
    - `partial_failed`
    - `failed`
    - `skipped`
- If user-side delivery policy blocks dispatch:
  - no fake send occurs
  - no fake success occurs
  - a `DigestDeliveryDecision` is written
  - no `DigestDispatchRun` is created in this policy-blocked path in v1

## Eligible Job Rules
- Eligible jobs must satisfy:
  - `publish_target = official_account`
  - `status in [prepared, previewed]`
  - `status = failed` only when retry is enabled
- Default idempotency rules:
  - `sent` jobs are not dispatched again
  - concurrent running dispatch runs for the same issue are blocked
  - repeated dispatch on an already-sent issue becomes `skipped`, not resend

## Auto-Dispatch Hook
- Auto-dispatch only runs after orchestration when both are enabled:
  - `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=true`
  - `APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT=true`
- If `APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE=true`:
  - dry-run orchestration still prepares jobs
  - auto-dispatch is skipped unless provider mode is `real` and real send is enabled
- Repeated orchestration does not resend already-sent jobs.
- Auto-dispatch now also respects user-side delivery control:
  - quiet hours
  - muted windows
  - weekday allow-lists
  - digest-content thresholds
  - missing-today-focus policy
- A later self-service reserve boundary can update the same `SubscriptionPolicy` fields and inspect an authoritative preview without crossing into admin/provider routes.

## Dry-Run Vs Real Behavior At Issue Level
- `dry_run`
  - produces a `completed` run when all eligible jobs preview successfully
  - increments `previewed_jobs`
  - keeps `sent_jobs = 0`
- `real`
  - uses existing provider readiness checks
  - sends each eligible job through the current real-send boundary
  - increments `sent_jobs` on success
- `disabled`
  - blocks issue-level dispatch cleanly before fake success is recorded

## Idempotency And Retry Semantics
- `retry_failed=false` by default.
- Failed jobs re-enter eligibility only when:
  - request payload sets `retry_failed=true`
  - or `APP_DIGEST_DISPATCH_RETRY_FAILED_JOBS=true`
- Missing jobs can be prepared first only when:
  - request payload sets `force_prepare=true`
  - or `APP_DIGEST_DISPATCH_PREPARE_IF_MISSING=true`

## Current Non-Goals
- new delivery channels
- broadcast or campaign logic
- OAuth binding flows
- AI digest rewriting
- scheduling or marketing automation

## Future Work
- richer delivery scheduling on top of issue dispatch runs
- user-level delivery analytics
- more explicit retry policies per binding
- campaign/broadcast logic only if future product scope truly requires it
