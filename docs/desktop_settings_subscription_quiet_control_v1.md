# Desktop Settings Subscription Quiet Control v1

## Why Desktop Is Now Exposing Delivery-Control Settings
- Desktop already cached `SubscriptionPolicy` rows through sync.
- This phase surfaces the existing quiet-control fields directly in Settings so users can edit them without adding a new desktop-only policy store.
- The desktop shell still does not call admin-only dispatch or delivery-control preview endpoints.

## Reused Backend Policy Fields
- The desktop editor reuses:
  - `SubscriptionPolicy.enabled`
  - `SubscriptionPolicy.quiet_hours`
  - `SubscriptionPolicy.frequency_cap`
  - `SubscriptionPolicy.policy.timezone`
  - `SubscriptionPolicy.policy.allowed_weekdays`
  - `SubscriptionPolicy.policy.muted_until`
  - `SubscriptionPolicy.policy.minimum_selected_cards`
  - `SubscriptionPolicy.policy.skip_if_no_today_focus`
- Weekday numbering stays aligned with the backend:
  - `0 = Monday`
  - `6 = Sunday`

## Local Hint Vs Authoritative Backend Decision
- Settings now shows a local-only hint panel from cached policy data plus current local time.
- The local hint can flag:
  - quiet hours currently active
  - muted-until currently active
  - weekday currently blocked
  - approximate next allowed local time when it can be derived
- The local hint does not evaluate digest-content gates such as:
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- The backend remains authoritative for actual dispatch eligibility.

## Supported Editable Fields
- `enabled`
- quiet hours start / end
- `timezone`
- `allowed_weekdays`
- `muted_until`
- `minimum_selected_cards`
- `skip_if_no_today_focus`
- `frequency_cap`

## Writeback Flow Through Sync Mutations
- Desktop reads from cached `subscription_policy_cache`.
- Settings writes still queue only:
  - `subscription_policy.patch`
- The mutation goes through:
  1. `queueSubscriptionPolicyPatch`
  2. local mutation outbox
  3. `POST /sync/push`
  4. authoritative `SyncEvent` apply back into the desktop cache
- Pending and failed mutation state stays visible in Settings.

## Current Non-Goals
- new delivery channels
- direct admin preview or dispatch calls from desktop
- OAuth or user-facing binding flows
- campaign or broadcast logic
- AI policy suggestions

## Future Work
- user-facing authoritative eligibility preview
- client-driven snooze actions
- richer schedule controls
- mini-client policy editing if ever justified
