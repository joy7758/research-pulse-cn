# Architecture

## Overview
Research Pulse CN is implemented as a modular monolith that keeps domain decisions, persistence, adapters, and API transport separate while remaining easy to run in one process.

Core flow:
1. CRUD APIs manage user profiles, paper profiles, events, snapshots, and subscription policies.
2. Pulse preview and run requests build deterministic facts, candidates, scores, suppression reasons, and final selections.
3. A model-provider adapter produces card copy only for selected candidates.
4. Selected pulse cards enqueue outbox delivery jobs.
5. The worker dispatches delivery jobs through current supported channel adapters and manages retry and dead-letter transitions.
6. Digest issues are upserted from selected pulse cards and can be prepared for future official-account publication.
7. Official-account publication jobs can be dispatched through a provider boundary in `disabled`, `dry_run`, or explicit `real` mode while callback events update existing bindings.
8. Mini read grants expose compact mobile-friendly read models for future mini-program landing without opening write access.
9. Sync devices consume incremental `SyncEvent` feeds and push idempotent mutations back through the same service layer.

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

### Fact collection
- `DeterministicFactCollector` inspects current paper state.
- It currently emits:
  - next action facts
  - stalled progress facts
  - signal change facts
  - deadline risk facts
  - related paper placeholder facts

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

### Publication reserve boundary
- `WeChatIdentityBinding` stores admin-managed official-account or mini-program identity bindings without real OAuth flows.
- `DigestPublicationJob` is a provider-neutral preparation record.
- `DigestPublicationAttempt` records dispatch visibility for each provider-boundary invocation.
- `OfficialAccountCallbackEvent` records inbound callback payloads and deduped handling state.
- The publication layer now separates:
  - reserve objects and payload preparation
  - provider status/readiness inspection
  - callback ingestion
  - dry-run preview dispatch
  - explicit per-binding real sends through `template_notice`
- Real sends remain opt-in:
  - `provider_mode=real`
  - `real_send_enabled=true`
  - configured credentials and template id
- Access tokens are cached outside the database and never written to publication-attempt rows.

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

### Consistency model
- Supported sync patches are last-write-wins in v1.
- Client mutations flow through the same service layer as admin/API writes.
- This keeps the desktop client, future lightweight clients, and future digest publishing surfaces aligned on one canonical backend state model.

## Why this shape
- It is production-friendly without over-fragmenting into microservices.
- It is simple to evolve toward stronger AI-agent autonomy because the decision interfaces are explicit and swappable.
- It preserves private commercial flexibility: providers, rules, and channels can change without forcing a schema rewrite.
