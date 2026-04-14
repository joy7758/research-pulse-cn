# Official-Account Digest Reserve

## Why Digest Is Separate
- `PulseCard` is still the ranked atomic output of the pulse pipeline.
- `PulseDigestIssue` is the daily digest artifact built from already selected cards.
- Keeping digest separate prevents future official-account publishing and mini-program landing flows from coupling themselves to outbox delivery internals.

## Why WeChat Binding Is Modeled Now
- Future official-account and mini-program work will need a shared identity anchor.
- `WeChatIdentityBinding` lets the backend model `official_account` and `mini_program` identities before real OAuth or provider calls exist.
- This keeps later provider work additive instead of forcing a schema rewrite.

## WeChatIdentityBinding Model
- One row represents one admin-managed WeChat-side identity binding.
- Key fields:
  - `user_id`
  - `channel_type`
  - `app_id`
  - `openid`
  - `unionid`
  - `bind_state`
  - `subscribed`
  - `digest_enabled`
  - `display_label`
  - timestamps and metadata
- Current boundary:
  - no real OAuth
  - no real subscription callbacks
  - no assumption that one business user will always have only one binding

## PulseDigestIssue And PulseDigestItem Model
- `PulseDigestIssue` is unique per `user_id + issue_date`.
- It stores deterministic digest metadata:
  - status
  - title
  - summary
  - highlight counts
  - deep-link placeholder
  - machine-readable content payload
  - build metadata
- `PulseDigestItem` stores the stable ordered snapshot of selected cards for the issue.
- Digest items are derived from existing `PulseCard` rows only.
- The digest builder does not re-score or re-run pulse selection.

## DigestPublicationJob Model
- `DigestPublicationJob` is the future publication reserve record.
- It links one digest issue to one publication target and optional binding.
- In v1 it stores:
  - target
  - status
  - publish mode
  - provider name
  - prepared payload
  - timestamps and last error
- Jobs in this phase are preview or preparation artifacts only.

## Build Vs Prepare-Publication Flow
1. Pulse run selects `PulseCard` rows.
2. Pulse completion auto-upserts one `PulseDigestIssue` for the user-local date.
3. Admins can rebuild the same issue idempotently for the same `user_id + issue_date`.
4. Admins can prepare publication.
5. The stub publication layer finds eligible official-account bindings and writes `DigestPublicationJob` rows.
6. No external send occurs.

## Current Non-Goals
- Real WeChat Official Account API integration
- Real Mini Program API integration
- OAuth or end-user binding flows
- Customer-facing UI
- Turning WeChat back into a direct `DeliveryJob` message channel

## Current Limitations
- Binding lifecycle is admin-managed only.
- Publication payloads are provider-neutral previews, not real sends.
- Publication jobs are not exposed through sync in v1.
- Digest generation uses deterministic summaries only.
- Deep links are placeholders for future mini-program landing routes.

## Future Work
- real official-account provider integration
- mini-program landing and read-only client
- real binding and OAuth flows
- richer digest composition and editorial controls
