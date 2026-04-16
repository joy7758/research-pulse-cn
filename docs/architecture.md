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
8. Official-account callback events, binding handshake reserve sessions, explicit admin claim flow, and real webpage OAuth completion now provide a future-safe bridge from provider callback evidence to `WeChatIdentityBinding` without turning OAuth into a generic app login system.
9. Mini read grants expose compact mobile-friendly read models for future mini-program landing without opening write access, now including structured Today digest rendering, a read-only subscription reserve summary, a read-only binding-handoff reserve summary, and a read-only editor-handoff reserve summary.
10. Subscription self-service grants expose a narrow user-side settings boundary for future official-account or mini entry without reusing admin or mini auth, and now also expose a separate handshake-reserve sub-boundary plus an explicit editor contract and preview-before-save surface.
11. `SubscriptionEditorHandoffGrant` derives a short-lived `/subscription-editor/*` token from mini reserve plus an existing self-service grant without turning mini auth into a write boundary, and a thin web shell under `apps/subscription-editor-web` consumes that token without creating a generic login surface.
12. Admin-managed `GroupWorkspace` containers now group selected users and papers into compact shared boards, while `ResultShareGrant` exposes opaque public read-only links for structured digest issues, paper snapshots, and workspace boards without turning sharing into file sync.
13. A thin public browser shell under `apps/result-share-web` now consumes those token-based share endpoints directly, optionally connects an in-memory self-service token, renders safe read-only structured outputs, exposes explicit collect-preview/collect actions for supported share kinds, and shows a manual invite/join handoff summary for `workspace_board` shares.
14. A thin public browser shell under `apps/group-workspace-invite-web` now consumes the public invite bootstrap plus self-service claim routes, keeps invite/self-service tokens in memory only, and does not introduce a generic login surface or source-file sharing.
15. A thin internal browser shell under `apps/group-workspace-admin-web` now consumes the admin-managed workspace and share-grant endpoints, reuses existing `GET /users` and `GET /papers` reads as lookup sources, and keeps admin bearer tokens in memory only.
16. Sync devices consume incremental `SyncEvent` feeds and push idempotent mutations back through the same service layer.
17. A Tauri desktop shell consumes the same sync feed, keeps a local SQLite outbox, performs limited writeback through `/sync/push`, manages a local-only paper workspace, stores local markdown notes/templates, keeps local review-matrix / response-letter workflows, exposes synced `SubscriptionPolicy` quiet-control fields in Settings with non-authoritative local hints, and renders sectioned daily digests on the Today page when the synced cache includes structured digest payloads.
18. A pulse input layer now records lightweight work activity and research watch profiles so future retrieval can start from explicit inputs instead of implicit guesses.
19. A thin internal browser shell under `apps/user-workbench-admin-web` now consumes read-only `/admin/user-workbench/*` aggregation routes so support workflows can traverse users, papers, and watch profiles without introducing writes or file sharing.
20. An external retrieval boundary now converts those inputs into persisted source-specific plans, executes official-source fetches behind provider adapters, stores normalized scholarly results, and lets the pulse pipeline consume those persisted records for deterministic `related_paper` cards without executing retrieval inline.

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
- A separate internal user workbench shell now consumes safe read-only summaries over those user/paper/watch-profile objects:
  - user -> papers
  - user -> watch profiles
  - paper -> watch profiles
  - no file-level data is exposed through this shell
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
- `WeChatIdentityBinding` stores official-account or mini-program identity bindings, now including explicit real official-account OAuth completion tied to handshake sessions.
- `DigestPublicationJob` is a provider-neutral preparation record.
- `DigestPublicationAttempt` records dispatch visibility for each provider-boundary invocation.
- `DigestDispatchRun` aggregates one issue-level official-account dispatch over multiple prepared jobs.
- `DigestDeliveryDecision` records user-side eligibility or skip decisions before official-account issue dispatch.
- `SubscriptionSelfServiceGrant` adds a separate self-service auth boundary for reading and patching safe official-account subscription controls without exposing admin/provider APIs.
- `OfficialAccountCallbackEvent` records inbound callback payloads and deduped handling state.
- `OfficialAccountBindingHandshakeSession` adds a reserve bridge from callback evidence to explicit binding claim and OAuth completion without creating login state.
- The publication layer now separates:
  - reserve objects and payload preparation
  - issue-level dispatch orchestration
  - user-side delivery control evaluation
  - provider status/readiness inspection
  - callback ingestion
  - callback-to-binding handshake reserve
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
  - subscription reserve summary
  - paper summaries
  - paper detail
- These views deliberately omit admin-only and provider-internal fields.
- Mini now prefers orchestrated digest structure when present:
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
- If structured fields are absent, mini falls back to a deterministic section mapping from legacy `highlights` / `items`.

## Subscription self-service reserve

### Grant boundary
- `SubscriptionSelfServiceGrant` is a dedicated bearer-token auth object for `/subscription-self-service/*`.
- It is separate from:
  - admin JWT auth
  - internal service auth
  - sync device-token auth
  - mini read auth
- Tokens are stored hashed at rest and returned in plaintext once at issuance time.

### Safe self-service surface
- Self-service endpoints only expose official-account subscription controls:
  - `GET /subscription-self-service/bootstrap`
  - `GET /subscription-self-service/settings`
  - `PATCH /subscription-self-service/settings`
  - `GET /subscription-self-service/delivery-control-preview`
  - `GET /subscription-self-service/editor-bootstrap`
  - `GET /subscription-self-service/editor-contract`
  - `POST /subscription-self-service/settings/preview`
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
- Supported editable fields are intentionally narrow:
  - `enabled`
  - `quiet_hours`
  - `policy.timezone`
  - `policy.allowed_weekdays`
  - `policy.muted_until`
  - `policy.minimum_selected_cards`
  - `policy.skip_if_no_today_focus`
- The authoritative delivery preview reuses the backend evaluator but does not persist `DigestDeliveryDecision` rows in this phase.
- The editor reserve adds a versioned machine-readable contract plus preview-before-save semantics without creating a second policy store.
- Mini read-only subscription reserve also reuses that evaluator for an authoritative preview, but mini grant auth remains read-only and separate from self-service edit auth.
- Mini read-only reserve also exposes a `self_service_entry` handoff summary so future UI clients know editor contract and preview endpoints exist without turning mini into a write surface yet.
- Mini read-only reserve now also exposes an `editor_handoff_reserve` summary so future mobile/WebView clients know a short-lived bridge to `/subscription-editor/*` exists without making mini grant auth directly writable.
- The current browser/webview-friendly editor shell consumes that bridge directly and stays thin:
  - in-memory handoff token only
  - contract/bootstrap/preview/save over existing `/subscription-editor/*`
  - no browser-side policy engine or new auth layer
- Self-service grant auth can also create/read/cancel a reserve handshake session, but admin auth remains the only claim path in this phase.
- Self-service grant auth can also issue an official-account OAuth authorize URL and inspect safe OAuth progress, while mini grant auth remains read-only.
- `SubscriptionEditorHandoffGrant` adds a separate short-lived auth boundary for `/subscription-editor/*`:
  - mini can mint the handoff token when reserve conditions are satisfied
  - the token can reuse existing editor bootstrap/contract/preview/save services
  - the token cannot call `/mini/*`, `/subscription-self-service/*`, or admin routes

## Group workspace and result sharing

### Workspace boundary
- `GroupWorkspace` is an admin-managed shared container for structured outcomes.
- `GroupWorkspaceMember` binds users into one workspace with explicit roles:
  - `owner`
  - `editor`
  - `viewer`
- `GroupWorkspacePaper` binds selected papers into one workspace board.
- The board model is read-only and deterministic:
  - workspace summary
  - member summaries
  - safe paper snapshots
  - compact quick stats
- `GroupWorkspaceInviteGrant` now adds an opaque invite-token boundary for workspace membership growth.
- `GroupWorkspaceInviteClaim` records deterministic claim outcomes for one user and one invite.
- Invite roles in v1 are intentionally restricted to:
  - `editor`
  - `viewer`
- `owner` remains admin-managed only.

### Result share boundary
- `ResultShareGrant` is a hashed opaque-token read-only grant for:
  - `digest_issue`
  - `paper_snapshot`
  - `workspace_board`
- `ResultShareAlias` is an additive opaque alias layer over `ResultShareGrant`:
  - alias resolution stays revocable and deterministic
  - raw share tokens remain the source of truth
  - aliases never expose the underlying raw share token
- Public share routes resolve:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`
  - `GET /result-shares/{share_token}/invite-handoff`
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - `GET /share-aliases/{alias}/invite-handoff`
  - optional `GET /s/{alias}` redirect
- Backend-only analytics reserve may observe those public routes and classify traffic by:
  - access mode: `share_token`, `alias`, `alias_redirect`
  - event type: `bootstrap_view`, `content_view`, `redirect`, `invite_handoff_redirect`
  - outcome: `resolved`, `rejected`
- Analytics capture stays privacy-aware:
  - no raw IP storage
  - no full referrer URL storage
  - no raw full user-agent storage
  - analytics write failures do not block share resolution
- Share content excludes:
  - source files
  - local attachment paths
  - local note contents
  - raw provider payloads
  - openid/unionid
- This keeps growth/share surfaces additive without weakening existing admin, mini, self-service, or provider auth boundaries.
- A thin browser shell under `apps/result-share-web` stays outside the backend auth system:
  - reads only `/result-shares/{share_token}/bootstrap`
  - reads only `/result-shares/{share_token}/content`
  - may read `/share-aliases/{alias}/bootstrap`
  - may read `/share-aliases/{alias}/content`
  - reads `/subscription-self-service/result-shares/{share_token}/collect-preview` only after a separate self-service token is connected
  - posts `/subscription-self-service/result-shares/{share_token}/collect` only after a separate self-service token is connected
  - may use `/subscription-self-service/share-aliases/{alias}/collect-preview` and `/subscription-self-service/share-aliases/{alias}/collect` when opened through alias mode
  - reads `/subscription-self-service/workspace-result-collections` only after a separate self-service token is connected
  - clears query or fragment share token, share alias, and self-service token hints from the visible URL after moving them into in-memory state
  - shows `workspace_invite_handoff_reserve` and `result_collect_handoff_reserve` for `workspace_board` shares as information only
- A separate internal admin shell under `apps/group-workspace-admin-web` stays inside the admin boundary:
  - accepts admin/operator bearer tokens from manual paste or query/fragment fallback
  - clears query or fragment bearer tokens from the visible URL after moving them into in-memory state
  - manages only workspace list/detail, member/paper add-remove, and `workspace_board` share-grant create/revoke flows
  - does not add source-file semantics or public editing
- Admin analytics reads stay inside the admin boundary:
  - `GET /admin/result-share-analytics/summary`
  - `GET /admin/result-share-analytics/events`

### Result collect reserve boundary
- `GroupWorkspaceResultCollectRecord` records one audit-friendly collect outcome per:
  - collecting user
  - target workspace
  - result share context
  - collected paper
- Result collect remains separate from result sharing:
  - public result-share routes stay read-only
  - collect stays behind `SubscriptionSelfServiceGrant`
  - collect adds structured `PaperProfile` objects to `GroupWorkspace`
  - collect does not expose or sync source files, local attachments, or local note contents
- Supported collectable share kinds in v1:
  - `digest_issue`
  - `paper_snapshot`
- `workspace_board` is intentionally not collectable in v1.
- Self-service collect routes:
  - `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - `POST /subscription-self-service/result-shares/{share_token}/collect`
  - `GET /subscription-self-service/workspace-result-collections`
- Public share bootstrap now also carries an informational `collection_reserve` block so future browser shells can discover the next-step collect boundary without turning share routes into write surfaces.
- The existing `apps/result-share-web` shell is now the minimal browser consumer of that reserve:
  - share bootstrap/content remain public and read-only
  - collect-preview/collect remain self-service-only
  - no source-file semantics are introduced
- Mini reserve may advertise the collect next step, but mini auth still cannot collect directly.

### Workspace-board invite handoff reserve
- `workspace_board` share pages remain read-only and still cannot claim membership directly.
- Public share bootstrap may now include an informational `workspace_invite_handoff_reserve` block:
  - separate invite token required
  - invite bootstrap available
  - self-service claim supported in a separate flow
  - direct claim via share page remains false
  - handoff redirect may be supported through a separate backend redirect boundary
  - source files remain excluded
- An optional invite shell entry URL hint may be configured, but it never carries a token.
- An optional `invite_handoff_url` may point to a backend redirect boundary and may carry only non-sensitive context flags.

### Workspace-board result collect handoff reserve
- `workspace_board` share pages remain read-only and still cannot collect papers directly.
- Public share bootstrap may now also include an informational `result_collect_handoff_reserve` block:
  - separate digest or paper share token required
  - result-share bootstrap available in a separate flow
  - collect supported via self-service in a separate flow
  - direct collect via current share remains false
  - source files remain excluded
- An optional result-share shell entry URL hint may be configured, but it never carries a token.

### Invite and join reserve boundary
- Workspace invites are distinct from result shares:
  - invite bootstrap is public and read-only
  - claim stays behind `SubscriptionSelfServiceGrant`
- Public bootstrap route:
  - `GET /workspace-invites/{invite_token}/bootstrap`
- Self-service invite routes:
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
- A thin public browser shell under `apps/group-workspace-invite-web` stays outside the backend auth system:
  - accepts invite tokens from `/invite/<token>`, query/fragment fallback, or manual paste
  - accepts an optional self-service token only for self-service routes
  - clears query or fragment invite/self-service tokens from the visible URL after moving them into in-memory state
  - remains read-only except for the explicit self-service claim action
  - may show a `result_collect_handoff_reserve` summary after membership-facing states, but that summary remains informational only
- Mini reserve may advertise the next step, but mini auth still cannot claim membership directly.
- Invite/join payloads exclude source files, local attachments, local notes, provider secrets, and WeChat identity secrets.
- Result collect remains a parallel self-service reserve:
  - it may use a public share as its read-only source
  - it still does not make result-share routes writable
  - it still does not introduce source-file semantics
- Invite bootstrap/preview/claim/membership payloads may also carry an informational `result_collect_handoff_reserve` block:
  - separate result-share token required
  - result-share bootstrap available
  - collect supported via self-service in a separate flow
  - direct collect via invite page remains false
  - source files remain excluded

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
- Unknown subscribe identities are now preserved as explicit reconciliation candidates for later admin claim.

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
