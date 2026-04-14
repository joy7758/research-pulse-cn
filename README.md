# Research Pulse CN

Commercial closed-source backend for a China-focused research paper lifecycle and pulse subscription system.

## Repository status
Private repository. Proprietary and confidential.

## What is included
- FastAPI backend with OpenAPI docs
- SQLAlchemy 2 models and Alembic migration
- CRUD APIs for users, papers, progress events, signal snapshots, and subscription policies
- Deterministic pulse preview and run flow
- Outbox-style delivery jobs with retry and dead-letter transitions
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
6. Seed demo data:
   `make seed`
7. Run the API:
   `make run`

Open API docs at `http://127.0.0.1:8000/docs`.

## Common commands
- `make install`: install runtime and dev dependencies
- `make run`: run the FastAPI development server
- `make migrate`: apply Alembic migrations
- `make seed`: load local demo data
- `make worker`: process pending pulse and delivery jobs once
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
- `APP_MAX_DELIVERY_RETRIES`: retry ceiling before dead-letter
- `APP_DELIVERY_RETRY_DELAY_SECONDS`: retry backoff in seconds

## Running the worker
The worker can be run once for local verification:

`make worker`

For a continuously polling worker:

`python -m research_pulse_cn.worker.main --limit 20 --poll-interval 15`

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
