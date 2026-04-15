# Development Guide

## Prerequisites
- Python 3.12+
- Docker and Docker Compose
- Node.js 20+
- Rust toolchain
- macOS desktop work requires Xcode Command Line Tools for Tauri

## First-time setup
1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `make install`
4. `cp .env.example .env`

## Daily workflow
1. Start infrastructure: `make docker-up`
2. Apply migrations: `make migrate`
3. Bootstrap an admin: `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
4. Seed demo data if needed: `make seed`
5. Run API: `make run-api`
6. Run worker once: `make worker`
7. Run scheduler once: `make scheduler-tick`
8. Run long-lived worker if needed: `make run-worker`
9. Run long-lived scheduler if needed: `make run-scheduler`

## Checks
- Lint: `make lint`
- Format: `make format`
- Tests: `make test`
- Full local gate: `make check`

## Desktop shell
- Install desktop dependencies:
  - `make desktop-install`
- Run the desktop shell:
  - `make desktop-dev`
- Run desktop lint + typecheck:
  - `make desktop-lint`
- Run desktop tests:
  - `make desktop-test`
- Build the desktop web frontend:
  - `make desktop-build-web`

Desktop sync in this phase uses:
- `GET /sync/me`
- `POST /sync/push`
- `GET /sync/feed`
- `POST /sync/ack`

The desktop shell does not use admin login. It uses admin-issued device tokens, keeps the token on the Rust side, and persists local mutations into a SQLite outbox before attempting sync.

Desktop can now also emit lightweight `work_activity.record` mutations for local-only actions such as attachment import, note create/save, and review-note generation. These mutations carry summary metadata only and never upload local file or note contents.

## Pulse scoring knobs
- Defaults live in application settings and `.env.example`
- Per-user overrides can be applied through `SubscriptionPolicy.policy["pulse"]`
- See `docs/pulse_scoring.md` for the exact pipeline and supported knobs

## Scheduler knobs
- Daily auto-scheduling only applies to enabled `SubscriptionPolicy` rows with `frequency = daily`
- Supported policy JSON keys:
  - `schedule.timezone`
  - `schedule.send_hour_local`
  - `schedule.send_minute_local`
- If `schedule` is omitted, the service falls back to app-level defaults
- Event policies stay manual in v1

## Auth and admin boundary
- `UserProfile` remains a business entity and is not used for login.
- Human admins authenticate through `/auth/login` and receive:
  - a short-lived JWT access token
  - a server-revocable refresh token
- Internal service callers use `APP_INTERNAL_SERVICE_TOKEN`.
- Role matrix:
  - `viewer`: read-only business endpoints and pulse preview
  - `operator`: business writes, pulse run, scheduler tick, replay, and requeue
  - `super_admin`: operator permissions plus admin-account management and audit-log access
- `GET /health/live` stays public.
- `GET /health/ready` and `/ops/*` require operator/super_admin or the internal service token.

## Bootstrap flow
- Create or update the initial super admin:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
- Optional display name:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!' DISPLAY_NAME='Ops Admin'`
- After bootstrap, obtain tokens from `/auth/login` before using protected business or admin routes.

## Database notes
- Production target is PostgreSQL.
- Tests use SQLite through `APP_DATABASE_URL`.
- Alembic migrations are the source of truth for schema evolution.

## Delivery adapter notes
- Console adapter is the safe default for local verification.
- Webhook adapter is the only network-shaped outbound adapter in current runtime flows.
- Legacy `dingtalk` and `wechat` enum values remain only for compatibility with old rows and are rejected for new policy writes.
- Future communication work should target:
  - official-account digest publishing
  - mini-program lightweight client access through sync

## Sync foundation
- Device tokens are created under `/admin/client-devices`.
- Device tokens can only access `/sync/*`.
- Incremental sync flow in v1:
  - `GET /sync/feed`
  - `POST /sync/ack`
  - `POST /sync/push`
- Sync defaults live in `.env.example`:
  - `APP_SYNC_DEVICE_TOKEN_TTL_DAYS`
  - `APP_SYNC_FEED_DEFAULT_LIMIT`
  - `APP_SYNC_FEED_MAX_LIMIT`
  - `APP_SYNC_PUSH_MAX_BATCH_SIZE`
- Conflict handling in v1 is last-write-wins for supported patch operations.
- `POST /sync/push` now also accepts `work_activity.record` for lightweight desktop activity capture.

## Desktop shell
- The desktop shell lives under `apps/desktop`.
- Tauri commands exposed to the frontend include:
  - `appBootstrap`
  - `connectDevice`
  - `disconnectDevice`
  - `clearLocalCache`
  - `queuePaperPatch`
  - `queueProgressEventCreate`
  - `queueSubscriptionPolicyPatch`
  - `syncNow`
  - `getSyncStatus`
  - `getTodayOverview`
  - `listPapers`
  - `getPaperDetail`
  - `listSubscriptionPolicies`
  - `listPendingMutations`
  - `listReviewRounds`
  - `createReviewRound`
  - `updateReviewRound`
  - `listReviewComments`
  - `addReviewComment`
  - `updateReviewComment`
  - `deleteReviewComment`
  - `generateReviewerMatrixNote`
  - `generateResponseLetterNote`
  - `getReviewRoundDetail`
- Local cache tables:
  - `sync_state`
  - `paper_cache`
  - `progress_event_cache`
  - `signal_snapshot_cache`
  - `subscription_policy_cache`
  - `digest_issue_cache`
  - `sync_event_cache`
  - `mutation_outbox`
  - `workspace_settings`
  - `paper_workspace_cache`
  - `paper_attachment_cache`
  - `paper_note_cache`
  - `paper_review_round_cache`
  - `review_comment_item_cache`
- Desktop sync now runs:
  - push queued mutations
  - pull feed pages
  - apply events
  - ack only after successful apply
- Desktop local actions now also queue `work_activity.record` for:
  - attachment import
  - note create
  - note save
  - review round create
  - reviewer-matrix note generation
  - response-letter note generation
- `progress_percentage` in desktop list/detail views is the same derived heuristic used by the mini read model, not a persisted workflow truth field.
- Desktop local workspace in v1:
  - choose a workspace root from Settings
  - ensure a deterministic paper workspace from Paper Detail
  - import attachments as managed local copies only
  - refresh attachment status when files disappear from disk
- Desktop local notes/templates in v1:
  - create markdown notes under `papers/<paper_id>/notes/`
  - create from built-in templates or as blank notes
  - save note content to disk from the Paper Detail editor
  - refresh note metadata when files are missing or changed outside the app
- Desktop local review matrix in v1:
  - create local review rounds per paper
  - store ordered reviewer comments with manual dispositions and response summaries
  - generate local `reviewer_matrix` and `response_letter` markdown notes from structured rows
  - update linked generated notes in place when regenerating the same round
- Changing or clearing the workspace root does not move or delete existing managed files.
- `clearLocalCache` and `disconnectDevice` do not delete managed workspace files, local note files, or generated review notes.

## Official-account digest reserve
- WeChat identity binding is admin-managed only in v1.
- There is no real OAuth, official-account API call, or mini-program frontend in this phase.
- New admin endpoints:
  - `GET /admin/wechat-bindings`
  - `POST /admin/wechat-bindings`
  - `PATCH /admin/wechat-bindings/{binding_id}`
  - `GET /admin/digest-issues`
  - `GET /admin/digest-issues/{digest_issue_id}`
  - `POST /admin/digest-issues/build/{user_id}`
  - `POST /admin/digest-issues/orchestrate/{user_id}`
  - `GET /admin/digest-issues/{digest_issue_id}/daily-preview`
  - `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
  - `GET /admin/digest-publication-jobs`
- `PulseDigestIssue` is built from already selected `PulseCard` rows only.
- Daily digest orchestration now reshapes selected cards into a fixed section model:
  - `today_focus`
  - `yesterday_recap`
  - `signal_updates`
  - `related_papers`
  - `other_updates`
- Conservative orchestration caps come from:
  - `APP_DIGEST_SIGNAL_UPDATES_MAX_ITEMS`
  - `APP_DIGEST_RELATED_PAPERS_MAX_ITEMS`
  - `APP_DIGEST_OTHER_UPDATES_MAX_ITEMS`
- `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=true` only prepares publication jobs after orchestration; it does not dispatch sends.
- `APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT=true` adds one issue-level dispatch step after orchestration only when the provider boundary allows it.
- `APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE=true` keeps auto-dispatch off in `dry_run`.
- `APP_DIGEST_DISPATCH_PREPARE_IF_MISSING=true` allows issue-level dispatch to prepare missing official-account jobs first.
- Publication preparation is stub-only:
  - jobs move to `prepared`
  - no real external send occurs
- Future WeChat work remains:
  - official-account digest publishing
  - mini-program read-only landing on top of sync

## Mini-program read-only reserve
- Mini access is modeled as a separate read-only auth boundary.
- Operators and super admins can create preview grants under:
  - `GET /admin/mini-read-grants`
  - `POST /admin/mini-read-grants`
  - `POST /admin/mini-read-grants/{grant_id}/revoke`
- Mini grant tokens can only access:
  - `GET /mini/bootstrap`
  - `GET /mini/today`
  - `GET /mini/digest-issues/{digest_issue_id}`
  - `GET /mini/papers`
  - `GET /mini/papers/{paper_id}`
- Mini defaults live in `.env.example`:
  - `APP_MINI_READ_GRANT_DEFAULT_TTL_HOURS`
  - `APP_MINI_PAPERS_DEFAULT_LIMIT`
  - `APP_MINI_PAPERS_MAX_LIMIT`
- `progress_percentage` is a derived UI/read-model heuristic from `PaperProfile.type`, not a persisted workflow truth field.
- Preview grants can point at:
  - a user overview
  - a digest landing
  - a paper-detail landing
- No real mini-program auth, session exchange, or frontend code exists in v1.

## Official-account provider boundary
- Official-account dispatch now has an explicit provider mode:
  - `disabled`
  - `dry_run`
  - `real`
- New provider settings live in `.env.example`:
  - `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`
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
- Admin inspection and dispatch endpoints:
  - `GET /admin/digest-issues/{digest_issue_id}/dispatch-preview`
  - `POST /admin/digest-issues/{digest_issue_id}/dispatch`
  - `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
  - `GET /admin/digest-publication-attempts`
  - `GET /admin/digest-dispatch-runs`
  - `GET /admin/digest-dispatch-runs/{dispatch_run_id}`
  - `GET /admin/official-account/provider-status`
  - `POST /admin/official-account/provider-token/refresh`
  - `GET /admin/official-account/callback-events`
- Provider ingress endpoints:
  - `GET /integrations/wechat/official-account/callback`
  - `POST /integrations/wechat/official-account/callback`
- `dry_run` dispatch creates preview attempts and never performs a live send.
- `real` dispatch is still opt-in and requires:
  - `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE=real`
  - `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED=true`
  - configured app id, app secret, and digest template id
- Real mode uses a client-credential access-token flow with Redis-preferred caching and in-memory fallback for local/test.

## Pulse input layer
- New backend entities:
  - `WorkActivityEvent`
  - `ResearchWatchProfile`
  - `ExternalRetrievalPlan`
- New read/management endpoints:
  - `GET /work-activity-events`
  - `GET /research-watch-profiles`
  - `POST /research-watch-profiles`
  - `PATCH /research-watch-profiles/{profile_id}`
  - `DELETE /research-watch-profiles/{profile_id}`
  - `POST /research-watch-profiles/bootstrap/{paper_id}`
  - `GET /pulse/input-preview/{user_id}`
  - `GET /external-retrieval/input-preview/{user_id}`
  - `GET /external-retrieval/plans`
  - `POST /external-retrieval/plans/build/{user_id}`
- Cloud-side service actions auto-record work activity for:
  - `paper.patch`
  - `progress_event.create`
  - `subscription_policy.patch`
- Desktop-local attachment/note/review actions contribute through `work_activity.record`.
- `POST /pulse/preview/{user_id}` and `POST /pulse/run/{user_id}` now also accept an optional `timezone` query parameter for deterministic yesterday-summary inspection.
- `today_suggestion` is now a first-party pulse card type generated only from internal paper/progress/signal state.
- `yesterday_summary` is now a first-party pulse card type generated only from the previous local day of `WorkActivityEvent`.
- `related_paper` is now a first-party pulse card type generated only from persisted normalized `ExternalRetrievedRecord` rows.
- External retrieval now has a separate planning and execution boundary:
  - `ExternalRetrievalPlan` persists source-specific plan inputs
  - `ExternalRetrievalRun` persists one fetch attempt per plan
  - `ExternalRetrievedRecord` stores normalized official-source records
  - `GET /pulse/input-preview/{user_id}` includes compact planning and latest-run summaries
  - pulse preview/run consume normalized records only and never execute retrieval inline
- No AI summarization is enabled in this phase.
- Summary timezone resolution order is:
  - explicit request timezone
  - first enabled daily policy timezone
  - app default timezone

### Today-suggestion scoring knobs
- `APP_PULSE_WEIGHT_TODAY_SUGGESTION`
- `APP_PULSE_TODAY_SUGGESTION_STALE_DAYS_THRESHOLD`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_PRIORITY`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_HAS_NEXT_ACTION`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_REVISION_STAGE`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_STALE_PROGRESS`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_BLOCKER_PRESENT`

### Yesterday-summary scoring knobs
- `APP_PULSE_WEIGHT_YESTERDAY_SUMMARY`
- `APP_PULSE_YESTERDAY_SUMMARY_MIN_EVENTS`
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_ACTIVITY_DIVERSITY`
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_MULTI_PAPER`

### Related-paper scoring knobs
- `APP_PULSE_WEIGHT_RELATED_PAPER`
- `APP_PULSE_MODIFIER_RELATED_PAPER_HAS_DOI`
- `APP_PULSE_MODIFIER_RELATED_PAPER_MATCH_REASON_COUNT`
- `APP_PULSE_MODIFIER_RELATED_PAPER_LINKED_PAPER`
- `APP_PULSE_MODIFIER_RELATED_PAPER_RECENT_RETRIEVAL`
- `APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS`
- `APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN`
- `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`

### External retrieval planning knobs
- `APP_EXTERNAL_RETRIEVAL_MODE`
- `APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES`
- `APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER`
- `APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT`
- `APP_EXTERNAL_RETRIEVAL_HTTP_CONNECT_TIMEOUT_SECONDS`
- `APP_EXTERNAL_RETRIEVAL_HTTP_READ_TIMEOUT_SECONDS`
- `APP_EXTERNAL_RETRIEVAL_MAX_RESULTS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES`
- `APP_EXTERNAL_RETRIEVAL_OPENALEX_API_KEY`
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO`
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME`
- `plan_only` keeps execution blocked while preserving plan preview/build.
- `execute` enables official-source fetches for persisted plans.
- Unknown callback identities are stored for review and do not auto-create bindings.

### External retrieval endpoints
- `GET /external-retrieval/input-preview/{user_id}`
- `GET /external-retrieval/provider-status`
- `GET /external-retrieval/plans`
- `POST /external-retrieval/plans/build/{user_id}`
- `POST /external-retrieval/plans/execute/{plan_id}`
- `GET /external-retrieval/runs`
- `GET /external-retrieval/runs/{run_id}`
- `GET /external-retrieval/results`
- Retrieval execution remains separate from pulse preview/run:
  - no inline retrieval during pulse generation
  - no related-news cards yet
  - no AI ranking
  - no scraping

## Ops endpoints
- `GET /health/live`: lightweight process liveness
- `GET /health/ready`: database readiness and component details, protected by operator/admin or internal service auth
- `GET /ops/metrics`: Prometheus-style counters
- `GET /ops/heartbeats`: scheduler and worker heartbeat rows
- `GET /ops/pulse-jobs`: pulse job lifecycle inspection
- `GET /ops/delivery-jobs`: delivery job inspection
- `GET /ops/delivery-attempts`: one row per delivery send attempt
- `POST /ops/scheduler/tick`: local manual scheduler trigger
- `POST /ops/delivery-jobs/{delivery_job_id}/requeue`: requeue failed or dead-letter delivery work
- `POST /ops/pulse-jobs/{pulse_job_id}/replay`: create or reuse a replay job

## Observability notes
- Worker heartbeats are stored in the database for local and low-volume deployments.
- Delivery attempts are append-only and tied to the existing outbox flow.
- Metrics are process-local counters in v1; treat them as lightweight local observability, not a distributed metrics backend.
- Replay and requeue are idempotent where practical and will not silently duplicate active work.

## Next extension points
- Replace `DummyModelProvider` with a real provider adapter.
- Expand deterministic facts into richer signal scoring and portfolio context.
- Add richer official-account digest sending strategy on top of persisted pulse, digest, and issue-dispatch data.
- Add real mini-program auth and landing handoff on top of the read-only reserve.
- Add customer-facing auth separately from `AdminAccount`.
- Add SSO/OIDC only after the internal admin boundary stabilizes.
