# Sync Foundation

## Why Sync Is Now First-Class
- The desktop client needs a durable way to read cloud-side paper state and push local edits back without inventing a second backend model.
- Future lightweight clients should reuse the same feed, cursor, and mutation backbone instead of adding one-off read APIs.
- Future official-account digest publishing should also consume the same persisted paper, pulse, and delivery state rather than a separate messaging-specific data path.

## Device Identity Model
- `ClientDevice` links one client installation to one `UserProfile`.
- Supported client types in v1:
  - `desktop`
  - `mobile`
- Devices are operator-managed from `/admin/client-devices`.
- A revoked or inactive device can no longer authenticate to `/sync/*`.

## Token Model
- Device tokens are distinct from:
  - admin JWT + refresh token auth
  - internal service bearer token auth
- Plaintext device tokens are returned only when:
  - a device is created
  - a token is rotated
- Only token hashes are stored at rest in `client_access_tokens`.
- Device tokens are valid only on `/sync/*`.

## Sync Event Model
- `SyncEvent` is the append-only user-scoped event log for client consumption.
- Each event has:
  - a UUID id
  - a monotonic `sequence`
  - `user_id`
  - `entity_type`
  - `entity_id`
  - `event_type`
  - `payload`
  - `event_source`
  - `occurred_at`
- Events emitted in v1 cover:
  - paper profile create/update
  - progress event create
  - signal snapshot create
  - subscription policy create/update
  - pulse card persistence
  - pulse digest issue create/update

## Mutation Model
- `SyncMutation` records each device-originated write keyed by `(client_device_id, client_mutation_id)`.
- Supported statuses:
  - `accepted`
  - `applied`
  - `duplicate`
  - `failed`
- Supported mutation types in v1:
  - `paper.patch`
  - `progress_event.create`
  - `subscription_policy.patch`

## Feed Ack Push Flow
1. Device authenticates with its bearer token.
2. `GET /sync/feed` reads ordered events strictly after:
   - the supplied `after_sequence`, or
   - the device cursor if `after_sequence` is omitted.
3. Device applies events locally.
4. `POST /sync/ack` advances the server-side cursor forward only.
5. `POST /sync/push` submits idempotent mutations with `client_mutation_id`.
6. Successful mutations go through the existing service layer and emit new `SyncEvent` rows.

## Idempotency Rules
- `client_mutation_id` is unique per device.
- Repeating the same mutation id does not reapply the change.
- `POST /sync/ack` is forward-only:
  - higher sequence moves the cursor
  - same or lower sequence is accepted without rewinding

## Current Limitations
- Conflict handling is last-write-wins for supported patch operations.
- There is no CRDT or field-level merge strategy in v1.
- Device auth is admin-managed only; no end-user self-service device registration exists.
- Delivery job status changes are not yet emitted as sync events.
- WeChat identity bindings and publication jobs are intentionally kept out of sync in v1.
- Legacy `dingtalk` and `wechat` enum values remain only for compatibility with older rows and are rejected for new policy writes.
- Desktop clients currently use read-only pull sync only; write-back mutations from the desktop shell are deferred to a later phase.

## Future Work
- desktop write-back sync
- official-account digest publishing
- mini-program lightweight client access
- richer sync conflict handling
- offline batching heuristics and mutation compaction
- broader entity coverage such as delivery status and analytics snapshots
