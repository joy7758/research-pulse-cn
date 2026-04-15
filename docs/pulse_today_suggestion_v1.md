# Pulse Today Suggestion v1

## Why Today Suggestion Is Added Before External Retrieval
- The pulse system can already identify one useful internal next step without calling external retrieval or model-based recommendation logic.
- `today_suggestion` keeps the next-step experience grounded in current structured state:
  - `PaperProfile`
  - `ProgressEvent`
  - `SignalSnapshot`
  - subscription-policy timezone context
- This keeps the pulse pipeline explainable while external retrieval remains deferred.

## Eligible Paper Selection Rules
- Eligible active paper types:
  - `in_prep`
  - `under_review`
  - `revision`
- Excluded:
  - `paused`
- `published` papers are considered only when both are true:
  - they already have an explicit `next_action`
  - they have a recent internal signal snapshot within the configured stale-days threshold
- The builder produces at most one `today_suggestion` candidate per user per pulse run.
- If no actionable paper exists, no candidate is generated.

## Suggestion Kinds
- `execute_next_action`
  - chosen when `next_action` exists and `blocker` is empty
- `resolve_blocker`
  - chosen when `blocker` exists
- `define_next_action`
  - chosen when the paper is active but no `next_action` is defined
- All title, summary, why-now, and action text are deterministic and concise.
- No AI generation is used.

## Scoring, Suppression, And Dedupe
- Current stable card type order is:
  - `signal_change`
  - `deadline_risk`
  - `stalled_progress`
  - `today_suggestion`
  - `next_action`
  - `yesterday_summary`
  - `related_paper`
- Current scoring knobs are:
  - `APP_PULSE_WEIGHT_TODAY_SUGGESTION`
  - `APP_PULSE_MODIFIER_TODAY_SUGGESTION_PRIORITY`
  - `APP_PULSE_MODIFIER_TODAY_SUGGESTION_HAS_NEXT_ACTION`
  - `APP_PULSE_MODIFIER_TODAY_SUGGESTION_REVISION_STAGE`
  - `APP_PULSE_MODIFIER_TODAY_SUGGESTION_STALE_PROGRESS`
  - `APP_PULSE_MODIFIER_TODAY_SUGGESTION_BLOCKER_PRESENT`
  - `APP_PULSE_TODAY_SUGGESTION_STALE_DAYS_THRESHOLD`
- Required score-breakdown modifier keys are:
  - `today_suggestion_priority`
  - `today_suggestion_has_next_action`
  - `today_suggestion_revision_stage`
  - `today_suggestion_stale_progress`
  - `today_suggestion_blocker_present`
- Suppression still respects:
  - quiet hours
  - low score
  - frequency cap
  - dedupe window
- Dedupe now uses:
  - `user_id`
  - `source_paper_id`
  - `suggestion_kind`
  - `action_context`
- Cross-card suppression against `next_action` is still deferred in this phase.

## Pulse Preview And Run Implications
- `POST /pulse/preview/{user_id}` can now expose one `today_suggestion` candidate with:
  - `suggestion_kind`
  - chosen paper metadata
  - score breakdown
  - suppression reasons when applicable
  - top reason codes and selection context
- `POST /pulse/run/{user_id}` persists the selected `today_suggestion` as a normal `PulseCard`.
- Persisted `candidate_metadata` preserves:
  - `suggestion_kind`
  - reason codes
  - paper/action context
  - effective timezone

## Digest Compatibility Notes
- Digest building tolerates selected `today_suggestion` cards without special branching.
- In this phase, `today_suggestion` is usually paper-centric:
  - `source_paper_id` is normally set
- Compact digest and mini/desktop read payloads still should not assume every card shares the same metadata shape.
- Desktop compatibility is limited to type and Today-view tolerance in this phase.

## Current Non-Goals
- no external academic retrieval
- no news retrieval
- no AI advice generation
- no generic recommendation feed
- no new delivery channel
- no syncing local file or note contents to the backend

## Future Work
- external academic retrieval inputs
- related-paper and related-news cards
- richer today-suggestion heuristics
- user feedback loops for suggestion quality
- smarter suppression across overlapping internal action cards
