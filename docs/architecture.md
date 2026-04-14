# Architecture

## Overview
Research Pulse CN is implemented as a modular monolith that keeps domain decisions, persistence, adapters, and API transport separate while remaining easy to run in one process.

Core flow:
1. CRUD APIs manage user profiles, paper profiles, events, snapshots, and subscription policies.
2. Pulse preview and run requests feed deterministic facts into a rule engine.
3. A model-provider adapter produces pulse card content.
4. Pulse cards enqueue outbox delivery jobs.
5. The worker dispatches delivery jobs through channel adapters and manages retry and dead-letter transitions.

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

### `adapters`
- Contains outbound channel integrations and model-provider implementations.
- Current adapters:
  - `ConsoleChannelAdapter`
  - `DingTalkWebhookAdapter`
  - `WeChatTemplateAdapter` stub
  - `DummyModelProvider`

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

### Rule selection
- `DeterministicRuleEngine` deduplicates facts by paper and card type.
- It ranks by priority and yields a bounded ordered set.

### Card generation
- `DummyModelProvider` turns structured facts into stable card payloads.
- `SimpleCardValidator` blocks incomplete outputs before persistence.

### Delivery
- Each enabled subscription policy creates a delivery job per card.
- `DeliveryService` moves jobs through:
  - `pending`
  - `sending`
  - `sent`
  - `failed`
  - `dead_letter`

## Why this shape
- It is production-friendly without over-fragmenting into microservices.
- It is simple to evolve toward stronger AI-agent autonomy because the decision interfaces are explicit and swappable.
- It preserves private commercial flexibility: providers, rules, and channels can change without forcing a schema rewrite.
