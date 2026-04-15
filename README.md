# Research Pulse CN

Commercial closed-source backend for a China-focused research paper lifecycle and pulse subscription system.

## Repository status
Private repository. Proprietary and confidential.

## What is included
- FastAPI backend with OpenAPI docs
- SQLAlchemy 2 models and Alembic migration
- CRUD APIs for users, papers, progress events, signal snapshots, and subscription policies
- Deterministic pulse preview and run flow
- Daily scheduler foundation with per-policy local-time scheduling
- Outbox-style delivery jobs with retry and dead-letter transitions
- Worker heartbeats, delivery-attempt tracking, readiness checks, and Prometheus-style metrics
- Current delivery paths for `in_app`, `email`, and `webhook`, with console/webhook adapters for local development
- Device-token sync backbone for desktop and future lightweight clients
- WeChat identity bindings plus digest issue/publication reserve objects for future official-account and mini-program flows
- Official-account provider boundary with `disabled` / `dry_run` / explicit `real` mode, callback ingress, and token-backed real-send activation
- Tauri 2 desktop shell with Rust-side pull sync, local SQLite cache, mutation outbox, minimal writeback for paper/progress/subscription policy edits, a local paper workspace layer, local markdown notes/templates, and a local review-matrix workflow that generates reviewer-matrix / response-letter drafts
- Pulse input-layer foundation with lightweight `WorkActivityEvent` capture, `ResearchWatchProfile` management, desktop-emitted work activity mutations, and deterministic pulse-input preview APIs
- Seed data, Docker Compose, pytest, Ruff, and CI

## Architecture
This project is built as a modular monolith.

Key boundaries:
- `domain`: enums and service contracts
- `db`: SQLAlchemy models, metadata, and session wiring
- `repositories`: persistence access
- `services`: application use cases, pulse engine, and delivery orchestration
- `adapters`: outbound channels and model-provider adapters
- `api`: FastAPI routes and exception handling

The code keeps pulse generation behind stable interfaces such as `FactCollector`, `RuleEngine`, `ModelProvider`, `CardValidator`, and `ChannelAdapter`. That makes the system easier to evolve toward more autonomous AI-agent-driven workflows without rewriting the backbone.

## Stack
- Python 3.12+
- FastAPI
- SQLAlchemy 2
- PostgreSQL
- Redis
- Docker Compose
- Pytest
- Ruff

## Local development
1. Create a virtual environment:
   `python3 -m venv .venv && source .venv/bin/activate`
2. Install dependencies:
   `make install`
3. Copy environment variables:
   `cp .env.example .env`
4. Start infrastructure:
   `make docker-up`
5. Run migrations:
   `make migrate`
6. Bootstrap a super admin for protected routes:
   `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
7. Seed demo data:
   `make seed`
8. Run the API:
   `make run-api`
9. Run the delivery worker:
   `make run-worker`
10. Run the daily scheduler:
   `make run-scheduler`
11. Install desktop dependencies if you are working on the shell:
   `make desktop-install`
12. Run the desktop shell:
   `make desktop-dev`

Open API docs at `http://127.0.0.1:8000/docs`.

## Desktop shell
The repository now includes a desktop client skeleton under `apps/desktop` using:
- Tauri 2
- React
- TypeScript
- Vite

The shell currently uses device-token sync against:
- `GET /sync/me`
- `POST /sync/push`
- `GET /sync/feed`
- `POST /sync/ack`

Desktop prerequisites on macOS include:
- Xcode Command Line Tools
- Rust

The desktop shell now also supports a local-only paper workspace:
- user-chosen workspace root
- deterministic `papers/<paper_id>/...` folder layout
- managed-copy attachment import
- local attachment metadata index in desktop SQLite

This workspace layer does not upload files, sync attachments to the backend, or run OCR/AI analysis in v1.

The desktop shell now also supports local-only per-paper notes:
- markdown note files under `papers/<paper_id>/notes/`
- built-in templates for research notes, revision planning, response letters, reviewer matrices, and submission checklists
- note metadata indexed in desktop SQLite while note content remains file-backed on disk

These notes do not sync to the backend and do not use AI generation in v1.

The desktop shell now also supports a local-only review matrix workflow:
- manual review rounds per paper
- structured reviewer comment rows with dispositions and response summaries
- generated local markdown drafts for `reviewer_matrix` and `response_letter`

Review matrix data and generated drafts stay local in v1 and do not sync to the backend.

Selected desktop-local actions now also emit lightweight `work_activity.record` mutations through the existing sync outbox so the cloud can build pulse inputs without receiving local file or note contents.

## Pulse input layer
The backend now includes a pulse input layer for future retrieval and recap work:
- `WorkActivityEvent` for structured "what the user did" signals
- `ResearchWatchProfile` for structured "what the user should watch" interests
- `GET /pulse/input-preview/{user_id}` for a deterministic preview of the current input window, activity summary, and effective watch seeds

This phase remains input-only:
- no external retrieval
- no AI summarization
- no final yesterday-summary pulse cards yet

## Common commands
- `make install`: install runtime and dev dependencies
- `make run` or `make run-api`: run the FastAPI development server
- `make migrate`: apply Alembic migrations
- `make seed`: load local demo data
- `make worker`: process pending pulse and delivery jobs once
- `make run-worker`: run the polling delivery worker
- `make scheduler-tick`: run one scheduler tick
- `make run-scheduler`: run the polling scheduler
- `make bootstrap-admin EMAIL=... PASSWORD=...`: create or update the bootstrap super admin
- `make lint`: run Ruff checks
- `make format`: run Ruff formatting
- `make test`: run the test suite
- `make check`: run lint and tests
- `make docker-up`: start API dependencies with Docker Compose
- `make docker-down`: stop Docker Compose services
- `make desktop-install`: install desktop dependencies under `apps/desktop`
- `make desktop-dev`: run the Tauri desktop shell in development mode
- `make desktop-lint`: run desktop lint and typecheck
- `make desktop-test`: run desktop frontend tests plus Rust cache/sync tests
- `make desktop-build-web`: build the desktop web frontend without native packaging

## Environment
Main environment variables are documented in `.env.example`.

Important values:
- `APP_DATABASE_URL`: optional override for local SQLite or test databases
- `POSTGRES_*`: PostgreSQL connection settings
- `REDIS_*`: Redis connection settings
- `APP_DEFAULT_TIMEZONE`: fallback timezone for daily scheduling
- `APP_PULSE_DEFAULT_SEND_HOUR_LOCAL`: default local send hour for daily policies
- `APP_PULSE_DEFAULT_SEND_MINUTE_LOCAL`: default local send minute for daily policies
- `APP_MAX_DELIVERY_RETRIES`: retry ceiling before dead-letter
- `APP_DELIVERY_RETRY_DELAY_SECONDS`: retry backoff in seconds
- `APP_WORKER_HEARTBEAT_INTERVAL_SECONDS`: expected heartbeat cadence for local workers
- `APP_WORKER_LEASE_SECONDS`: lease duration when a worker claims a pulse job
- `APP_AUTH_ACCESS_TOKEN_TTL_MINUTES`: admin access token lifetime
- `APP_AUTH_REFRESH_TOKEN_TTL_DAYS`: server-revocable refresh token lifetime
- `APP_AUTH_JWT_SECRET`: JWT signing secret for admin access tokens
- `APP_AUTH_JWT_ISSUER`: expected issuer claim for admin access tokens
- `APP_AUTH_JWT_AUDIENCE`: expected audience claim for admin access tokens
- `APP_INTERNAL_SERVICE_TOKEN`: bearer token for internal `/ops/*` and readiness callers
- `APP_SYNC_DEVICE_TOKEN_TTL_DAYS`: sync device token lifetime
- `APP_SYNC_FEED_DEFAULT_LIMIT`: default incremental sync page size
- `APP_SYNC_FEED_MAX_LIMIT`: max allowed sync feed page size
- `APP_SYNC_PUSH_MAX_BATCH_SIZE`: max mutations accepted per sync push batch
- `APP_MINI_READ_GRANT_DEFAULT_TTL_HOURS`: default preview-grant lifetime for `/mini/*`
- `APP_MINI_PAPERS_DEFAULT_LIMIT`: default compact paper page size for mini reads
- `APP_MINI_PAPERS_MAX_LIMIT`: max compact paper page size for mini reads
- `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`: official-account provider mode: `disabled`, `dry_run`, or `real`
- `APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND`: outbound transport strategy, currently `template_notice`
- `APP_WECHAT_OFFICIAL_APP_ID`: official-account app id for provider readiness and callback matching
- `APP_WECHAT_OFFICIAL_APP_SECRET`: official-account secret for real access-token refresh
- `APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID`: template-notice template id used in real mode
- `APP_WECHAT_OFFICIAL_CALLBACK_TOKEN`: signature token for callback verification
- `APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY`: reserved AES key for future richer callback handling
- `APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED`: enable or disable callback ingress handling
- `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED`: explicit safety switch required in addition to `provider_mode=real`
- `APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS`: early-refresh buffer for cached access tokens
- `APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS`: connect timeout for provider HTTP calls
- `APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS`: read timeout for provider HTTP calls
- `APP_OFFICIAL_ACCOUNT_MAX_RETRIES`: retry budget for real outbound template sends
- `APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON`: optional logical-field to template-field mapping JSON
- `APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID`: default mini-program app id for landing payloads
- `APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL`: optional base URL for future article landing payloads
- `APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS`: dispatch timeout budget reported in provider status

Real official-account sending stays opt-in. Local and test setups do not require live WeChat credentials unless you intentionally enable `provider_mode=real` and `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED=true`.
Mini-program access is reserve-only and read-only in this phase.

## Running workers and scheduler
Run one-off local cycles:

`make worker`

`make scheduler-tick`

Run long-lived local loops:

`python -m research_pulse_cn.worker.main --limit 20 --poll-interval 15`

`python -m research_pulse_cn.scheduler.main --poll-interval 60`

With Docker Compose, the codebase now exposes separate `api`, `worker`, and `scheduler` services.

## Operations surface
- Auth:
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `POST /auth/logout`
  - `GET /auth/me`
- Admin:
  - `GET /admin/admin-accounts`
  - `POST /admin/admin-accounts`
  - `PATCH /admin/admin-accounts/{admin_account_id}`
  - `POST /admin/admin-accounts/{admin_account_id}/set-password`
  - `GET /admin/audit-logs`
  - `GET /admin/client-devices`
  - `POST /admin/client-devices`
  - `POST /admin/client-devices/{client_device_id}/rotate-token`
  - `POST /admin/client-devices/{client_device_id}/revoke`
  - `GET /admin/wechat-bindings`
  - `POST /admin/wechat-bindings`
  - `PATCH /admin/wechat-bindings/{binding_id}`
  - `GET /admin/digest-issues`
  - `GET /admin/digest-issues/{digest_issue_id}`
  - `POST /admin/digest-issues/build/{user_id}`
  - `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
  - `GET /admin/digest-publication-jobs`
  - `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
  - `GET /admin/digest-publication-attempts`
  - `GET /admin/official-account/provider-status`
  - `POST /admin/official-account/provider-token/refresh`
  - `GET /admin/official-account/callback-events`
  - `GET /admin/mini-read-grants`
  - `POST /admin/mini-read-grants`
  - `POST /admin/mini-read-grants/{grant_id}/revoke`
- Health:
  - `GET /health`
  - `GET /health/live`
  - `GET /health/ready`
- Pulse:
  - `POST /pulse/preview/{user_id}`
  - `POST /pulse/run/{user_id}`
  - `GET /pulse/input-preview/{user_id}`
- Research inputs:
  - `GET /work-activity-events`
  - `GET /research-watch-profiles`
  - `POST /research-watch-profiles`
  - `PATCH /research-watch-profiles/{profile_id}`
  - `DELETE /research-watch-profiles/{profile_id}`
  - `POST /research-watch-profiles/bootstrap/{paper_id}`
- Ops:
  - `GET /ops/metrics`
  - `GET /ops/heartbeats`
  - `GET /ops/pulse-jobs`
  - `GET /ops/delivery-jobs`
  - `GET /ops/delivery-attempts`
  - `POST /ops/scheduler/tick`
  - `POST /ops/delivery-jobs/{delivery_job_id}/requeue`
  - `POST /ops/pulse-jobs/{pulse_job_id}/replay`
- Sync:
  - `GET /sync/me`
  - `GET /sync/feed`
- `POST /sync/push`
- `POST /sync/ack`

Desktop writeback in v1 is intentionally narrow:
- `paper.patch`
- `progress_event.create`
- `subscription_policy.patch`
- `work_activity.record`
- Mini:
  - `GET /mini/bootstrap`
  - `GET /mini/today`
  - `GET /mini/digest-issues/{digest_issue_id}`
  - `GET /mini/papers`
  - `GET /mini/papers/{paper_id}`
- Integrations:
  - `GET /integrations/wechat/official-account/callback`
  - `POST /integrations/wechat/official-account/callback`

## Seeded demo profile
`make seed` creates:
- one demo user
- two demo papers
- progress and signal history
- in-app and webhook delivery policies

## Structure
- `src/research_pulse_cn`: application code
- `tests`: test suite
- `docs`: product and implementation notes

## Pulse scoring
The ranking pipeline is documented in [docs/pulse_scoring.md](docs/pulse_scoring.md).

## Operations guide
Operational scheduling, replay, requeue, heartbeats, attempts, and metrics are documented in [docs/operations.md](docs/operations.md).

## Auth and admin boundary
Admin authentication, RBAC, internal service auth, audit logs, and bootstrap flow are documented in [docs/auth_admin_boundary.md](docs/auth_admin_boundary.md).

## Sync foundation
Device identity, incremental feed, mutation idempotency, and future lightweight-client alignment are documented in [docs/sync_foundation.md](docs/sync_foundation.md).

## Desktop Tauri skeleton
Desktop shell layout, local cache, pull-sync flow, and developer workflow are documented in [docs/desktop_tauri_skeleton_v1.md](docs/desktop_tauri_skeleton_v1.md).

## Official-account digest reserve
Digest issues, WeChat identity binding, and publication preparation without real external sends are documented in [docs/official_account_digest_reserve.md](docs/official_account_digest_reserve.md).

## Mini-program read-only reserve
Mini preview grants, compact mobile read models, and derived paper progress percentages are documented in [docs/mini_program_readonly_reserve.md](docs/mini_program_readonly_reserve.md).

## Official-account provider boundary
Dry-run dispatch, callback ingress, subscription-state updates, and provider-safe settings are documented in [docs/official_account_provider_boundary.md](docs/official_account_provider_boundary.md).

## Official-account real send
Real-mode activation, access-token caching, template-notice transport, and credential-backed per-binding dispatch are documented in [docs/official_account_real_send_v1.md](docs/official_account_real_send_v1.md).
