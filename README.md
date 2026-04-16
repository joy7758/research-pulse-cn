# Research Pulse CN

Commercial closed-source backend for a China-focused research paper lifecycle and pulse subscription system.

## Repository status
Private repository. Proprietary and confidential.

## What is included
- FastAPI backend with OpenAPI docs
- SQLAlchemy 2 models and Alembic migration
- CRUD APIs for users, papers, progress events, signal snapshots, and subscription policies
- Deterministic pulse preview and run flow
- Daily scheduler foundation with per-policy local-time scheduling
- Outbox-style delivery jobs with retry and dead-letter transitions
- Worker heartbeats, delivery-attempt tracking, readiness checks, and Prometheus-style metrics
- Current delivery paths for `in_app`, `email`, and `webhook`, with console/webhook adapters for local development
- Device-token sync backbone for desktop and future lightweight clients
- WeChat identity bindings plus digest issue/publication reserve objects for future official-account and mini-program flows, including deterministic daily-digest orchestration and issue-level official-account dispatch orchestration
- Official-account provider boundary with `disabled` / `dry_run` / explicit `real` mode, callback ingress, and token-backed real-send activation
- Deterministic user-side delivery control on top of official-account digest dispatch, including quiet hours, mute-until, weekday allow-lists, minimum digest thresholds, and persisted delivery decisions
- Admin-issued subscription self-service reserve grants that expose safe official-account settings reads, safe settings patching, and authoritative delivery-control preview without real WeChat OAuth
- Self-service editor reserve endpoints that add machine-readable field/section contracts, preview-before-save semantics, and future mobile/web handoff metadata on top of the same self-service grant boundary
- Mini editor handoff reserve that adds a short-lived `SubscriptionEditorHandoffGrant` bridge from mini read-only reserve to `/subscription-editor/*` without making mini grants directly writable
- A thin React/Vite subscription editor web shell under `apps/subscription-editor-web` for manually exercising handoff-grant-protected `/subscription-editor/*` flows in a browser or future WebView shell
- Admin-managed group workspaces with structured workspace boards plus opaque read-only result share grants for `digest_issue`, `paper_snapshot`, and `workspace_board` without exposing source files, local attachment paths, or local note contents
- A thin public React/Vite result-share shell under `apps/result-share-web` for opening `ResultShareGrant` links in a browser, optionally connecting an in-memory self-service token for collect-preview/collect flows, and surfacing manual invite/join plus result-collect handoff summaries on `workspace_board` shares without introducing source-file sharing, browser token persistence, or a generic login system
- The same result-sharing boundary now also supports admin-issued opaque `ResultShareAlias` links so public browser entry can use aliases without exposing the underlying raw share token
- A thin internal React/Vite admin shell under `apps/group-workspace-admin-web` for operator-managed workspace list/detail, member/paper add-remove flows, and `workspace_board` share-grant issuance without introducing end-user login or source-file sharing
- A thin internal React/Vite admin shell under `apps/user-workbench-admin-web` for read-only search and drilldown across users, papers, and research watch profiles without introducing end-user login, file sharing, or business write flows
- A backend-only workspace invite/join reserve that adds opaque invite grants, public invite bootstrap, self-service claim-preview/claim routes, and safe membership summaries without introducing source-file sharing or a generic login system
- A thin public React/Vite invite shell under `apps/group-workspace-invite-web` for safe workspace-invite bootstrap, self-service claim preview/claim, and membership confirmation without introducing end-user login, browser token persistence, or source-file sharing
- The same invite shell can now also surface a manual handoff summary toward the separate result-share collect flow after membership is claimed or confirmed, without mixing invite tokens and share tokens or introducing source-file sharing
- A backend-only result collect reserve that lets self-service users collect structured `digest_issue` and `paper_snapshot` paper objects into eligible group workspaces without exposing source files, local attachments, or local notes
- Official-account binding handshake reserve sessions that connect callback evidence, existing bindings, and self-service grants, plus real official-account webpage OAuth completion for code/state exchange and safe binding create/reuse without introducing a generic app login system
- Mini read-only reserve endpoints that now consume structured digests, expose a safe subscription reserve summary, and keep mini grant auth separate from self-service grant auth
- Tauri 2 desktop shell with Rust-side pull sync, local SQLite cache, mutation outbox, minimal writeback for paper/progress/subscription policy edits, a local paper workspace layer, local markdown notes/templates, and a local review-matrix workflow that generates reviewer-matrix / response-letter drafts
- Pulse input-layer foundation with lightweight `WorkActivityEvent` capture, `ResearchWatchProfile` management, deterministic external-retrieval planning plus official-source execution/normalization boundaries, desktop-emitted work activity mutations, deterministic pulse-input preview APIs, a deterministic `yesterday_summary` pulse card, a deterministic `today_suggestion` pulse card generated from internal paper/progress/signal state only, and a deterministic `related_paper` pulse card generated only from persisted normalized external scholarly results
- Seed data, Docker Compose, pytest, Ruff, and CI

## Architecture
This project is built as a modular monolith.

Key boundaries:
- `domain`: enums and service contracts
- `db`: SQLAlchemy models, metadata, and session wiring
- `repositories`: persistence access
- `services`: application use cases, pulse engine, and delivery orchestration
- `adapters`: outbound channels and model-provider adapters
- `api`: FastAPI routes and exception handling

The code keeps pulse generation behind stable interfaces such as `FactCollector`, `RuleEngine`, `ModelProvider`, `CardValidator`, and `ChannelAdapter`. That makes the system easier to evolve toward more autonomous AI-agent-driven workflows without rewriting the backbone.

## Stack
- Python 3.12+
- FastAPI
- SQLAlchemy 2
- PostgreSQL
- Redis
- Docker Compose
- Pytest
- Ruff

## Local development
1. Create a virtual environment:
   `python3 -m venv .venv && source .venv/bin/activate`
2. Install dependencies:
   `make install`
3. Copy environment variables:
   `cp .env.example .env`
4. Start infrastructure:
   `make docker-up`
5. Run migrations:
   `make migrate`
6. Bootstrap a super admin for protected routes:
   `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
7. Seed demo data:
   `make seed`
8. Run the API:
   `make run-api`
9. Run the delivery worker:
   `make run-worker`
10. Run the daily scheduler:
   `make run-scheduler`
11. Install desktop dependencies if you are working on the shell:
   `make desktop-install`
12. Run the desktop shell:
   `make desktop-dev`
13. Install the subscription editor web shell if you want to test handoff-grant editing flows:
   `make subscription-editor-install`
14. Run the subscription editor web shell:
   `make subscription-editor-dev`
15. Install the result share shell if you want to demo public share links:
   `make result-share-install`
16. Run the result share shell:
   `make result-share-dev`
17. Install the internal workspace admin shell if you want to manage workspaces in a browser:
   `make workspace-admin-install`
18. Run the internal workspace admin shell:
   `make workspace-admin-dev`
19. Install the internal user workbench shell if you want read-only search across users, papers, and watch profiles:
   `make user-workbench-install`
20. Run the internal user workbench shell:
   `make user-workbench-dev`
21. Install the workspace invite shell if you want to test public invite bootstrap plus self-service claim flows:
   `make workspace-invite-install`
22. Run the workspace invite shell:
   `make workspace-invite-dev`

Group workspace/result sharing in this phase now has two thin browser shells:
- internal admin/operator management in `apps/group-workspace-admin-web`
- public read-only share rendering in `apps/result-share-web`
- public invite bootstrap plus self-service claim rendering in `apps/group-workspace-invite-web`
- public opaque-alias entry for the same result-share shell:
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - optional `GET /s/{alias}` redirect boundary
- self-service result collect reserve for:
  - `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - `POST /subscription-self-service/result-shares/{share_token}/collect`
  - `GET /subscription-self-service/share-aliases/{alias}/collect-preview`
  - `POST /subscription-self-service/share-aliases/{alias}/collect`
  - `GET /subscription-self-service/workspace-result-collections`
- PDFs, source files, local attachments, and local note contents are still excluded
- workspace invite/join now also has a backend reserve:
  - `GET /workspace-invites/{invite_token}/bootstrap`
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`

Internal support workflows in this phase now also have a separate read-only workbench in `apps/user-workbench-admin-web` for:
- user lookup
- paper lookup
- watch-profile lookup
- safe drilldown across those structured objects only

Open API docs at `http://127.0.0.1:8000/docs`.

## Desktop shell
The repository now includes a desktop client skeleton under `apps/desktop` using:
- Tauri 2
- React
- TypeScript
- Vite

The shell currently uses device-token sync against:
- `GET /sync/me`
- `POST /sync/push`
- `GET /sync/feed`
- `POST /sync/ack`

Desktop prerequisites on macOS include:
- Xcode Command Line Tools
- Rust

The desktop shell now also supports a local-only paper workspace:
- user-chosen workspace root
- deterministic `papers/<paper_id>/...` folder layout
- managed-copy attachment import
- local attachment metadata index in desktop SQLite

This workspace layer does not upload files, sync attachments to the backend, or run OCR/AI analysis in v1.

The desktop shell now also supports local-only per-paper notes:
- markdown note files under `papers/<paper_id>/notes/`
- built-in templates for research notes, revision planning, response letters, reviewer matrices, and submission checklists
- note metadata indexed in desktop SQLite while note content remains file-backed on disk

These notes do not sync to the backend and do not use AI generation in v1.

The desktop shell now also supports a local-only review matrix workflow:
- manual review rounds per paper
- structured reviewer comment rows with dispositions and response summaries
- generated local markdown drafts for `reviewer_matrix` and `response_letter`

Review matrix data and generated drafts stay local in v1 and do not sync to the backend.

Selected desktop-local actions now also emit lightweight `work_activity.record` mutations through the existing sync outbox so the cloud can build pulse inputs without receiving local file or note contents.

Desktop Settings now also exposes synced delivery-control fields from cached `SubscriptionPolicy` rows:
- `enabled`
- `quiet_hours`
- `policy.timezone`
- `policy.allowed_weekdays`
- `policy.muted_until`
- `policy.minimum_selected_cards`
- `policy.skip_if_no_today_focus`

These edits still queue `subscription_policy.patch` through the existing sync writeback path. The Settings hint panel is local-only and is not an authoritative backend dispatch decision.

Desktop Today now also prefers the orchestrated sectioned digest payload when available:
- `today_focus`
- `yesterday_recap`
- `signal_updates`
- `related_papers`
- `other_updates`

Older cached digests that only have `highlights` / `items` still render through a deterministic desktop fallback path.

Mini read-only routes now also prefer the same orchestrated sectioned digest payload when available and fall back to legacy `highlights` / `items` when older digest content is all that exists.

Mini reserve now also exposes a short-lived editor handoff bridge:
- `POST /mini/subscription-reserve/editor-handoff`
- `GET /mini/subscription-reserve/editor-handoff-status`

These routes mint or inspect a narrow handoff token for `/subscription-editor/*` only. Mini grants still cannot patch subscription settings directly.
Mini reserve now also exposes an informational `workspace_invite_reserve` block:
- mini grant still cannot claim workspace membership directly
- a separate self-service grant is required
- invite claim remains self-service-only in this phase
Mini reserve now also exposes an informational `workspace_collect_reserve` block:
- mini grant still cannot collect shared results into a workspace directly
- a separate self-service grant is required
- collect remains limited to `digest_issue` and `paper_snapshot` in this phase

## Subscription editor web shell
The repository now also includes a thin browser/WebView-friendly shell under `apps/subscription-editor-web` using:
- React
- TypeScript
- Vite

This shell:
- accepts a short-lived handoff token from manual paste or `#handoff_token=...`
- keeps the token in memory only
- calls only:
  - `GET /subscription-editor/bootstrap`
  - `GET /subscription-editor/contract`
  - `POST /subscription-editor/settings/preview`
  - `PATCH /subscription-editor/settings`
- does not create a new auth system or generic app login surface

## Result share web shell
The repository now also includes a thin public browser shell under `apps/result-share-web` using:
- React
- TypeScript
- Vite

This shell:
- accepts a raw share token from `/share/<token>`, query/fragment fallback, or manual paste
- accepts an opaque share alias from `/share-alias/<alias>`, query/fragment fallback, or manual paste
- accepts an optional self-service token from manual paste or local-dev query/fragment fallback
- keeps query/fragment token or alias hints in memory only after clearing them from the visible URL
- calls only:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - `POST /subscription-self-service/result-shares/{share_token}/collect`
  - `GET /subscription-self-service/share-aliases/{alias}/collect-preview`
  - `POST /subscription-self-service/share-aliases/{alias}/collect`
  - `GET /subscription-self-service/workspace-result-collections`
- renders read-only `digest_issue`, `paper_snapshot`, and `workspace_board` views plus an explicit self-service collect flow for collectable share kinds
- shows a manual invite/join handoff summary on `workspace_board` shares without mixing the share page into invite claim auth
- shows a separate manual result-collect handoff summary on `workspace_board` shares without turning the board share itself into a collect source
- keeps raw token mode and opaque alias mode additive over the same underlying `ResultShareGrant` semantics
- does not add login, editing, or source-file sharing

The separate invite shell under `apps/group-workspace-invite-web` now also:
- keeps invite/self-service tokens in memory only
- stays focused on membership bootstrap, claim preview, claim, and membership summaries
- may show a manual result-collect handoff summary after claimed / already_member / membership states
- still does not perform collect directly

## Group workspace admin web shell
The repository now also includes a thin internal browser shell under `apps/group-workspace-admin-web` using:
- React
- TypeScript
- Vite

This shell:
- accepts an admin/operator bearer token from manual paste or query/fragment fallback
- keeps the token in memory only
- manages only:
  - `GET/POST/PATCH /admin/group-workspaces`
  - `GET /admin/group-workspaces/{workspace_id}/board`
  - member and paper add/remove routes
  - `workspace_board` share-grant create/revoke flows
- reuses existing `GET /users` and `GET /papers` reads as internal lookup sources
- does not add end-user login, public editing, or source-file sharing

## Group workspace invite web shell
The repository now also includes a thin public browser shell under `apps/group-workspace-invite-web` using:
- React
- TypeScript
- Vite

This shell:
- accepts an invite token from `/invite/<token>`, query/fragment fallback, or manual paste
- accepts an optional self-service token from manual paste or local-dev query/fragment fallback
- keeps both tokens in memory only after clearing visible URL hints
- calls only:
  - `GET /workspace-invites/{invite_token}/bootstrap`
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
- does not add a generic login system, source-file sharing, or browser token persistence

## User workbench admin web shell
The repository now also includes a thin internal browser shell under `apps/user-workbench-admin-web` using:
- React
- TypeScript
- Vite

This shell:
- accepts a viewer/operator/super_admin bearer token from manual paste or query/fragment fallback
- keeps the token in memory only
- reads only:
  - `GET /admin/user-workbench/users`
  - `GET /admin/user-workbench/users/{user_id}`
  - `GET /admin/user-workbench/papers`
  - `GET /admin/user-workbench/papers/{paper_id}`
  - `GET /admin/user-workbench/watch-profiles`
- supports drilldown:
  - user -> papers
  - user -> watch profiles
  - paper -> watch profiles
- does not add end-user login, business writes, or source-file sharing

Official-account binding reserve now also adds:
- admin-created handshake sessions with one-time state tokens
- admin reconciliation candidate listing over unmatched subscribe callback events
- explicit callback-event claim into `WeChatIdentityBinding`
- self-service handshake reserve bootstrap/create/read/cancel endpoints
- mini read-only `binding_handoff_reserve` summary
- real webpage OAuth completion on top of the reserve:
  - self-service `oauth-start`
  - admin authorize-url issuance
  - public callback `code/state` exchange
  - safe binding create/reuse and callback-evidence linking

## Pulse input layer
The backend now includes a pulse input layer for future retrieval and recap work:
- `WorkActivityEvent` for structured "what the user did" signals
- `ResearchWatchProfile` for structured "what the user should watch" interests
- deterministic external retrieval planning through `ExternalRetrievalPlan`
- official-source retrieval execution through `ExternalRetrievalRun`
- normalized scholarly result storage through `ExternalRetrievedRecord`
- `GET /pulse/input-preview/{user_id}` for a deterministic preview of the current input window, activity summary, effective watch seeds, and compact retrieval planning
- `GET /external-retrieval/input-preview/{user_id}` for full retrieval-input preview
- `POST /external-retrieval/plans/build/{user_id}` for plan-hash-upserted plan persistence
- `GET /external-retrieval/provider-status` for safe execution readiness
- `POST /external-retrieval/plans/execute/{plan_id}` for official-source fetch + normalize
- `GET /external-retrieval/runs` and `GET /external-retrieval/results` for inspecting persisted runs and normalized records
- `yesterday_summary` pulse cards built only from previous-local-day `WorkActivityEvent` rows
- `today_suggestion` pulse cards built only from internal paper, progress, signal, and policy-timezone context
- `related_paper` pulse cards built only from persisted `ExternalRetrievedRecord` rows whose runs completed successfully

This phase still keeps external-card consumption narrow:
- no related-news cards
- no AI summarization
- no AI ranking of fetched scholarly records

Yesterday-summary behavior in this phase:
- uses previous-local-day activity only
- excludes `source=system` events
- generates at most one summary candidate per user per run
- persists as a normal `PulseCard` when selected

Today-suggestion behavior in this phase:
- uses current internal paper state only
- excludes paused papers
- generates at most one suggestion candidate per user per run
- supports `execute_next_action`, `resolve_blocker`, and `define_next_action`
- persists as a normal `PulseCard` when selected

## Common commands
- `make install`: install runtime and dev dependencies
- `make run` or `make run-api`: run the FastAPI development server
- `make migrate`: apply Alembic migrations
- `make seed`: load local demo data
- `make worker`: process pending pulse and delivery jobs once
- `make run-worker`: run the polling delivery worker
- `make scheduler-tick`: run one scheduler tick
- `make run-scheduler`: run the polling scheduler
- `make bootstrap-admin EMAIL=... PASSWORD=...`: create or update the bootstrap super admin
- `make lint`: run Ruff checks
- `make format`: run Ruff formatting
- `make test`: run the test suite
- `make check`: run lint and tests
- `make docker-up`: start API dependencies with Docker Compose
- `make docker-down`: stop Docker Compose services
- `make desktop-install`: install desktop dependencies under `apps/desktop`
- `make desktop-dev`: run the Tauri desktop shell in development mode
- `make desktop-lint`: run desktop lint and typecheck
- `make desktop-test`: run desktop frontend tests plus Rust cache/sync tests
- `make desktop-build-web`: build the desktop web frontend without native packaging
- `make subscription-editor-install`: install subscription-editor shell dependencies under `apps/subscription-editor-web`
- `make subscription-editor-dev`: run the subscription-editor shell in development mode
- `make subscription-editor-lint`: run subscription-editor shell lint and typecheck
- `make subscription-editor-test`: run subscription-editor shell tests
- `make subscription-editor-build`: build the subscription-editor shell
- `make result-share-install`: install result-share shell dependencies under `apps/result-share-web`
- `make result-share-dev`: run the result-share shell in development mode
- `make result-share-lint`: run result-share shell lint and typecheck
- `make result-share-test`: run result-share shell tests
- `make result-share-build`: build the result-share shell
- `make workspace-admin-install`: install workspace-admin shell dependencies under `apps/group-workspace-admin-web`
- `make workspace-admin-dev`: run the workspace-admin shell in development mode
- `make workspace-admin-lint`: run workspace-admin shell lint and typecheck
- `make workspace-admin-test`: run workspace-admin shell tests
- `make workspace-admin-build`: build the workspace-admin shell
- `make user-workbench-install`: install user-workbench shell dependencies under `apps/user-workbench-admin-web`
- `make user-workbench-dev`: run the user-workbench shell in development mode
- `make user-workbench-lint`: run user-workbench shell lint and typecheck
- `make user-workbench-test`: run user-workbench shell tests
- `make user-workbench-build`: build the user-workbench shell
- `make subscription-editor-install`: install web-shell dependencies under `apps/subscription-editor-web`
- `make subscription-editor-dev`: run the subscription editor web shell
- `make subscription-editor-lint`: run editor web lint and typecheck
- `make subscription-editor-test`: run editor web tests
- `make subscription-editor-build`: build the editor web shell

## Environment
Main environment variables are documented in `.env.example`.

Important values:
- `APP_DATABASE_URL`: optional override for local SQLite or test databases
- `POSTGRES_*`: PostgreSQL connection settings
- `REDIS_*`: Redis connection settings
- `APP_DEFAULT_TIMEZONE`: fallback timezone for daily scheduling
- `APP_PULSE_DEFAULT_SEND_HOUR_LOCAL`: default local send hour for daily policies
- `APP_PULSE_DEFAULT_SEND_MINUTE_LOCAL`: default local send minute for daily policies
- `APP_MAX_DELIVERY_RETRIES`: retry ceiling before dead-letter
- `APP_DELIVERY_RETRY_DELAY_SECONDS`: retry backoff in seconds
- `APP_WORKER_HEARTBEAT_INTERVAL_SECONDS`: expected heartbeat cadence for local workers
- `APP_WORKER_LEASE_SECONDS`: lease duration when a worker claims a pulse job
- `APP_AUTH_ACCESS_TOKEN_TTL_MINUTES`: admin access token lifetime
- `APP_AUTH_REFRESH_TOKEN_TTL_DAYS`: server-revocable refresh token lifetime
- `APP_AUTH_JWT_SECRET`: JWT signing secret for admin access tokens
- `APP_AUTH_JWT_ISSUER`: expected issuer claim for admin access tokens
- `APP_AUTH_JWT_AUDIENCE`: expected audience claim for admin access tokens
- `APP_INTERNAL_SERVICE_TOKEN`: bearer token for internal `/ops/*` and readiness callers
- `APP_SYNC_DEVICE_TOKEN_TTL_DAYS`: sync device token lifetime
- `APP_SYNC_FEED_DEFAULT_LIMIT`: default incremental sync page size
- `APP_SYNC_FEED_MAX_LIMIT`: max allowed sync feed page size
- `APP_SYNC_PUSH_MAX_BATCH_SIZE`: max mutations accepted per sync push batch
- `APP_MINI_READ_GRANT_DEFAULT_TTL_HOURS`: default preview-grant lifetime for `/mini/*`
- `APP_MINI_PAPERS_DEFAULT_LIMIT`: default compact paper page size for mini reads
- `APP_MINI_PAPERS_MAX_LIMIT`: max compact paper page size for mini reads
- `APP_SUBSCRIPTION_EDITOR_WEB_ALLOWED_ORIGINS`: browser origins allowed to call the editor shell APIs during local development
- `APP_GROUP_WORKSPACE_INVITES_ENABLED`: enable or disable workspace invite issuance and claim flows
- `APP_GROUP_WORKSPACE_INVITE_DEFAULT_MAX_CLAIMS`: default invite claim capacity when create does not override it
- `APP_GROUP_WORKSPACE_INVITE_TTL_HOURS`: default invite lifetime
- `APP_GROUP_WORKSPACE_INVITE_PUBLIC_BOOTSTRAP_ENABLED`: enable or disable public invite bootstrap separately
- `APP_DIGEST_SIGNAL_UPDATES_MAX_ITEMS`: max `signal_change` cards kept in the `signal_updates` digest section
- `APP_DIGEST_RELATED_PAPERS_MAX_ITEMS`: max `related_paper` cards kept in the `related_papers` digest section
- `APP_DIGEST_OTHER_UPDATES_MAX_ITEMS`: max overflow cards kept in the `other_updates` digest section
- `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT`: when true, digest orchestration also upserts prepared official-account publication jobs without dispatching sends
- `APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT`: when true, orchestration may also trigger one issue-level official-account dispatch run
- `APP_DIGEST_DISPATCH_MAX_PUBLICATION_JOBS_PER_RUN`: cap for eligible official-account jobs dispatched under one digest issue run
- `APP_DIGEST_DISPATCH_RETRY_FAILED_JOBS`: allow failed official-account jobs to re-enter issue-level dispatch eligibility by default
- `APP_DIGEST_DISPATCH_PREPARE_IF_MISSING`: allow issue-level dispatch to prepare official-account jobs first when none exist yet
- `APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE`: when true, auto-dispatch only runs in `real` mode with real send enabled
- Official-account delivery control policy keys now live in `SubscriptionPolicy.policy`:
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- `SubscriptionPolicy.quiet_hours` remains the separate quiet-window field for user-side delivery gating
- `SubscriptionSelfServiceGrant` now reserves a separate bearer-token auth boundary for `/subscription-self-service/*`
- mini read-only subscription reserve is exposed through:
  - `GET /mini/subscription-reserve`
  - mini grant auth only
  - authoritative delivery preview reuse without write access
- self-service editor reserve is exposed through:
  - `GET /subscription-self-service/editor-bootstrap`
  - `GET /subscription-self-service/editor-contract`
  - `POST /subscription-self-service/settings/preview`
  - `PATCH /subscription-self-service/settings?include_preview=true`
  - authoritative preview-before-save without persisting draft state
- group workspace invite/join reserve is exposed through:
  - `GET /workspace-invites/{invite_token}/bootstrap`
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
  - public bootstrap stays read-only
  - membership claim stays behind self-service grant auth
- `subscription-self-service` editable fields are limited to:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- mini read-only reserve now also includes a `self_service_entry` handoff block describing:
  - mini grant remains read-only
  - a separate self-service grant is still required for edits
  - editor contract and editor preview are available for future clients
- `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`: official-account provider mode: `disabled`, `dry_run`, or `real`
- `APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND`: outbound transport strategy, currently `template_notice`
- `APP_WECHAT_OFFICIAL_APP_ID`: official-account app id for provider readiness and callback matching
- `APP_WECHAT_OFFICIAL_APP_SECRET`: official-account secret for real access-token refresh
- `APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID`: template-notice template id used in real mode
- `APP_WECHAT_OFFICIAL_CALLBACK_TOKEN`: signature token for callback verification
- `APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY`: reserved AES key for future richer callback handling
- `APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED`: enable or disable callback ingress handling
- `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED`: explicit safety switch required in addition to `provider_mode=real`
- `APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS`: early-refresh buffer for cached access tokens
- `APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS`: connect timeout for provider HTTP calls
- `APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS`: read timeout for provider HTTP calls
- `APP_OFFICIAL_ACCOUNT_MAX_RETRIES`: retry budget for real outbound template sends
- `APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON`: optional logical-field to template-field mapping JSON
- `APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID`: default mini-program app id for landing payloads
- `APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL`: optional base URL for future article landing payloads
- `APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS`: dispatch timeout budget reported in provider status
- `APP_PULSE_WEIGHT_TODAY_SUGGESTION`: base score weight for `today_suggestion`
- `APP_PULSE_TODAY_SUGGESTION_STALE_DAYS_THRESHOLD`: stale-progress threshold used in today-suggestion selection and scoring
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_PRIORITY`: multiplier for paper priority in today-suggestion scoring
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_HAS_NEXT_ACTION`: bonus when the chosen paper already has a concrete next action
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_REVISION_STAGE`: bonus when the chosen paper is in revision
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_STALE_PROGRESS`: bonus when the chosen paper has gone stale past the threshold
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_BLOCKER_PRESENT`: bonus when the chosen paper is currently blocked
- `APP_PULSE_WEIGHT_YESTERDAY_SUMMARY`: base score weight for `yesterday_summary`
- `APP_PULSE_YESTERDAY_SUMMARY_MIN_EVENTS`: minimum qualifying previous-day activity events before candidate generation
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_ACTIVITY_DIVERSITY`: bonus when multiple activity types were recorded
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_MULTI_PAPER`: bonus when previous-day work touched multiple papers
- `APP_PULSE_WEIGHT_RELATED_PAPER`: base score weight for `related_paper`
- `APP_PULSE_MODIFIER_RELATED_PAPER_HAS_DOI`: bonus when a normalized scholarly result has a DOI
- `APP_PULSE_MODIFIER_RELATED_PAPER_MATCH_REASON_COUNT`: per-match-reason bonus for normalized related-paper candidates
- `APP_PULSE_MODIFIER_RELATED_PAPER_LINKED_PAPER`: bonus when the normalized record links back to a known internal paper
- `APP_PULSE_MODIFIER_RELATED_PAPER_RECENT_RETRIEVAL`: bonus when the source retrieval run completed recently
- `APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS`: lookback window for eligible completed related-paper retrieval results
- `APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN`: cap for deterministic related-paper candidates before scoring/selection
- `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`: historical resurfacing window for the same canonical scholarly result
- `APP_EXTERNAL_RETRIEVAL_MODE`: `disabled`, `plan_only`, or `execute`
- `APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES`: enabled official sources for planning and execution
- `APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER`: cap for persisted planning rows built per user
- `APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN`: keyword cap per deterministic plan
- `APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN`: topic cap per deterministic plan
- `APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT`: activity lookback window used for retrieval seeds
- `APP_EXTERNAL_RETRIEVAL_HTTP_CONNECT_TIMEOUT_SECONDS`: connect timeout for external source calls
- `APP_EXTERNAL_RETRIEVAL_HTTP_READ_TIMEOUT_SECONDS`: read timeout for external source calls
- `APP_EXTERNAL_RETRIEVAL_MAX_RESULTS_PER_PLAN`: per-plan result cap during execution
- `APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES`: reuse window for recent successful plan runs
- `APP_EXTERNAL_RETRIEVAL_OPENALEX_API_KEY`: optional OpenAlex API key
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO`: optional Crossref polite-access email
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME`: optional Crossref user-agent app label
- `APP_EXTERNAL_RETRIEVAL_MODE`: `disabled` or `plan_only`
- `APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES`: comma-separated enabled planning sources for this phase
- `APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER`: max persisted plans produced per build
- `APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN`: keyword cap used by source plan builders
- `APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN`: topic cap used by source plan builders
- `APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT`: recent activity lookback used for touched-paper seed context

Real official-account sending stays opt-in. Local and test setups do not require live WeChat credentials unless you intentionally enable `provider_mode=real` and `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED=true`.
Mini-program access is reserve-only and read-only in this phase.

## Running workers and scheduler
Run one-off local cycles:

`make worker`

`make scheduler-tick`

Run long-lived local loops:

`python -m research_pulse_cn.worker.main --limit 20 --poll-interval 15`

`python -m research_pulse_cn.scheduler.main --poll-interval 60`

With Docker Compose, the codebase now exposes separate `api`, `worker`, and `scheduler` services.

## Operations surface
- Auth:
  - `POST /auth/login`
  - `POST /auth/refresh`
  - `POST /auth/logout`
  - `GET /auth/me`
- Admin:
  - `GET /admin/admin-accounts`
  - `POST /admin/admin-accounts`
  - `PATCH /admin/admin-accounts/{admin_account_id}`
  - `POST /admin/admin-accounts/{admin_account_id}/set-password`
  - `GET /admin/audit-logs`
  - `GET /admin/client-devices`
  - `POST /admin/client-devices`
  - `POST /admin/client-devices/{client_device_id}/rotate-token`
  - `POST /admin/client-devices/{client_device_id}/revoke`
  - `GET /admin/wechat-bindings`
  - `POST /admin/wechat-bindings`
  - `PATCH /admin/wechat-bindings/{binding_id}`
  - `GET /admin/digest-issues`
  - `GET /admin/digest-issues/{digest_issue_id}`
  - `POST /admin/digest-issues/build/{user_id}`
  - `POST /admin/digest-issues/orchestrate/{user_id}`
  - `GET /admin/digest-issues/{digest_issue_id}/daily-preview`
  - `GET /admin/digest-issues/{digest_issue_id}/dispatch-preview`
  - `POST /admin/digest-issues/{digest_issue_id}/dispatch`
  - `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
  - `GET /admin/digest-publication-jobs`
  - `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
  - `GET /admin/digest-publication-attempts`
  - `GET /admin/digest-dispatch-runs`
  - `GET /admin/digest-dispatch-runs/{dispatch_run_id}`
  - `GET /admin/official-account/provider-status`
  - `POST /admin/official-account/provider-token/refresh`
  - `GET /admin/official-account/callback-events`
  - `GET /admin/mini-read-grants`
  - `POST /admin/mini-read-grants`
  - `POST /admin/mini-read-grants/{grant_id}/revoke`
- Health:
  - `GET /health`
  - `GET /health/live`
  - `GET /health/ready`
- Pulse:
  - `POST /pulse/preview/{user_id}`
  - `POST /pulse/run/{user_id}`
  - `GET /pulse/input-preview/{user_id}`
- Research inputs:
  - `GET /work-activity-events`
  - `GET /research-watch-profiles`
  - `POST /research-watch-profiles`
  - `PATCH /research-watch-profiles/{profile_id}`
  - `DELETE /research-watch-profiles/{profile_id}`
  - `POST /research-watch-profiles/bootstrap/{paper_id}`
- Ops:
  - `GET /ops/metrics`
  - `GET /ops/heartbeats`
  - `GET /ops/pulse-jobs`
  - `GET /ops/delivery-jobs`
  - `GET /ops/delivery-attempts`
  - `POST /ops/scheduler/tick`
  - `POST /ops/delivery-jobs/{delivery_job_id}/requeue`
  - `POST /ops/pulse-jobs/{pulse_job_id}/replay`
- Sync:
  - `GET /sync/me`
  - `GET /sync/feed`
- `POST /sync/push`
- `POST /sync/ack`

Desktop writeback in v1 is intentionally narrow:
- `paper.patch`
- `progress_event.create`
- `subscription_policy.patch`
- `work_activity.record`
- Mini:
  - `GET /mini/bootstrap`
  - `GET /mini/today`
  - `GET /mini/digest-issues/{digest_issue_id}`
  - `GET /mini/papers`
  - `GET /mini/papers/{paper_id}`
- Integrations:
  - `GET /integrations/wechat/official-account/callback`
  - `POST /integrations/wechat/official-account/callback`

## Seeded demo profile
`make seed` creates:
- one demo user
- two demo papers
- progress and signal history
- in-app and webhook delivery policies

## Structure
- `src/research_pulse_cn`: application code
- `tests`: test suite
- `docs`: product and implementation notes

## Pulse scoring
The ranking pipeline is documented in [docs/pulse_scoring.md](docs/pulse_scoring.md).

## Operations guide
Operational scheduling, replay, requeue, heartbeats, attempts, and metrics are documented in [docs/operations.md](docs/operations.md).

## Auth and admin boundary
Admin authentication, RBAC, internal service auth, audit logs, and bootstrap flow are documented in [docs/auth_admin_boundary.md](docs/auth_admin_boundary.md).

## Sync foundation
Device identity, incremental feed, mutation idempotency, and future lightweight-client alignment are documented in [docs/sync_foundation.md](docs/sync_foundation.md).

## Desktop Tauri skeleton
Desktop shell layout, local cache, pull-sync flow, and developer workflow are documented in [docs/desktop_tauri_skeleton_v1.md](docs/desktop_tauri_skeleton_v1.md).

## Official-account digest reserve
Digest issues, WeChat identity binding, and publication preparation without real external sends are documented in [docs/official_account_digest_reserve.md](docs/official_account_digest_reserve.md).

Deterministic sectioned daily-digest orchestration for official-account publication preparation is documented in [docs/official_account_daily_digest_orchestration_v1.md](docs/official_account_daily_digest_orchestration_v1.md).

Issue-level official-account daily dispatch orchestration is documented in [docs/official_account_daily_dispatch_v1.md](docs/official_account_daily_dispatch_v1.md).

## Mini-program read-only reserve
Mini preview grants, compact mobile read models, and derived paper progress percentages are documented in [docs/mini_program_readonly_reserve.md](docs/mini_program_readonly_reserve.md).

User-side editor reserve bootstrap, machine-readable contract, and preview-before-save semantics are documented in [docs/user_subscription_self_service_editor_reserve_v1.md](docs/user_subscription_self_service_editor_reserve_v1.md).

## Official-account provider boundary
Dry-run dispatch, callback ingress, subscription-state updates, and provider-safe settings are documented in [docs/official_account_provider_boundary.md](docs/official_account_provider_boundary.md).

## Official-account real send
Real-mode activation, access-token caching, template-notice transport, and credential-backed per-binding dispatch are documented in [docs/official_account_real_send_v1.md](docs/official_account_real_send_v1.md).
