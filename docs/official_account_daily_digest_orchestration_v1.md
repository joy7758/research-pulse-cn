# Official-Account Daily Digest Orchestration v1

## Why Digest Orchestration Is Added After Core Pulse Cards Exist
- The digest layer already had selected `PulseCard` rows and publication-preparation reserve objects.
- This phase turns that reserve into one deterministic daily packet instead of a loose highlight list.
- Orchestration still consumes already selected cards only:
  - no AI copywriting
  - no real-time external retrieval
  - no new delivery channel

## Stable Section Model
- Daily digest payloads now use a fixed section model:
  1. `today_focus`
  2. `yesterday_recap`
  3. `signal_updates`
  4. `related_papers`
  5. `other_updates`
- Selection rules stay deterministic:
  - `today_focus`
    - prefer one `today_suggestion`
    - fallback to one `next_action`
    - fallback to one `stalled_progress` or `deadline_risk`
  - `yesterday_recap`
    - at most one `yesterday_summary`
  - `signal_updates`
    - `signal_change` cards up to `APP_DIGEST_SIGNAL_UPDATES_MAX_ITEMS`
  - `related_papers`
    - `related_paper` cards up to `APP_DIGEST_RELATED_PAPERS_MAX_ITEMS`
  - `other_updates`
    - remaining selected cards up to `APP_DIGEST_OTHER_UPDATES_MAX_ITEMS`
- A selected `PulseCard` can appear in at most one section.

## Digest Payload Structure
- `PulseDigestIssue.content_payload` now carries a publication-friendly daily structure:
  - `issue_date`
  - `title`
  - `summary`
  - `section_order`
  - `sections`
  - `quick_stats`
  - `highlights`
  - `focus_card`
  - `publication_preview`
- Compatibility fields remain in place:
  - `deep_link_path`
  - `items`
  - `highlights`
  - `mini_program_path`
- Section items stay compact and deterministic:
  - `pulse_card_id`
  - `card_type`
  - `source_paper_id`
  - `title`
  - `summary`
  - `why_now`
  - `action_text`
  - `deep_link`

## Orchestration Vs Publication Preparation
- Orchestration:
  - rebuilds one digest issue per `user_id + issue_date`
  - reorganizes already selected cards into the fixed section model
  - updates `title`, `summary`, and `content_payload`
- Publication preparation:
  - still creates or updates `DigestPublicationJob` rows only
  - now prefers `content_payload.publication_preview` when present
  - does not dispatch sends by itself
- `POST /admin/digest-issues/orchestrate/{user_id}` can optionally trigger preparation when `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=true`.

## Auto-Prepare Behavior
- `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=false`
  - orchestration only
- `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=true`
  - orchestration also upserts prepared publication jobs for eligible official-account bindings
  - no real send is dispatched
  - repeated calls remain idempotent through the existing job upsert path
- If issue-level auto-dispatch is enabled later:
  - orchestration still owns section building
  - dispatch remains a separate issue-level step on top of prepared jobs
  - repeated orchestration should not resend already-sent jobs
  - user-side delivery control remains a later gating layer and does not change section building

## Compatibility Notes For Desktop And Mini Read Models
- Mini digest detail payloads now expose the sectioned digest structure when present:
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
- Existing `highlights` and `items` remain available so older compact readers do not break.
- Desktop and sync compatibility stays additive in this phase:
  - digest sync payloads continue to expose `highlights` and `items`
  - sectioned fields are added without requiring desktop admin/orchestration calls
  - desktop Today now prefers the structured digest payload when present and falls back to legacy highlights/items otherwise
- Mini compatibility now also stays additive:
  - mini read-only endpoints prefer the structured digest payload
  - mini falls back deterministically to legacy highlights/items
  - mini remains read-only and separate from self-service edit flows

## Current Non-Goals
- AI copywriting or summary generation
- new delivery channels
- broadcast or campaign orchestration
- `related_news`
- real-time retrieval during digest orchestration
- major desktop UI changes

## Future Work
- richer publication formatting for official-account templates
- digest feedback loops on section usefulness
- optional section personalization
- later news integration only if justified by the product boundary
