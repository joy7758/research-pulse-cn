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
- Console adapter, DingTalk webhook adapter skeleton, and WeChat adapter stub
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

Open API docs at `http://127.0.0.1:8000/docs`.

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
- Health:
  - `GET /health`
  - `GET /health/live`
  - `GET /health/ready`
- Pulse:
  - `POST /pulse/preview/{user_id}`
  - `POST /pulse/run/{user_id}`
- Ops:
  - `GET /ops/metrics`
  - `GET /ops/heartbeats`
  - `GET /ops/pulse-jobs`
  - `GET /ops/delivery-jobs`
  - `GET /ops/delivery-attempts`
  - `POST /ops/scheduler/tick`
  - `POST /ops/delivery-jobs/{delivery_job_id}/requeue`
  - `POST /ops/pulse-jobs/{pulse_job_id}/replay`

## Seeded demo profile
`make seed` creates:
- one demo user
- two demo papers
- progress and signal history
- in-app and DingTalk delivery policies

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
