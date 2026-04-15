# Pulse Related Paper Candidate v1

## Why Related Paper Cards Consume Normalized External Records Instead Of Calling Retrieval Directly
- `related_paper` now sits downstream of retrieval planning and retrieval execution.
- Pulse preview/run only reads persisted `ExternalRetrievedRecord` rows.
- This keeps the boundary hard:
  - retrieval planning decides what to query
  - retrieval execution fetches and normalizes official-source results
  - pulse candidate generation only scores already-persisted normalized records
- No network calls happen during `POST /pulse/preview/{user_id}` or `POST /pulse/run/{user_id}` in this phase.

## Candidate Source Rules
- Eligible source rows must come from:
  - `ExternalRetrievedRecord`
  - parent `ExternalRetrievalRun.status = completed`
  - `retrieval_scope = related_paper`
- Candidate sourcing is further bounded by:
  - `APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS`
  - `APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN`
- If no eligible normalized results exist, no `related_paper` candidate is generated.

## Canonical External Reference Key Logic
- Each normalized scholarly result now derives a deterministic canonical key in this order:
  1. `doi`
  2. `source_kind + external_id`
  3. normalized title fallback
- The key is used for two separate jobs:
  - collapse duplicate normalized results across repeated runs or sources
  - suppress resurfacing the same scholarly result again inside the related-paper dedupe window
- When duplicates exist, the pulse pipeline prefers the most recent completed run/result for that canonical key.
- Selected `PulseCard` rows now persist:
  - `external_reference_key`

## Scoring, Suppression, And Dedupe Behavior
- Stable card-type order remains:
  - `signal_change`
  - `deadline_risk`
  - `stalled_progress`
  - `today_suggestion`
  - `next_action`
  - `yesterday_summary`
  - `related_paper`
- Related-paper scoring knobs:
  - `APP_PULSE_WEIGHT_RELATED_PAPER`
  - `APP_PULSE_MODIFIER_RELATED_PAPER_HAS_DOI`
  - `APP_PULSE_MODIFIER_RELATED_PAPER_MATCH_REASON_COUNT`
  - `APP_PULSE_MODIFIER_RELATED_PAPER_LINKED_PAPER`
  - `APP_PULSE_MODIFIER_RELATED_PAPER_RECENT_RETRIEVAL`
  - `APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS`
  - `APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN`
  - `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`
- Required score-breakdown modifier keys:
  - `related_paper_has_doi`
  - `related_paper_match_reason_count`
  - `related_paper_linked_paper`
  - `related_paper_recent_retrieval`
- Suppression still respects:
  - quiet hours
  - low score
  - frequency cap
  - dedupe window
- Historical dedupe now suppresses the same `external_reference_key` for the same user inside `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`.

## Pulse Preview And Run Implications
- `POST /pulse/preview/{user_id}` now exposes `related_paper` candidates with:
  - canonical external identity
  - linked internal paper context when available
  - source kind and retrieval scope
  - score breakdown and suppression reasons
- `POST /pulse/run/{user_id}` persists selected `related_paper` candidates as normal `PulseCard` rows.
- Persisted metadata keeps enough context for ops/debugging:
  - external record id
  - external run id
  - external plan id
  - source kind
  - canonical key
  - linked paper context

## Digest And Desktop Compatibility Notes
- Digest building now tolerates real `related_paper` cards backed by normalized external results.
- Official-account daily digest orchestration now places capped `related_paper` cards into the `related_papers` section without triggering retrieval at digest-build time.
- `source_paper_id` may be present when the originating retrieval plan was linked to a paper.
- Desktop Today and digest-highlight read models already accept `related_paper`, so this phase only tightens type compatibility rather than adding new retrieval UI.

## Current Non-Goals
- no `related_news` cards
- no AI ranking
- no AI summarization
- no retrieval execution during pulse preview/run
- no desktop retrieval browsing UI
- no new delivery channels

## Future Work
- `related_news` candidate generation
- richer ranking over normalized scholarly results
- user feedback loops for related-paper relevance
- broader consumption of normalized external records beyond pulse cards
