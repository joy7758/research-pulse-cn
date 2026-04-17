# Subscription Boundary And Quiet Control v1

## Why User-Side Delivery Control Is Added After Issue-Level Dispatch Exists
- The system already had:
  - `SubscriptionPolicy`
  - deterministic daily digest orchestration
  - issue-level official-account dispatch runs
  - provider readiness and real/dry-run boundaries
- This phase adds a separate user-side policy gate before send:
  - quiet hours
  - temporary mute
  - weekday allow-lists
  - minimum digest-content thresholds
- The goal is to keep "provider can send" separate from "policy allows sending now".

## Normalized SubscriptionPolicy Delivery Controls
- This phase still reuses `SubscriptionPolicy`; it does not add a new channel system.
- Delivery control uses:
  - `SubscriptionPolicy.channel`
  - `SubscriptionPolicy.enabled`
  - `SubscriptionPolicy.quiet_hours`
  - `SubscriptionPolicy.policy`
- Supported `policy` keys in v1:
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- `quiet_hours` remains outside `policy` JSON and is normalized separately.
- Weekday numbering is deterministic:
  - `0 = Monday`
  - `6 = Sunday`
- Effective timezone resolution:
  1. `policy.timezone`
  2. app default timezone

## DigestDeliveryDecision Model
- `DigestDeliveryDecision` records one delivery-policy decision snapshot for one digest issue.
- Key fields:
  - `digest_issue_id`
  - `user_id`
  - `channel`
  - `subscription_policy_id`
  - `dispatch_run_id`
  - `decision`
  - `reason_codes`
  - `effective_timezone`
  - `local_issue_weekday`
  - `selected_card_count`
  - `focus_card_type`
  - `quiet_hours`
  - `muted_until`
  - `next_allowed_at`
  - `created_at`
- This model is not a replacement for publication attempts or audit logs.

## Delivery-Control Preview Behavior
- `GET /admin/digest-issues/{digest_issue_id}/delivery-control-preview` returns:
  - digest issue summary
  - matched subscription policy summary for `official_account`
  - normalized control policy
  - current local time and weekday
  - `eligible` or `skipped`
  - deterministic `reason_codes`
  - `next_allowed_at` when it can be computed
- Required reason codes in v1:
  - `policy_disabled`
  - `quiet_hours_active`
  - `muted_until_active`
  - `weekday_blocked`
  - `insufficient_selected_cards`
  - `missing_today_focus`
  - `no_digest_content`
  - `no_subscription_policy`

## Dispatch Integration
- `GET /admin/digest-issues/{digest_issue_id}/dispatch-preview` now embeds:
  - provider readiness
  - publication job counts
  - `delivery_control_preview`
- `POST /admin/digest-issues/{digest_issue_id}/dispatch` now evaluates delivery control first.
- If policy blocks dispatch:
  - a `DigestDeliveryDecision` row is persisted
  - the response returns a controlled `skipped` result
  - no fake send is recorded
  - no fake success is recorded
  - no `DigestDispatchRun` is created for this policy-blocked path in v1
- If policy is eligible:
  - a `DigestDeliveryDecision` row is persisted
  - existing issue-level dispatch continues unchanged

## Auto-Dispatch Interaction
- Auto-dispatch after orchestration still depends on:
  - `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT`
  - `APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT`
- Auto-dispatch now also evaluates delivery control before send.
- If policy blocks:
  - no dispatch run is created
  - a `DigestDeliveryDecision` row is written
  - orchestration metadata records the skip reason
- If `APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE=true` and the provider is not real-ready:
  - this remains a provider skip
  - it is not rewritten into a policy skip

## Desktop Settings Integration
- Desktop now reuses the same normalized policy fields from cached `SubscriptionPolicy` rows.
- The Settings screen can edit:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- Desktop still writes only through `queueSubscriptionPolicyPatch -> /sync/push`.
- Desktop local hints are best-effort only and do not replace backend delivery-control evaluation.

## Self-Service Reserve Compatibility
- A separate self-service reserve boundary can now reuse the same normalized delivery-control fields without reusing admin auth.
- `/subscription-self-service/settings` supports only the same safe editable subset:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- `/subscription-self-service/delivery-control-preview` is authoritative for current backend state, unlike desktop local hints.
- A later editor-reserve layer can reuse the same normalization and evaluator path through:
  - `GET /subscription-self-service/editor-contract`
  - `POST /subscription-self-service/settings/preview`

## Provider Readiness Vs Policy Eligibility Distinction
- Provider readiness answers:
  - can the official-account provider execute safely?
- Policy eligibility answers:
  - should this user receive the digest right now?
- Both are required for a real dispatch.
- The system now exposes them separately in preview and orchestration metadata.

## Current Non-Goals
- new delivery channels
- OAuth login or user-facing binding flows
- campaign or broadcast logic
- AI-based send-policy decisions
- new desktop or mini UI surfaces for editing preferences

## Future Work
- user self-service editing for digest quiet controls
- richer delivery preferences
- per-section opt-in and opt-out
- client-driven temporary snooze actions
