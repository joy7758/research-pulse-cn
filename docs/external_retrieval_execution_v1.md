# External Retrieval Execution v1

## Why Execution Is Added Before Final Pulse Cards
- The system now has deterministic retrieval plans through `ExternalRetrievalPlan`.
- The next stable step is to execute those plans against official scholarly APIs before any pulse-card consumption is added.
- This keeps the boundary explicit:
  - planning decides what to query
  - execution fetches and normalizes results
  - later pulse phases decide whether any result should become a card
- This phase still stops short of `related_paper` or `related_news` pulse-card generation.

## ExternalRetrievalRun Model
- `ExternalRetrievalRun` stores one execution attempt for one persisted plan.
- Stored fields:
  - `id`
  - `plan_id`
  - `user_id`
  - `source_kind`
  - `retrieval_scope`
  - `status`
  - `request_url`
  - `request_payload`
  - `response_summary`
  - `raw_result_count`
  - `normalized_result_count`
  - `started_at`
  - `finished_at`
  - `last_error`
  - `created_at`
  - `updated_at`
- v1 `status` values:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `skipped`

## ExternalRetrievedRecord Model
- `ExternalRetrievedRecord` stores one normalized scholarly result row produced by one run.
- Stored fields:
  - `id`
  - `run_id`
  - `plan_id`
  - `user_id`
  - `source_kind`
  - `retrieval_scope`
  - `external_id`
  - `external_url`
  - `doi`
  - `title`
  - `abstract_snippet`
  - `publication_year`
  - `publication_date`
  - `source_title`
  - `authors`
  - `matched_reason_codes`
  - `raw_payload`
  - `sort_order`
  - `created_at`
  - `updated_at`
- `unique(run_id, external_id)` prevents duplicate normalized rows inside one run.

## Provider Boundaries
- Execution stays behind explicit source adapters:
  - `OpenAlexExecutor`
  - `CrossrefExecutor`
  - `ArxivExecutor`
- These executors:
  - consume persisted `ExternalRetrievalPlan`
  - build official-API requests only
  - parse source-native response shapes
  - emit normalized records
- No generic web search or HTML scraping layer is introduced.

## OpenAlex, Crossref, And arXiv Execution Notes
- OpenAlex:
  - uses the official `api.openalex.org` works endpoint
  - `api_key` is optional and attached only when configured
  - JSON results are normalized directly
- Crossref:
  - uses the official `api.crossref.org/works` endpoint
  - polite identification is attached when configured through `mailto` and/or `User-Agent`
  - JSON results are normalized directly
- arXiv:
  - uses the official `export.arxiv.org/api/query` endpoint
  - sends `search_query`, `start`, and `max_results`
  - parses Atom XML deterministically
  - does not attempt bulk OAI-PMH harvesting

## Normalization Model
- Each executor maps provider-native records into the shared `ExternalRetrievedRecord` shape.
- Top-level normalized fields stay intentionally small:
  - stable external identifier
  - canonical title and URL
  - compact abstract snippet when available
  - publication date/year
  - source title
  - compact author list
  - inherited match reason codes from the originating plan
- Provider-specific details stay inside `raw_payload` for debugging and later richer normalization.

## Execute Endpoint And Dedupe Behavior
- `POST /external-retrieval/plans/execute/{plan_id}`:
  - is operator-protected
  - validates mode and source readiness
  - creates an `ExternalRetrievalRun`
  - fetches from the official source API
  - normalizes and persists `ExternalRetrievedRecord` rows
  - never creates `PulseCard` rows in this phase
- Dedupe behavior:
  - bounded by `APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES`
  - if a recent successful run exists for the same plan and `force=false`, the service returns that existing run
  - `force=true` bypasses dedupe and creates a fresh run

## Provider Status And Readiness
- `GET /external-retrieval/provider-status` exposes safe execution readiness:
  - current mode
  - enabled sources
  - readiness checks
  - safe config presence booleans
  - timeout settings
  - execution caps
  - dedupe window
- The response never returns:
  - API keys
  - raw contact strings
  - fetched content payloads

## Current Non-Goals
- no final `related_paper` or `related_news` pulse cards
- no AI query rewriting
- no AI ranking or summarization
- no scraping or generic crawler layer
- no scheduled execution
- no desktop retrieval UI work

## Future Work
- consume normalized retrieval results in `related_paper` pulse candidates
- add result-level dedupe across runs
- add richer source-specific normalization and provenance
- add scheduled execution and freshness policies
- add feedback loops for ranking quality
