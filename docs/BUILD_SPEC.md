# Build Spec v0.1

## Goal
Implement the backend foundation for Research Pulse CN.

## Scope now
Backend only. Build a production-friendly modular monolith with:
- FastAPI app
- PostgreSQL persistence
- Redis for queue/cache support
- SQLAlchemy 2 + Alembic
- Pydantic v2
- Docker Compose
- pytest + ruff
- Makefile
- OpenAPI docs

## Core entities

### UserProfile
- id: UUID pk
- name: string
- email: string nullable unique
- field: string nullable
- interests: jsonb list
- watched_topics: jsonb list
- watched_venues: jsonb list
- reminder_preferences: jsonb object
- risk_thresholds: jsonb object
- created_at
- updated_at

### PaperProfile
- id: UUID pk
- user_id: UUID fk
- title: string
- title_zh: string nullable
- title_en: string nullable
- type: enum [published, under_review, revision, in_prep, paused]
- stage: string
- venue: string nullable
- identifiers: jsonb object
- source_links: jsonb list
- last_touch_at: datetime nullable
- next_action: string nullable
- blocker: string nullable
- priority: int default 3
- created_at
- updated_at

### ProgressEvent
- id: UUID pk
- paper_id: UUID fk
- stage: string
- happened_at: datetime
- summary: text
- evidence_links: jsonb list
- owner: string nullable

### SignalSnapshot
- id: UUID pk
- paper_id: UUID fk
- source: enum [CNKI, WANFANG, CQVIP, READPAPER, GOOGLE_SCHOLAR, MANUAL]
- citation_count: int nullable
- download_count: int nullable
- read_count: int nullable
- inclusion_status: string nullable
- fetched_at: datetime

### SubscriptionPolicy
- id: UUID pk
- user_id: UUID fk
- channel: enum [in_app, dingtalk, wechat, email, webhook]
- enabled: bool
- frequency: enum [daily, event]
- quiet_hours: jsonb object nullable
- frequency_cap: int default 3
- endpoint: string nullable
- policy: jsonb object

### PulseJob
- id: UUID pk
- user_id: UUID fk
- scheduled_for: datetime
- status: enum [pending, running, completed, failed]
- error: text nullable
- created_at
- updated_at

### PulseCard
- id: UUID pk
- pulse_job_id: UUID fk
- user_id: UUID fk
- card_type: enum [signal_change, stalled_progress, deadline_risk, next_action, related_paper]
- priority: int
- title: string
- summary: text
- why_now: text
- action_text: string nullable
- deep_link: string nullable
- evidence_refs: jsonb list
- generated_by: jsonb object
- generated_at: datetime

### DeliveryJob
- id: UUID pk
- pulse_card_id: UUID fk nullable
- pulse_job_id: UUID fk nullable
- user_id: UUID fk
- channel: enum [in_app, dingtalk, wechat, email, webhook]
- endpoint: string
- idem_key: string unique
- payload: jsonb object
- status: enum [pending, sending, sent, failed, dead_letter]
- retry_count: int default 0
- next_retry_at: datetime nullable
- last_error: text nullable
- created_at
- updated_at
- sent_at: datetime nullable

## Services and interfaces
Need interfaces and default implementations for:
- FactCollector
- RuleEngine
- ModelProvider
- CardValidator
- ChannelAdapter

Implementations for v0.1:
- DeterministicFactCollector
- DeterministicRuleEngine
- DummyModelProvider
- SimpleCardValidator
- ConsoleChannelAdapter
- DingTalkWebhookAdapter
- WeChatTemplateAdapter interface stub

## API endpoints
- GET /health
- CRUD /users
- CRUD /papers
- POST /papers/{paper_id}/progress-events
- GET /papers/{paper_id}/progress-events
- POST /papers/{paper_id}/signal-snapshots
- GET /papers/{paper_id}/signal-snapshots
- CRUD /subscription-policies
- POST /pulse/preview/{user_id}
- POST /pulse/run/{user_id}
- GET /delivery-jobs

## Worker
Implement a simple worker process that:
- finds pending PulseJob rows
- builds candidate facts
- generates PulseCard rows using DummyModelProvider
- enqueues DeliveryJob rows
- dispatches DeliveryJob rows through adapter registry
- supports retry and dead-letter state transition

## Infra
Create:
- pyproject.toml
- docker-compose.yml
- alembic config and migrations
- .env.example
- Makefile
- seed script with demo data
- docs/architecture.md
- basic CI workflow for lint + tests

## Quality bar
- code should run locally
- tests for model/service/api basics
- ruff configured
- keep repository commercial/private-ready
- do not add any OSS license
