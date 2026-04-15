# External Retrieval Input Boundary v1

## Why Retrieval Planning Is Added Before Retrieval Execution
- The pulse system now has explicit internal inputs through:
  - `WorkActivityEvent`
  - `ResearchWatchProfile`
- The next stable step is to make external retrieval planning visible before any network execution happens.
- This keeps future academic retrieval explainable:
  - which watch seeds were used
  - which source-specific plans were produced
  - why each plan exists
- This phase is still planning-only:
  - no live network calls
  - no fetched documents
  - no related-paper or related-news pulse cards yet

## ExternalRetrievalPlan Model
- `ExternalRetrievalPlan` stores persisted planning records only.
- Stored fields:
  - `id`
  - `user_id`
  - `source_kind`
  - `retrieval_scope`
  - `watch_profile_id`
  - `paper_id`
  - `plan_label`
  - `query_text`
  - `query_payload`
  - `effective_inputs`
  - `reason_codes`
  - `plan_hash`
  - `status`
  - `created_at`
  - `updated_at`
- v1 `source_kind` values:
  - `openalex`
  - `crossref`
  - `arxiv`
- v1 `retrieval_scope` values:
  - `related_paper`
  - `venue_update`
  - `author_watch`
- v1 `status` values:
  - `planned`
  - `previewed`
  - `skipped`
- The table intentionally does not store:
  - fetched results
  - normalized external entities
  - raw article or paper content

## Effective Seed Building Logic
- Effective retrieval seeds are built deterministically from:
  - enabled `ResearchWatchProfile` rows
  - recent non-system `WorkActivityEvent` context
- The seed builder dedupes and sorts:
  - `topics`
  - `keywords`
  - `venues`
  - `authors_of_interest`
  - `touched_paper_titles`
- Recent activity context is bounded by `APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT`.
- `source=system` events are ignored for retrieval-input context.

## Source-Specific Plan Builders
- `ExternalRetrievalPlanner` is the planning boundary.
- v1 builders:
  - `OpenAlexPlanBuilder`
  - `CrossrefPlanBuilder`
  - `ArxivPlanBuilder`
- Builder intent stays conservative:
  - `OpenAlex` focuses on keyword/topic/author/venue planning
  - `Crossref` focuses on keyword/title/venue planning
  - `arXiv` focuses on keyword/topic planning
- Plans stay compact:
  - inspectable `plan_label`
  - deterministic `query_text`
  - structured `query_payload`
  - compact `reason_codes`

## Plan Hashing And Upsert Behavior
- Each plan is hashed deterministically from:
  - `user_id`
  - `source_kind`
  - `retrieval_scope`
  - optional `watch_profile_id`
  - optional `paper_id`
  - `query_text`
  - `query_payload`
  - `effective_inputs`
- `plan_hash` is unique.
- `POST /external-retrieval/plans/build/{user_id}` uses plan-hash upsert semantics:
  - identical plans are reused
  - repeated builds do not create duplicates
  - returned plans remain stable across repeated builds

## Preview And Build Endpoints
- `GET /external-retrieval/input-preview/{user_id}` returns:
  - enabled watch profiles
  - effective retrieval seeds
  - recent activity context summary
  - source plan previews
  - notes clarifying that no execution occurs
- `GET /external-retrieval/plans` lists persisted plans with optional filters:
  - `user_id`
  - `source_kind`
  - `retrieval_scope`
  - `status`
  - `paper_id`
- `POST /external-retrieval/plans/build/{user_id}`:
  - requires operator access
  - persists deterministic plans
  - never performs live retrieval in this phase
- `GET /pulse/input-preview/{user_id}` now includes a compact retrieval-planning section so pulse input review can inspect planning and recap inputs together.

## Current Non-Goals
- no real retrieval execution
- no live external credentials
- no LLM query rewriting
- no AI ranking or summarization
- no related-paper or related-news final pulse cards
- no desktop retrieval UI expansion

## Future Work
- real retrieval execution behind the same planner boundary
- normalized external result storage
- related-paper and related-news pulse candidates
- retrieval feedback and quality loops
- execution throttling, caching, and freshness controls
