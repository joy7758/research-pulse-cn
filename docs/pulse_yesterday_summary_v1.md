# Pulse Yesterday Summary v1

## Why Yesterday Summary Is Added Before External Retrieval
- The pulse pipeline now has enough internal input data to produce one useful recap without depending on crawlers or model calls.
- `WorkActivityEvent` already captures lightweight "what the user worked on" signals across API and desktop-originated actions.
- Adding a deterministic yesterday-summary card first hardens the pulse pipeline around explainable internal signals before external retrieval is introduced.

## Effective Timezone Resolution
- Yesterday summary uses one effective timezone for the target user.
- Resolution order is:
  - explicit `timezone` request parameter when provided
  - the first enabled daily `SubscriptionPolicy` timezone
  - `APP_DEFAULT_TIMEZONE`
- The summary window is always the previous local calendar day in that effective timezone.

## Yesterday Summary Builder Logic
- Builder input:
  - `user_id`
  - optional explicit timezone
  - optional target local date for deterministic tests
- Builder output is machine-readable and includes:
  - `summary_date`
  - `window_started_at`
  - `window_ended_at`
  - `total_events`
  - `activity_type_counts`
  - `touched_papers`
  - `distinct_activity_type_count`
  - `top_activity_types`
  - deterministic `text_summary`
- `source=system` work activity is excluded.
- No AI summarization is used.

## Card Generation, Scoring, And Suppression
- At most one `yesterday_summary` candidate is generated per user per pulse run.
- No candidate is generated when the previous local day has zero qualifying events.
- The candidate is global rather than paper-centric:
  - `source_paper_id` stays `null`
  - `candidate_metadata` carries `summary_date`, counts, and touched-paper details
- Current stable card type order is:
  - `signal_change`
  - `deadline_risk`
  - `stalled_progress`
  - `next_action`
  - `yesterday_summary`
  - `related_paper`
- Current scoring knobs are:
  - `APP_PULSE_WEIGHT_YESTERDAY_SUMMARY`
  - `APP_PULSE_YESTERDAY_SUMMARY_MIN_EVENTS`
  - `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_ACTIVITY_DIVERSITY`
  - `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_MULTI_PAPER`
- Suppression behavior remains aligned with the existing pulse pipeline:
  - quiet hours
  - low score
  - frequency cap
  - dedupe for the same `user_id + summary_date + card_type`

## Pulse Preview And Run Implications
- `POST /pulse/preview/{user_id}` can now expose a `yesterday_summary` candidate with:
  - deterministic title, summary, and why-now text
  - score breakdown
  - suppression reasons when applicable
  - summary-date metadata for inspection
- `POST /pulse/run/{user_id}` persists the card as a normal `PulseCard` when selected.
- Persisted card metadata keeps `summary_date` and event counts available for later digest and ops inspection.

## Digest Compatibility Notes
- Digest building now tolerates selected cards that are not tied to one paper.
- `PulseDigestItem.source_paper_id` may remain `null` for `yesterday_summary`.
- Compact digest and mini/desktop read payloads must not assume every card has a paper summary attached.
- Desktop Today compatibility in this phase is intentionally minimal:
  - accept `card_type = yesterday_summary`
  - allow highlight items with no linked paper summary

## Current Non-Goals
- no external paper retrieval
- no research-news retrieval
- no AI recap text
- no "today suggestion" card
- no new delivery channel
- no cloud sync of local file or note contents

## Future Work
- today-suggestion cards from internal state
- external academic retrieval driven by watch seeds
- related-paper and related-news cards
- richer multi-day activity summarization
- editorial controls for digest composition
