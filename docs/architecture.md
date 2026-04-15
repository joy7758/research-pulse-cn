# Architecture

## Overview
Research Pulse CN is implemented as a modular monolith that keeps domain decisions, persistence, adapters, and API transport separate while remaining easy to run in one process.

Core flow:
1. CRUD APIs manage user profiles, paper profiles, events, snapshots, and subscription policies.
2. Pulse preview and run requests build deterministic facts, candidates, scores, suppression reasons, and final selections.
3. A model-provider adapter produces card copy only for selected candidates.
4. Selected pulse cards enqueue outbox delivery jobs.
5. The worker dispatches delivery jobs through current supported channel adapters and manages retry and dead-letter transitions.
6. Digest issues are upserted from selected pulse cards, orchestrated into sectioned daily packets, and can be prepared for official-account publication.
7. Official-account publication jobs can be dispatched through the provider boundary either per job or through issue-level dispatch runs, while a separate delivery-control layer decides whether user policy allows sending now.
8. Mini read grants expose compact mobile-friendly read models for future mini-program landing without opening write access.
9. Sync devices consume incremental `SyncEvent` feeds and push idempotent mutations back through the same service layer.
10. A Tauri desktop shell consumes the same sync feed, keeps a local SQLite outbox, performs limited writeback through `/sync/push`, manages a local-only paper workspace, stores local markdown notes/templates, keeps local review-matrix / response-letter workflows, exposes synced `SubscriptionPolicy` quiet-control fields in Settings with non-authoritative local hints, and renders sectioned daily digests on the Today page when the synced cache includes structured digest payloads.
11. A pulse input layer now records lightweight work activity and research watch profiles so future retrieval can start from explicit inputs instead of implicit guesses.
12. An external retrieval boundary now converts those inputs into persisted source-specific plans, executes official-source fetches behind provider adapters, stores normalized scholarly results, and lets the pulse pipeline consume those persisted records for deterministic `related_paper` cards without executing retrieval inline.

## Module boundaries

### `domain`
- Holds enums and contracts.
- Defines stable interfaces for `FactCollector`, `RuleEngine`, `ModelProvider`, `CardValidator`, and `ChannelAdapter`.
- Keeps future provider swaps localized.

### `db`
- Owns SQLAlchemy metadata, ORM models, and engine/session wiring.
- Uses PostgreSQL-oriented JSON handling while staying SQLite-friendly for tests.

### `repositories`
- Encapsulates query and persistence access.
- Keeps services from spreading ad-hoc SQL across the codebase.

### `services`
- Implements business flows:
  - CRUD use cases
  - deterministic pulse generation
  - delivery orchestration
  - worker processing
  - device lifecycle and sync mutation handling

### `adapters`
- Contains outbound channel integrations and model-provider implementations.
- Current adapters:
  - `ConsoleChannelAdapter`
  - `WebhookChannelAdapter`
  - `DummyModelProvider`

Future communication surfaces are intentionally outside the active delivery layer:
- official-account digest publishing
- mini-program lightweight client access through sync

### `api`
- FastAPI transport layer.
- Routes, dependency wiring, and exception translation only.

## Pulse chain

### Input layer
- `WorkActivityEvent` captures lightweight structured activity for recap-style inputs such as:
  - paper updates
  - progress events
  - subscription-policy changes
  - desktop attachment/note/review actions emitted through sync
- `ResearchWatchProfile` stores compact user watch interests that can later drive retrieval.
- `ExternalRetrievalPlan` stores deterministic source-specific planning records for later retrieval execution.
- `ExternalRetrievalRun` stores one execution attempt per persisted plan.
- `ExternalRetrievedRecord` stores normalized scholarly records fetched from official source APIs.
- `GET /pulse/input-preview/{user_id}` exposes:
  - previous-day work activity summary
  - raw ordered activity events
  - enabled watch profiles
  - effective deduped watch seeds
  - compact retrieval-planning preview
- `GET /external-retrieval/input-preview/{user_id}` exposes:
  - effective retrieval seeds
  - recent activity context summary
  - source-specific plan previews
- `POST /external-retrieval/plans/build/{user_id}` persists deterministic plans using plan-hash upsert semantics.
- `GET /external-retrieval/provider-status` exposes safe execution readiness and source status.
- `POST /external-retrieval/plans/execute/{plan_id}` executes one persisted plan through an official-source adapter.
- `GET /external-retrieval/runs` and `GET /external-retrieval/results` expose run history and normalized records.
- This layer stays intentionally upstream of pulse generation even after `related_paper` support:
  - no AI expansion
  - no related-news cards yet
  - no inline retrieval during pulse preview/run

### Fact collection
- `DeterministicFactCollector` inspects current paper state.
- It currently emits:
  - next action facts
  - stalled progress facts
  - signal change facts
  - deadline risk facts
- `RelatedPaperCandidateBuilder` separately turns persisted normalized scholarly records into related-paper facts.

### Rule selection
- `DeterministicRuleEngine` converts facts into stable candidates.
- Candidate ranking now happens in a dedicated scoring and suppression pipeline.

### Scoring and suppression
- `PulseService` resolves user-specific scoring knobs from defaults plus `SubscriptionPolicy.policy` overrides.
- Candidates are scored with explainable weighted breakdowns.
- Suppression is applied before selection for:
  - quiet hours
  - dedupe window
  - low score
  - paused paper guard
  - frequency cap overflow after ordering

Tie-break order is deterministic:
1. score total descending
2. explicit card type order
3. source timestamp descending
4. paper title ascending
5. candidate id ascending

### Card generation
- `DummyModelProvider` turns selected candidates into stable card payloads.
- `SimpleCardValidator` blocks incomplete outputs before persistence.

### Delivery
- Each enabled subscription policy creates a delivery job per selected card.
- `DeliveryService` moves jobs through:
  - `pending`
  - `sending`
  - `sent`
  - `failed`
  - `dead_letter`

## Digest reserve

### Why digest is separate from pulse cards
- `PulseCard` remains the ranked atomic unit for delivery and sync.
- `PulseDigestIssue` becomes the daily user-facing digest artifact for future official-account and mini-program surfaces.
- `PulseDigestItem` snapshots ordered card content into a digest-specific shape without re-running ranking.
- `PulseDigestIssue.content_payload` now also stores a deterministic sectioned daily-digest structure for publication preparation:
  - `today_focus`
  - `yesterday_recap`
  - `signal_updates`
  - `related_papers`
  - `other_updates`
- This keeps digest orchestration separate from both pulse ranking and official-account dispatch.

### Publication reserve boundary
- `WeChatIdentityBinding` stores admin-managed official-account or mini-program identity bindings without real OAuth flows.
- `DigestPublicationJob` is a provider-neutral preparation record.
- `DigestPublicationAttempt` records dispatch visibility for each provider-boundary invocation.
- `DigestDispatchRun` aggregates one issue-level official-account dispatch over multiple prepared jobs.
- `DigestDeliveryDecision` records user-side eligibility or skip decisions before official-account issue dispatch.
- `OfficialAccountCallbackEvent` records inbound callback payloads and deduped handling state.
- The publication layer now separates:
  - reserve objects and payload preparation
  - issue-level dispatch orchestration
  - user-side delivery control evaluation
  - provider status/readiness inspection
  - callback ingestion
  - dry-run preview dispatch
  - explicit per-binding real sends through `template_notice`
- Real sends remain opt-in:
  - `provider_mode=real`
  - `real_send_enabled=true`
  - configured credentials and template id
- Access tokens are cached outside the database and never written to publication-attempt rows.
- Provider readiness remains distinct from policy eligibility:
  - provider can be ready while delivery policy still blocks sends because of quiet hours, mute windows, weekday limits, or digest-content thresholds.

## Mini read-only reserve

### Mini auth boundary
- `MiniReadGrant` is a dedicated read-only token model for `/mini/*`.
- Mini grants are distinct from:
  - admin authentication
  - internal service authentication
  - sync device authentication
- Tokens are stored hashed at rest and returned in plaintext once at issuance time.

### Compact mobile read models
- The mini layer reshapes existing domain state into compact read payloads for:
  - bootstrap context
  - today overview
  - digest detail
  - paper summaries
  - paper detail
- These views deliberately omit admin-only and provider-internal fields.

### Derived progress percentage
- Mini paper views expose a deterministic `progress_percentage` derived from `PaperProfile.type`.
- This is a presentation heuristic only:
  - `published -> 100`
  - `revision -> 80`
  - `under_review -> 65`
  - `in_prep -> 35`
  - `paused -> 0`
- The workflow truth remains the underlying paper type, stage, and event history.

## Official-account callback ingress
- Callback endpoints are separate from admin auth because they are provider-ingress surfaces.
- Signature verification is token-based in v1.
- Supported callback events are intentionally narrow:
  - `subscribe`
  - `unsubscribe`
- Unknown identities are archived but do not create new user bindings automatically.

## Sync backbone

### Device identity
- `ClientDevice` represents a desktop or mobile sync client tied to one `UserProfile`.
- `ClientAccessToken` stores only hashed device credentials.
- Device tokens are valid only for `/sync/*`.

### Event feed
- `SyncEvent` stores user-scoped, monotonic events for paper, progress, signal, subscription, and pulse-card changes.
- `PulseDigestIssue` create/update now also emits compact sync events so future read-only clients can consume digest state.
- `SyncCursor` tracks the latest acknowledged sequence per device.
- `SyncMutation` records idempotent client-originated writes keyed by `(client_device_id, client_mutation_id)`.
- `work_activity.record` is now also accepted as a sync mutation type for lightweight desktop-local activity metadata, but it intentionally does not sync local file or note contents.

## Pulse yesterday-summary card
- The pulse pipeline now supports a global `yesterday_summary` card type in addition to paper-centric cards.
- It is generated from `WorkActivityEvent` only:
  - no external retrieval
  - no AI summarization
  - no source-paper requirement
- The summary uses the effective pulse timezone in this order:
  - explicit request parameter
  - first enabled daily subscription-policy timezone
  - app default timezone
- Selected cards persist as normal `PulseCard` rows and may flow into digest items with `source_paper_id = null`.

## Pulse today-suggestion card
- The pulse pipeline now also supports a deterministic `today_suggestion` card type.
- It is built only from internal structured state:
  - `PaperProfile`
  - `ProgressEvent`
  - `SignalSnapshot`
  - effective pulse timezone context from subscription policy or app default
- It remains retrieval-free and model-free in this phase.
- The builder selects at most one actionable paper per run and chooses one suggestion kind:
  - `execute_next_action`
  - `resolve_blocker`
  - `define_next_action`
- Selected cards persist as normal `PulseCard` rows and usually keep a non-null `source_paper_id`.

## Pulse related-paper card
- The pulse pipeline now supports deterministic `related_paper` cards sourced only from persisted normalized scholarly results.
- Candidate sourcing requires:
  - `ExternalRetrievedRecord`
  - parent `ExternalRetrievalRun.status = completed`
  - `retrieval_scope = related_paper`
- The pipeline derives a canonical external reference key in this order:
  - `doi`
  - `source_kind + external_id`
  - normalized title fallback
- That key is used for:
  - collapsing duplicate scholarly results across runs/sources
  - suppressing resurfacing of the same scholarly result within the related-paper dedupe window
- Selected cards persist as normal `PulseCard` rows and now also store `external_reference_key`.

## External retrieval planning and execution boundary
- The external retrieval layer now covers deterministic planning plus official-source execution.
- It is driven by:
  - enabled `ResearchWatchProfile` rows
  - recent non-system `WorkActivityEvent` context
- Builders currently exist for:
  - `openalex`
  - `crossref`
  - `arxiv`
- Matching executors now exist for:
  - `OpenAlexExecutor`
  - `CrossrefExecutor`
  - `ArxivExecutor`
- Supported retrieval scopes are:
  - `related_paper`
  - `venue_update`
  - `author_watch`
- Each plan persists:
  - source kind
  - retrieval scope
  - query text
  - structured query payload
  - effective inputs
  - reason codes
  - deterministic `plan_hash`
- Execution persists:
  - `ExternalRetrievalRun`
  - `ExternalRetrievedRecord`
- The boundary still stops before:
  - related-news pulse cards
  - AI rewriting, ranking, or summarization
  - generic web/news crawling

### Desktop shell
- `apps/desktop` is isolated from the Python backend.
- Rust owns:
  - secret storage
  - local SQLite cache
  - local mutation outbox
  - local workspace root validation
  - managed-copy attachment import
  - attachment metadata indexing
  - local note template rendering
  - local note file IO and metadata indexing
  - sync HTTP client
  - typed Tauri command boundary
- React owns:
  - connection/onboarding view
  - Today view
  - Papers view
  - Paper Detail view
  - Settings / Sync Status view
- Desktop writeback is intentionally narrow in v1:
  - `paper.patch`
  - `progress_event.create`
  - `subscription_policy.patch`
  - `work_activity.record`
- Desktop local workspace is intentionally local-only in v1:
  - workspace root selection
  - deterministic `papers/<paper_id>/...` folders
  - managed-copy attachments
  - markdown notes under `papers/<paper_id>/notes/`
  - built-in note templates rendered on the Rust side
  - no backend attachment sync
  - no backend note sync
  - no OCR or AI file understanding
- Desktop local actions can still contribute to the cloud-side pulse input layer through concise `work_activity.record` mutations that carry summary metadata only.
- The desktop shell applies a push-before-pull cycle, but local paper and policy caches remain authoritative only after server `SyncEvent` replay.

### Consistency model
- Supported sync patches are last-write-wins in v1.
- Client mutations flow through the same service layer as admin/API writes.
- This keeps the desktop client, future lightweight clients, and future digest publishing surfaces aligned on one canonical backend state model.

## Why this shape
- It is production-friendly without over-fragmenting into microservices.
- It is simple to evolve toward stronger AI-agent autonomy because the decision interfaces are explicit and swappable.
- It preserves private commercial flexibility: providers, rules, and channels can change without forcing a schema rewrite.
