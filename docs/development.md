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
3. Seed demo data if needed: `make seed`
4. Run API: `make run`
5. Run worker once: `make worker`

## Checks
- Lint: `make lint`
- Format: `make format`
- Tests: `make test`
- Full local gate: `make check`

## Pulse scoring knobs
- Defaults live in application settings and `.env.example`
- Per-user overrides can be applied through `SubscriptionPolicy.policy["pulse"]`
- See `docs/pulse_scoring.md` for the exact pipeline and supported knobs

## Database notes
- Production target is PostgreSQL.
- Tests use SQLite through `APP_DATABASE_URL`.
- Alembic migrations are the source of truth for schema evolution.

## Delivery adapter notes
- Console adapter is the safe default for local verification.
- DingTalk adapter is a non-network skeleton with retry-aware failure simulation.
- WeChat remains a stub and intentionally dead-letters if selected.

## Next extension points
- Replace `DummyModelProvider` with a real provider adapter.
- Expand deterministic facts into richer signal scoring and portfolio context.
- Add authenticated channel delivery implementations.
