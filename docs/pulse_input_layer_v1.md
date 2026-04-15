# Pulse Input Layer v1

## Why Pulse Input Layer Comes Before External Retrieval
- The pulse system needs explicit inputs for "what the user did yesterday" and "what the user should watch next" before external retrieval is added.
- Locking these two inputs down first keeps future retrieval, ranking, and summarization explainable instead of hiding basic relevance inside a crawler.
- This phase is intentionally input-only:
  - no external paper/news retrieval
  - no AI query generation
  - no final pulse-card generation from external sources yet

## WorkActivityEvent Model
- `WorkActivityEvent` stores lightweight user-work metadata only.
- Stored fields:
  - `id`
  - `user_id`
  - `paper_id`
  - `activity_type`
  - `summary`
  - `metadata`
  - `happened_at`
  - `source`
  - `created_at`
- Supported v1 activity types:
  - `paper_updated`
  - `progress_event_created`
  - `subscription_policy_updated`
  - `attachment_imported`
  - `note_created`
  - `note_saved`
  - `review_round_created`
  - `reviewer_matrix_generated`
  - `response_letter_generated`
- Important boundary:
  - no local file content
  - no note markdown content
  - no generated review-note content

## ResearchWatchProfile Model
- `ResearchWatchProfile` stores compact user watch interests for future retrieval.
- Stored fields:
  - `id`
  - `user_id`
  - `paper_id`
  - `label`
  - `enabled`
  - `source_mode`
  - `topics`
  - `keywords`
  - `venues`
  - `authors_of_interest`
  - `created_at`
  - `updated_at`
- `source_mode` in v1:
  - `manual`
  - `paper_bootstrap`
- Profiles are intentionally sparse and deterministic in this phase.

## Cloud Auto-Capture Vs Desktop-Emitted Activity
- Cloud-side service actions now auto-record work activity for:
  - `paper.patch` -> `paper_updated`
  - `progress_event.create` -> `progress_event_created`
  - `subscription_policy.patch` -> `subscription_policy_updated`
- Desktop local-only actions emit `work_activity.record` through the existing sync outbox for:
  - attachment import
  - note create
  - note save
  - review round create
  - reviewer-matrix note generation
  - response-letter note generation
- Desktop still sends only concise summary plus metadata. Local file contents and note contents stay local.

## Watch-Profile Bootstrap Logic
- `POST /research-watch-profiles/bootstrap/{paper_id}` creates a conservative profile from one paper.
- v1 bootstrap rules:
  - `label` comes from the paper title
  - `keywords` includes at least the full paper title
  - `venue` is included when present
  - `paper_id` is linked when the profile came from a paper
- No NLP, AI expansion, or semantic enrichment is used in this phase.

## Pulse Input Preview Endpoint
- `GET /pulse/input-preview/{user_id}` exposes the current pulse input layer without doing retrieval.
- The response includes:
  - previous-day preview window
  - machine-readable work activity summary
  - ordered work activity events
  - enabled watch profiles
  - effective deduped watch seeds
  - notes describing what later external retrieval would use
- Effective watch seeds are currently deduped by category:
  - `topics`
  - `keywords`
  - `venues`
  - `authors_of_interest`

## Current Non-Goals
- no external academic retrieval
- no news retrieval
- no AI summarization
- no AI keyword expansion
- no syncing local file or note contents to the backend
- no new delivery channel behavior

## Future Work
- external academic retrieval driven by watch seeds
- richer multi-day activity cards built from `WorkActivityEvent`
- related paper and research-news retrieval
- richer watch-profile derivation from user portfolios
- stronger input weighting from operational feedback

## Relationship To Yesterday Summary
- The pulse pipeline now consumes this input layer to build one deterministic `yesterday_summary` pulse candidate per user when the previous local day has qualifying work activity.
- The builder still uses only local backend state:
  - `WorkActivityEvent`
  - subscription-policy timezone hints
  - application default timezone fallback
- No external retrieval or AI recap text is involved.
