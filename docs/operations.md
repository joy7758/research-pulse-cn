# Operations Guide

## Scope
Phase 6 adds operations-grade visibility around the existing pulse pipeline without replacing the modular monolith.

Primary goals in v1:
- stable daily scheduling
- operational inspection
- replay and requeue controls
- worker heartbeat visibility
- delivery attempt tracking
- lightweight health and metrics endpoints

## Scheduler Model
The scheduler creates `PulseJob` rows. It does not run the pulse pipeline directly.

What is automated in v1:
- enabled `SubscriptionPolicy` rows with `frequency = daily`

What is not automated in v1:
- `frequency = event` policies
- backfill scheduling across missed historical dates
- real channel-specific scheduling windows

### Scheduling keys
Each daily schedule uses a stable key:

`daily:{subscription_policy_id}:{local_date}`

That key is stored in `pulse_jobs.schedule_key` and protected by a unique constraint, so repeated scheduler ticks do not create duplicate jobs for the same policy and local date.

### Local-time calculation
The scheduler computes due-ness in the policy's local timezone and persists `scheduled_for` in UTC.

Supported policy JSON keys:
- `schedule.timezone`
- `schedule.send_hour_local`
- `schedule.send_minute_local`

Fallbacks come from application settings:
- `APP_DEFAULT_TIMEZONE`
- `APP_PULSE_DEFAULT_SEND_HOUR_LOCAL`
- `APP_PULSE_DEFAULT_SEND_MINUTE_LOCAL`

## Pulse Job Lifecycle
`PulseJob` now carries enough state for operational inspection:
- `subscription_policy_id`
- `scheduled_reason`
- `schedule_key`
- `started_at`
- `completed_at`
- `failed_at`
- `lease_owner`
- `lease_expires_at`

`scheduled_reason` values in v1:
- `manual_run`
- `daily_schedule`
- `replay`

The worker claims pending jobs with a lease before processing them. This keeps repeated polling cycles from picking up the same pending job concurrently.

## Worker Heartbeats
Heartbeats are stored in `worker_heartbeats`.

Tracked fields:
- `worker_name`
- `worker_role`
- `status`
- `hostname_or_instance`
- `pid`
- `started_at`
- `last_heartbeat_at`
- `metadata`

Tracked roles in v1:
- `scheduler`
- `delivery_worker`

## Delivery Attempt Tracking
Each outbound send creates a `DeliveryAttempt` row.

Attempt statuses:
- `started`
- `sent`
- `failed`

This keeps the current outbox architecture intact while exposing every adapter invocation for debugging and replay analysis.

## Ops Endpoints
### Health
- `GET /health`: basic service health
- `GET /health/live`: lightweight liveness
- `GET /health/ready`: readiness with component details

### Metrics
- `GET /ops/metrics`

Prometheus-style counters exposed in v1:
- `scheduler_ticks_total`
- `scheduler_jobs_created_total`
- `pulse_jobs_completed_total`
- `pulse_jobs_failed_total`
- `pulse_cards_selected_total`
- `delivery_jobs_sent_total`
- `delivery_jobs_failed_total`
- `delivery_jobs_dead_letter_total`
- `sync_events_emitted_total`
- `sync_feed_requests_total`
- `sync_mutations_received_total`
- `sync_mutations_applied_total`
- `sync_mutations_failed_total`

### Inspection
- `GET /ops/heartbeats`
- `GET /ops/pulse-jobs`
- `GET /ops/delivery-jobs`
- `GET /ops/delivery-attempts`

These endpoints support light filtering by status, user, and recent time windows where relevant.

### Control
- `POST /ops/scheduler/tick`
- `POST /ops/delivery-jobs/{delivery_job_id}/requeue`
- `POST /ops/pulse-jobs/{pulse_job_id}/replay`

## Replay And Requeue Semantics
### Replay
Replay creates a new `PulseJob` with `scheduled_reason = replay` and `source_pulse_job_id` pointing to the original job.

Idempotency behavior:
- if the source job is already active, the API returns that active state
- if an active replay already exists, the API returns the existing replay
- otherwise a new replay job is created

### Requeue
Requeue reactivates an existing failed or dead-letter `DeliveryJob` by moving it back to `pending`.

Idempotency behavior:
- pending or sending jobs are returned as already active
- sent jobs are returned as already sent
- failed or dead-letter jobs are moved back to pending

## Local Commands
- `make run-api`
- `make worker`
- `make run-worker`
- `make scheduler-tick`
- `make run-scheduler`
- `make lint`
- `make test`

## Known Limitations
- Metrics are process-local counters, not a distributed metrics backend.
- Event policies are not auto-scheduled yet.
- Scheduler v1 creates jobs for the current local date only and does not backfill missed runs.
- Redis is not yet used as a coordination backend for scheduling or delivery leases.
- Device sync is last-write-wins and does not attempt multi-device merge semantics.
- Official-account digest publishing and mini-program client surfaces are future work.

## Future Work
- event-driven scheduling for `frequency = event`
- persistent shared metrics and richer gauges
- stronger distributed worker coordination
- official-account digest publishing on top of persisted pulse data
- mini-program lightweight client access on top of sync feeds
- alerting hooks and trace correlation across external providers
