# MVP China-First Research Pulse Roadmap v1

## MVP Goal
- Build the shortest useful loop for China-first research users:
  - import papers
  - organize paper state
  - track research progress
  - generate daily Research Pulse
  - deliver through desktop, official account, and mini-program surfaces

## Phase Pivot-2: Import Formats Foundation
- Scope:
  - CSL JSON
  - BibTeX
  - RIS
  - Excel
  - PDF folder metadata placeholder
- Implementation note:
  - backend-only parser and normalizer foundation lives under `src/research_pulse_cn/*` with no UI or import commit in this phase
- Non-goals:
  - CNKI
  - Wanfang
  - VIP
  - Zotero plugin
  - OAuth

## Phase Pivot-3: Import Preview And Import Commit
- Scope:
  - parse file
  - preview normalized paper rows
  - validate required fields
  - commit imported papers into repository-owned models
- Implementation note:
  - reuse existing `PaperProfile` persistence with a minimal preview-and-selected-commit backend flow, without adding a new UI in this phase
- Non-goals:
  - dedupe perfection
  - external source sync
  - attachment ingestion pipeline

## Phase Pivot-4: Paper Progress Workbench
- Scope:
  - show imported papers
  - edit progress state
  - update next action
  - update blockers
  - update priority and last-touch signals
- Implementation note:
  - reuse existing `PaperProfile` persistence and extend paper progress state through backend-only workbench APIs, summary views, and pulse-context read models without adding a new UI
- Non-goals:
  - advanced collaboration
  - admin preset expansion
  - large workflow automation

## Phase Pivot-5: Pulse Over Imported Papers
- Scope:
  - run pulse over imported paper state
  - reuse existing deterministic pulse engine
  - produce daily Research Pulse content grounded in imported papers and progress state
- Non-goals:
  - AI-heavy rewriting
  - broad news aggregation
  - plugin ecosystems

## Phase Pivot-6: Official-Account Daily Summary MVP
- Scope:
  - connect pulse output to the existing official-account delivery path
  - keep daily summary focused and minimal
- Implementation note:
  - reuse paper-based `ResearchPulseResult` to generate official-account daily summary draft, `publication_preview`, and template payload preview without creating real send jobs in this phase
- Non-goals:
  - full social growth tooling
  - referral or broadcast logic
  - new auth systems

## Phase Pivot-7: Desktop Notification MVP
- Scope:
  - deliver pulse reminder and pulse detail entry through the existing desktop foundation
  - keep desktop as the fastest operator and researcher surface
- Implementation note:
  - reuse paper-based `ResearchPulseResult` to generate local desktop notification draft, actions, deep-link placeholders, and payload preview without building a real desktop client in this phase
- Non-goals:
  - full desktop-local workspace reinvention
  - broad plugin support
  - file-sync feature expansion

## Phase Pivot-8: Mini-Program Detail MVP
- Scope:
  - reuse the existing mini read path for pulse detail viewing
  - keep mini focused on lightweight reading and follow-up context
- Implementation note:
  - reuse paper-based `ResearchPulseResult` and paper progress read models to generate share-safe mini-program detail preview payloads, cards, and path placeholders without building a real mini frontend in this phase
- Non-goals:
  - full mini editing
  - OAuth expansion
  - broad workflow authoring

## Roadmap Guardrails
- No new admin preset/report/print phases
- No new frontend app for this pivot phase
- No backend migration in Pivot-1
- No connector or plugin ecosystem work before the import-progress-pulse loop is stable
