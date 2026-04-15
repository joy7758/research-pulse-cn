# Pulse Scoring v1

## Input-layer boundary
- Pulse scoring now has an explicit upstream input layer documented in `docs/pulse_input_layer_v1.md`.
- That layer provides:
  - `WorkActivityEvent` for recent user-work signals
  - `ResearchWatchProfile` for compact watch interests
  - `GET /pulse/input-preview/{user_id}` for deterministic input inspection
  - `today_suggestion` facts built from internal paper/progress/signal state
  - `yesterday_summary` facts built from previous-local-day work activity only
  - persisted normalized scholarly records available for downstream `related_paper` candidate generation
- This scoring document still covers candidate generation, ranking, suppression, and selection only.
- Retrieval execution is already separated behind the external-retrieval boundary, but pulse still consumes persisted normalized records only.

## Pipeline stages
Pulse generation now follows an explainable deterministic pipeline:

1. Facts
   Deterministic facts are collected from paper state.
2. Candidates
   Facts are converted into typed pulse candidates.
3. Scoring
   Each candidate gets a weighted score and machine-readable breakdown.
4. Suppression
   Candidates can be suppressed without being deleted from diagnostics.
5. Selection
   Remaining candidates are sorted deterministically and capped.
6. Card generation
   Only selected candidates are rendered into final pulse cards.
7. Delivery
   Only selected cards create delivery jobs.

## Candidate types
Current candidate generation supports:
- `signal_change`
- `stalled_progress`
- `deadline_risk`
- `today_suggestion`
- `next_action`
- `yesterday_summary`
- `related_paper`

Notes:
- `today_suggestion` is built from one selected actionable paper and usually persists with `source_paper_id`.
- `today_suggestion` supports `execute_next_action`, `resolve_blocker`, and `define_next_action`.
- `yesterday_summary` is global, not paper-centric, and may persist with `source_paper_id = null`.
- `yesterday_summary` is generated only when the previous local day has qualifying non-system work activity.
- `related_paper` is now generated only from persisted `ExternalRetrievedRecord` rows whose parent run completed successfully.
- `related_paper` never triggers retrieval during pulse preview/run.
- `paused` papers do not produce candidates.

## Scoring knobs
Defaults come from application settings and can be overridden per user through `SubscriptionPolicy.policy["pulse"]`.

Supported knobs:
- `stale_days`
- `deadline_horizon_days`
- `dedupe_window_hours`
- `min_score`
- `max_cards_per_run`
- `score_weights`
- `urgency_modifiers`
- `today_suggestion_stale_days_threshold`
- `today_suggestion_priority_bonus`
- `today_suggestion_has_next_action_bonus`
- `today_suggestion_revision_stage_bonus`
- `today_suggestion_stale_progress_bonus`
- `today_suggestion_blocker_present_bonus`
- `yesterday_summary_min_events`
- `yesterday_summary_activity_diversity_bonus`
- `yesterday_summary_multi_paper_bonus`
- `related_paper_lookback_days`
- `related_paper_max_candidates_per_run`
- `related_paper_dedupe_days`
- `related_paper_has_doi_bonus`
- `related_paper_match_reason_count_bonus`
- `related_paper_linked_paper_bonus`
- `related_paper_recent_retrieval_bonus`

Default urgency modifiers currently cover:
- recent signal delta
- approaching deadline
- long stagnation
- explicit next action present

## Suppression rules
Suppression happens after scoring and before final selection.

Current suppression reasons:
- `quiet_hours`
- `dedupe_window`
- `low_score`
- `paused_paper`
- `frequency_cap`

Important behavior:
- quiet hours suppress candidates but keep them visible in preview diagnostics
- frequency cap is applied only after other suppression rules are evaluated
- dedupe uses the same user + card type + source paper signature inside the configured dedupe window
- `today_suggestion` dedupe uses user + source paper + suggestion kind + action context
- `yesterday_summary` dedupe uses the same user + `summary_date` + card type inside the configured dedupe window
- `related_paper` dedupe uses the same user + canonical `external_reference_key` inside `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`

## Tie-break behavior
When scores tie, candidates are ordered by:
1. explicit card type order
2. source timestamp descending
3. paper title ascending
4. candidate id ascending

This ordering is deterministic and covered by tests.

## Preview diagnostics
`POST /pulse/preview/{user_id}` returns:
- fact summary
- collected facts
- generated candidates
- selected cards
- suppressed candidates
- score breakdowns
- final ordering explanation
- optional effective-timezone inspection via `?timezone=Asia/Shanghai`

## Where model providers plug in
Real model providers should plug in after selection, not before.

That keeps:
- fact collection deterministic
- scoring explainable
- suppression auditable
- model cost limited to selected candidates only

## Known limitations in v1
- `related_paper` depends only on already-persisted normalized retrieval records and does not yet apply richer ranking beyond deterministic scoring
- pulse preview/run intentionally do not trigger retrieval execution
- `today_suggestion` is intentionally heuristic and does not yet suppress itself when a similar `next_action` card covers the same context
- `yesterday_summary` is previous-day-only and does not yet support multi-day rollups
- quiet hours use policy-local window definitions and assume valid timezones
- dedupe is signature-based and does not yet use richer semantic similarity
- scoring is weighted and explainable, but not yet calibrated from operational feedback
