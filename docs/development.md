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
- DingTalk adapter is a non-network skeleton with retry-aware failure simulation.
- WeChat remains a stub and intentionally dead-letters if selected.

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
- Add authenticated channel delivery implementations.
- Add customer-facing auth separately from `AdminAccount`.
- Add SSO/OIDC only after the internal admin boundary stabilizes.
