# Desktop Writeback Sync v1

## Why Desktop Writeback Stays Inside Sync Mutations
- Desktop writes now go through the same `/sync/push` mutation contract used by the broader sync backbone.
- The desktop shell still does not call business CRUD endpoints directly.
- This keeps device auth, auditing, validation, and server-side event emission aligned on one path.

## Local Mutation Outbox Model
- Desktop SQLite now persists:
  - `mutation_outbox`
  - `subscription_policy_cache`
- `mutation_outbox` stores one row per local mutation with:
  - `client_mutation_id`
  - mutation/resource identifiers
  - payload
  - status
  - attempt count
  - last error
  - resulting event sequence
- Supported statuses in v1:
  - `queued`
  - `sending`
  - `applied`
  - `duplicate`
  - `failed`

## Push-Before-Pull Sync Flow
1. Load queued and failed mutations in stable order.
2. Mark them as `sending` and submit them to `POST /sync/push`.
3. Record per-mutation results.
4. Pull fresh `SyncEvent` pages from `GET /sync/feed`.
5. Apply events to local SQLite sequentially.
6. Advance the server cursor with `POST /sync/ack` only after local apply succeeds.

The authoritative local cache still comes from server events, not direct optimistic mutation of cache tables.

## Authoritative Cache Model
- Paper, progress-event, signal, digest, and subscription-policy cache tables are read models.
- Desktop forms may queue mutations immediately, but the confirmed read state is only updated after the corresponding `SyncEvent` is applied locally.
- Failed mutations stay visible in the outbox and on affected paper/policy read models.

## Supported Mutation Types
- `paper.patch`
  - `stage`
  - `venue`
  - `next_action`
  - `blocker`
  - `priority`
  - `last_touch_at`
- `progress_event.create`
  - `stage`
  - `happened_at`
  - `summary`
  - `owner`
- `subscription_policy.patch`
  - `enabled`
  - `quiet_hours`
  - `frequency_cap`
  - `policy`
    - `timezone`
    - `allowed_weekdays`
    - `muted_until`
    - `minimum_selected_cards`
    - `skip_if_no_today_focus`

## Pending And Failed Mutation UX
- Paper list/detail now expose:
  - `pendingMutationCount`
  - `lastMutationError`
- Sync status now exposes:
  - `pendingMutationCount`
  - `failedMutationCount`
  - recent outbox errors
- Settings view shows:
  - cached subscription policies
  - delivery-control editor fields backed by synced cache
  - local-only quiet-control hint state
  - unresolved outbox rows
  - policy-level pending/error state

## Current Non-Goals
- no business CRUD calls from desktop
- no CRDT or field-level merge sophistication
- no offline background daemon
- no synced attachment or workspace management
- no synced local note files or note metadata
- no customer auth

## Future Work
- richer paper editing and batch operations
- local attachments and workspace structure beyond the v1 managed-copy layer
- background sync / retry loop
- stronger conflict handling and reconciliation UX
- stronger desktop secret storage and device hardening
