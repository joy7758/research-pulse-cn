# Development Guide

## Prerequisites
- Python 3.12+
- Docker and Docker Compose

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
  - `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
  - `GET /admin/digest-publication-jobs`
- `PulseDigestIssue` is built from already selected `PulseCard` rows only.
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
  - `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
  - `GET /admin/digest-publication-attempts`
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
- Unknown callback identities are stored for review and do not auto-create bindings.

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
- Add official-account digest publishing on top of persisted pulse and sync data.
- Add real mini-program auth and landing handoff on top of the read-only reserve.
- Add customer-facing auth separately from `AdminAccount`.
- Add SSO/OIDC only after the internal admin boundary stabilizes.
