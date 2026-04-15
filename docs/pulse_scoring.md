# Pulse Scoring v1

## Input-layer boundary
- Pulse scoring now has an explicit upstream input layer documented in `docs/pulse_input_layer_v1.md`.
- That layer provides:
  - `WorkActivityEvent` for recent user-work signals
  - `ResearchWatchProfile` for compact watch interests
  - `GET /pulse/input-preview/{user_id}` for deterministic input inspection
  - `today_suggestion` facts built from internal paper/progress/signal state
  - `yesterday_summary` facts built from previous-local-day work activity only
- This scoring document still covers candidate generation, ranking, suppression, and selection only.
- External retrieval is still deferred until the input layer is stable.

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
- `related_paper` is intentionally conservative in v1 and uses simple within-portfolio heuristics.
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
- `related_paper` uses simple heuristics and does not use external research graphs
- upstream watch seeds are available, but external retrieval is not implemented yet
- `today_suggestion` is intentionally heuristic and does not yet suppress itself when a similar `next_action` card covers the same context
- `yesterday_summary` is previous-day-only and does not yet support multi-day rollups
- quiet hours use policy-local window definitions and assume valid timezones
- dedupe is signature-based and does not yet use richer semantic similarity
- scoring is weighted and explainable, but not yet calibrated from operational feedback
