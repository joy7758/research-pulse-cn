# User Subscription Self-Service Editor Reserve v1

## Why Editor Reserve Is Added After Self-Service Reserve And OAuth Completion Exist
- The repository already has:
  - narrow self-service grant auth
  - safe official-account settings reads and patching
  - authoritative delivery-control preview
  - official-account OAuth completion for binding handoff
- This phase adds the machine-readable contract and preview-before-save layer needed by a future user-facing editor page.
- The goal is to stabilize API and data semantics before building real mini/web editing UI.

## Editor Bootstrap And Editor Contract
- New self-service editor endpoints:
  - `GET /subscription-self-service/editor-bootstrap`
  - `GET /subscription-self-service/editor-contract`
- `editor-bootstrap` returns:
  - safe grant summary
  - safe user summary
  - safe official-account binding summary
  - current normalized settings draft
  - latest digest summary when available
  - `authoritative_preview_supported = true`
  - a compact `self_service_entry` handoff block
- `editor-contract` returns:
  - `contract_version = "v1"`
  - deterministic sections
  - deterministic field definitions
  - validation hints
  - weekday numbering note

## Preview-Before-Save Semantics
- New preview endpoint:
  - `POST /subscription-self-service/settings/preview`
- Preview accepts the same safe editable subset as save.
- Preview does not persist:
  - no `SubscriptionPolicy` write
  - no `DigestDeliveryDecision` write
- Preview performs:
  1. field normalization
  2. deterministic validation
  3. hypothetical merged-policy shaping
  4. authoritative delivery-control evaluation when digest context exists
- Preview states:
  - `ready`
  - `no_digest_context`
  - `invalid_input`

## Authoritative Preview Vs Local Hint Vs Mini Read-Only Summary
- Self-service editor preview is authoritative because it uses the backend delivery-control evaluator directly.
- Desktop Settings still exposes a local hint only and does not become authoritative through this reserve.
- Mini remains read-only and only receives a compact `self_service_entry` / reserve summary that explains how future editing handoff will work.
- Mini reserve can now also mint a short-lived `SubscriptionEditorHandoffGrant` through a separate mini-protected handoff path, but that token is still derived from the self-service grant boundary rather than replacing it.
- The reusable contract/bootstrap/preview/save shaping can now also be consumed through a shared frontend core without changing the self-service or handoff auth boundaries.

## Supported Editable Fields
- v1 editable field ids:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- v1 supporting read-only fields:
  - `channel`
  - `latest_digest_summary`
  - `official_account_binding_summary`
  - `authoritative_preview_supported`
  - `self_service_grant_status`
- Unknown existing `SubscriptionPolicy.policy` keys are preserved during preview/save preparation and are not dropped by safe-field patching.

## Validation Model
- Validation is deterministic and shared between preview and save preparation.
- Rules in v1:
  - `quiet_hours` must be an object or null and must normalize into valid quiet-hour windows
  - `timezone` must be a non-empty string
  - `allowed_weekdays` must be integers in `0..6`
  - weekday numbering is `0 = Monday` through `6 = Sunday`
  - `minimum_selected_cards` must be an integer `>= 0`
  - `skip_if_no_today_focus` must be boolean
  - `muted_until` must be null or an ISO 8601 datetime string
- Preview returns field-specific `validation_errors` instead of persisting partial state.

## Current Non-Goals
- new delivery channels
- real mini/web editing UI
- desktop UI work
- generic end-user login/session system
- campaign or broadcast logic
- AI preference suggestions or copywriting
- group workspace sharing or source-file sharing

## Future Work
- real user-facing web/mobile editor page
- the current thin `apps/subscription-editor-web` shell can evolve into a richer editor without changing the backend contract
- mini-based editing handoff
- short-lived mini editor handoff token exchange
- richer schedule controls
- self-service analytics or audit views
