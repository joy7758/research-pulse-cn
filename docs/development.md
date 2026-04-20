# Development Guide

## Current Product Direction
- Active direction:
  - China-first Research Pulse
- Product focus:
  - import papers
  - track paper and research progress
  - generate daily Research Pulse
  - deliver through desktop, official account, and mini-program surfaces
- Frozen direction:
  - admin preset, registry, threshold, report, print, copy, and audit overbuild
- Read these docs before planning new phases:
  - `docs/product_pivot_china_first_research_pulse_v1.md`
  - `docs/zotero_reference_strategy_v1.md`
  - `docs/frozen_admin_overbuild_scope_v1.md`
  - `docs/mvp_china_first_research_pulse_roadmap_v1.md`

## Prerequisites
- Python 3.12+
- Docker and Docker Compose
- Node.js 20+
- Rust toolchain
- macOS desktop work requires Xcode Command Line Tools for Tauri

## First-time setup
1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `make install`
4. `cp .env.example .env`

## Daily workflow
1. Start infrastructure: `make docker-up`
2. Apply migrations: `make migrate`
3. Bootstrap an admin: `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
4. Seed demo data if needed: `make seed`
5. Run API: `make run-api`
6. Run worker once: `make worker`
7. Run scheduler once: `make scheduler-tick`
8. Run long-lived worker if needed: `make run-worker`
9. Run long-lived scheduler if needed: `make run-scheduler`

## Checks
- Lint: `make lint`
- Format: `make format`
- Tests: `make test`
- Full local gate: `make check`

## MVP Smoke Test
- Targeted Pivot-2 to Pivot-9 chain:
  - `.venv/bin/python -m pytest tests/test_import_formats_foundation.py tests/test_import_preview_commit.py tests/test_paper_progress_workbench.py tests/test_research_pulse_over_imported_papers.py tests/test_official_account_daily_summary_mvp.py tests/test_desktop_notification_mvp.py tests/test_mini_program_detail_mvp.py tests/test_mvp_end_to_end_smoke.py`
- Full backend suite:
  - `.venv/bin/python -m pytest`
- Ruff:
  - `.venv/bin/python -m ruff format src tests`
  - `.venv/bin/python -m ruff check .`
- MVP smoke-test document:
  - `docs/mvp_end_to_end_smoke_test_v1.md`
- Guardrails for MVP smoke work:
  - do not add real WeChat API calls
  - do not add real desktop notification calls
  - do not add real mini-program frontend files
  - do not add external LLM or external network dependencies
  - keep official-account / desktop / mini outputs at `draft` / `preview` / `not_sent`

## API Contract Tests
- Contract docs:
  - `docs/api_contract_mvp_v1.md`
  - `docs/schema_contract_mvp_v1.md`
  - `docs/error_warning_contract_mvp_v1.md`
- Targeted contract tests:
  - `.venv/bin/python -m pytest tests/test_api_contract_mvp.py tests/test_schema_contract_mvp.py tests/test_mvp_end_to_end_smoke.py`
- Related MVP chain tests:
  - `.venv/bin/python -m pytest tests/test_import_formats_foundation.py tests/test_import_preview_commit.py tests/test_paper_progress_workbench.py tests/test_research_pulse_over_imported_papers.py tests/test_official_account_daily_summary_mvp.py tests/test_desktop_notification_mvp.py tests/test_mini_program_detail_mvp.py tests/test_mvp_end_to_end_smoke.py tests/test_api_contract_mvp.py tests/test_schema_contract_mvp.py`
- Inspect OpenAPI locally without starting a separate export toolchain:
  ```bash
  .venv/bin/python - <<'PY'
  from research_pulse_cn.app import create_app
  import json
  print(json.dumps(create_app().openapi(), ensure_ascii=False, indent=2))
  PY
  ```
- Guardrails:
  - do not add real WeChat API integration while adjusting docs or tests
  - do not add real desktop notification calls
  - do not add mini-program frontend files
  - do not add external LLM or external network calls

## MVP UI Direction
- Design docs:
  - `docs/ui_reference_audit_mvp_v1.md`
  - `docs/mvp_interface_principles_v1.md`
  - `docs/mvp_information_architecture_v1.md`
  - `docs/mvp_user_flows_v1.md`
  - `docs/mvp_copywriting_guidelines_cn_v1.md`
- This phase is documentation-only:
  - do not add frontend code
  - do not add backend features
  - do not add migrations
  - do not add dependencies
- UI design guardrails:
  - keep the homepage centered on today's Research Pulse
  - keep import as a short preview-first flow
  - keep paper progress language closer to research work than system administration
  - keep official-account / desktop / mini outputs explicit as `draft` / `preview`

## MVP Wireframe Spec
- Design-2 docs:
  - `docs/mvp_wireframes_v1.md`
  - `docs/mvp_page_state_matrix_v1.md`
  - `docs/mvp_component_inventory_v1.md`
  - `docs/mvp_interaction_spec_v1.md`
  - `docs/mvp_wireframe_acceptance_checklist_v1.md`
- This phase is also documentation-only:
  - do not add frontend code
  - do not add backend code
  - do not add migrations
  - do not add dependencies
- Review checklist before closing the phase:
  - run `git diff --name-only | grep -Ev '^(docs/|README\\.md$)' || true`
  - confirm every wireframe page keeps a single primary action
  - confirm all channel pages still show `draft` / `preview` / `not_sent`

## MVP Visual Language and Prototype Spec
- Design-3 docs:
  - `docs/mvp_visual_language_v1.md`
  - `docs/mvp_design_tokens_v1.md`
  - `docs/mvp_component_visual_rules_v1.md`
  - `docs/mvp_clickable_prototype_spec_v1.md`
  - `docs/mvp_responsive_layout_rules_v1.md`
  - `docs/mvp_accessibility_readability_v1.md`
  - `docs/mvp_visual_acceptance_checklist_v1.md`
- This phase is also documentation-only:
  - do not add frontend code
  - do not add backend code
  - do not add migrations
  - do not add dependencies
- Review checklist before closing the phase:
  - run `git diff --name-only | grep -Ev '^(docs/|README\\.md$)' || true`
  - confirm `draft` / `preview` / `not_sent` remain explicit visual states
  - confirm no page introduces real WeChat / desktop / mini-program capability language

## Run MVP local demo
- Demo docs:
  - `docs/mvp_demo_fixture_pack_v1.md`
  - `docs/mvp_local_demo_script_v1.md`
- Run the local offline demo:
  - `.venv/bin/python scripts/run_mvp_demo.py --output-dir /tmp/research_pulse_cn_demo --date 2026-04-19 --format csv --max-items-per-section 3`
- Demo script test:
  - `.venv/bin/python -m pytest tests/test_mvp_demo_script.py tests/test_mvp_end_to_end_smoke.py tests/test_api_contract_mvp.py tests/test_schema_contract_mvp.py`
- Full suite:
  - `.venv/bin/python -m pytest`
- Guardrails:
  - keep the demo local and offline
  - do not add real WeChat API integration
  - do not add real desktop notification calls
  - do not add real mini-program frontend files
  - do not add external-model or external-network dependencies
  - generated output defaults to `/tmp` and should not be committed

## Frontend planning only
- Frontend-0 docs:
  - `docs/frontend_technical_feasibility_review_v1.md`
  - `docs/frontend_mvp_scope_v1.md`
  - `docs/frontend_api_consumption_plan_v1.md`
  - `docs/frontend_demo_data_mapping_v1.md`
  - `docs/frontend_component_mapping_v1.md`
  - `docs/frontend_implementation_sequence_v1.md`
  - `docs/frontend_acceptance_checklist_v1.md`
  - `docs/PROMPT_FRONTEND_1_MINIMAL_WEB_SHELL_CN.md`
- This phase is documentation-only:
  - do not run npm / pnpm / yarn
  - do not add `package.json`
  - do not add frontend runtime files
- Recommended docs-only checks before closing:
  - `git diff --name-only | grep -Ev '^(docs/|README\\.md$)' || true`
  - `git diff --name-only | grep -E '^(src/|tests/|scripts/|demo/|alembic/|migrations/|pyproject\\.toml|requirements|package\\.json|pnpm-lock|yarn.lock|package-lock\\.json)' || true`
  - `git diff --name-only | grep -Ei 'package\\.json|pnpm-lock|yarn.lock|package-lock\\.json|vite|next|react|vue|svelte|tailwind|electron|tauri' || true`

## Frontend minimal web shell
- Frontend-1 app path:
  - `apps/research-pulse-web`
- Hardening doc:
  - `docs/frontend_minimal_web_shell_hardening_v1.md`
- Frontend-2 doc:
  - `docs/frontend_paper_progress_page_v1.md`
- Frontend-2 hardening doc:
  - `docs/frontend_paper_progress_page_hardening_v1.md`
- Frontend-3 doc:
  - `docs/frontend_channel_draft_preview_pages_v1.md`
- Frontend-3 hardening doc:
  - `docs/frontend_channel_draft_preview_pages_hardening_v1.md`
- Frontend-4 doc:
  - `docs/frontend_channel_draft_preview_pages_v2.md`
- Install:
  - `cd apps/research-pulse-web && npm install`
- Run:
  - `npm run dev`
- Build:
  - `npm run build`
- Static checks:
  - `npm run lint`
  - `npm run typecheck`
- Current boundary:
  - the minimal shell currently contains 7 pages:
    - today pulse
    - import / import preview
    - pulse detail
    - paper progress
    - official-account draft
    - desktop notification draft
    - mini-program detail preview
  - it defaults to mock mode and curated demo JSON
  - it also includes curated `default / empty / issues / broken` mock scenarios for state validation
  - it does not add login, admin, real channel delivery, or backend contract changes
- Frontend-2 checks before closing:
  - confirm the only new page is `paper progress`
  - confirm no login / admin / settings / channel draft pages were added
  - confirm the page still runs fully in mock mode
  - confirm the primary action remains `更新选中论文进度`
- Frontend-2 hardening checks before closing:
  - confirm filter chips still show counts and selected state
  - confirm search + filter empty state exposes `清除筛选` / `清除搜索`
  - confirm `更新选中论文进度` stays disabled until one paper is selected
  - confirm the page still says `本地预览，不会真实修改论文库`
- Frontend-3 checks before closing:
  - confirm the only new pages are:
    - official-account draft
    - desktop notification draft
    - mini-program detail preview
  - confirm every channel page still shows `draft / preview / not_sent`
  - confirm copy actions stay local and do not trigger real send / push / mini-program abilities
  - confirm build, lint, typecheck, ruff and pytest all pass
- Frontend-3 hardening checks before closing:
  - confirm channel-page primary actions show disabled reasons when内容为空
  - confirm official / desktop / mini pages still keep `mock-only` copy and no real send wording
  - confirm mini tabs expose `tablist / tab / tabpanel` accessibility semantics
  - confirm `channel-double-grid` collapses cleanly by `1024px`
  - confirm build, lint, typecheck, ruff and pytest all pass
- Frontend-4 checks before closing:
  - confirm the same 3 channel pages remain mock-only
  - confirm copy feedback does not leak across tab or scenario changes
  - confirm local copy feedback can auto-clear after a short delay
  - confirm mini tabs support keyboard navigation
  - confirm channel action buttons stack cleanly below `820px`
  - confirm long path / note / title content does not break narrow layouts
  - confirm build, lint, typecheck, ruff and pytest all pass
- Frontend-1 Hardening checks before closing:
  - confirm no extra page is added under `apps/research-pulse-web/src/pages`
  - confirm mock mode still works without backend tokens
  - confirm `draft / preview / not_sent` stay explicit in visible copy
  - run:
    - `cd apps/research-pulse-web && npm run build`
    - `cd apps/research-pulse-web && npm run lint`
    - `cd apps/research-pulse-web && npm run typecheck`
    - `.venv/bin/python -m ruff check .`
    - `.venv/bin/python -m pytest`

## Desktop shell
- Install desktop dependencies:
  - `make desktop-install`
- Run the desktop shell:
  - `make desktop-dev`
- Run desktop lint + typecheck:
  - `make desktop-lint`
- Run desktop tests:
  - `make desktop-test`
- Build the desktop web frontend:
  - `make desktop-build-web`

## Subscription editor web shell
- Install web-shell dependencies:
  - `make subscription-editor-install`
- Run the web shell:
  - `make subscription-editor-dev`
- Run web-shell lint + typecheck:
  - `make subscription-editor-lint`
- Run web-shell tests:
  - `make subscription-editor-test`
- Build the web shell:
  - `make subscription-editor-build`

The shell lives under `apps/subscription-editor-web` and uses only:
- `GET /subscription-editor/bootstrap`
- `GET /subscription-editor/contract`
- `POST /subscription-editor/settings/preview`
- `PATCH /subscription-editor/settings`

The shell is not a mini-program build and does not introduce new auth. It consumes short-lived handoff grants only.

## Result share web shell
- Install share-shell dependencies:
  - `make result-share-install`
- Run the share shell:
  - `make result-share-dev`
- Run share-shell lint + typecheck:
  - `make result-share-lint`
- Run share-shell tests:
  - `make result-share-test`
- Build the share shell:
  - `make result-share-build`

The shell lives under `apps/result-share-web` and uses only:
- `GET /result-shares/{share_token}/bootstrap`
- `GET /result-shares/{share_token}/content`
- `GET /share-aliases/{alias}/bootstrap`
- `GET /share-aliases/{alias}/content`
- `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
- `POST /subscription-self-service/result-shares/{share_token}/collect`
- `GET /subscription-self-service/share-aliases/{alias}/collect-preview`
- `POST /subscription-self-service/share-aliases/{alias}/collect`
- `GET /subscription-self-service/workspace-result-collections`

The shell is public/token-based for share rendering and self-service-token-assisted for collect-preview/collect. It keeps both tokens in memory only and does not introduce login, editing, or source-file sharing.
Backend-only analytics reserve may now also observe those public share routes for:
- `bootstrap_view`
- `content_view`
- `redirect`
- `invite_handoff_redirect`
- `collect_handoff_redirect`
No browser tracker or third-party analytics script is added in this phase.
Admin-only aggregate reads now also reuse those persisted records for:
- `GET /admin/group-workspace-conversion-overview`
- `GET /admin/group-workspaces/{workspace_id}/conversion-overview`
- `GET /admin/group-workspace-conversion-drilldown`
- `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown`
- `GET /admin/result-share-grants/{grant_id}/conversion-drilldown`
- `GET /admin/result-share-aliases/{alias_id}/conversion-drilldown`
- direct share/collect attribution where persisted links exist
- workspace-level invite aggregates without claiming strict per-share causality
- daily buckets, recent safe rows, and top workspace/share-grant lists now live in the drilldown reserve
- per-share grant and alias drilldown now stays backend-only in this phase so a later admin shell can consume it without changing public share behavior
The internal `apps/group-workspace-admin-web` shell now also renders those aggregates as:
- a global conversion overview panel
- a workspace conversion overview panel inside workspace detail
- a global conversion drilldown panel with daily buckets, top entities, and recent safe rows
- a workspace conversion drilldown panel with recent activity plus active grant snapshots
- explicit attribution-scope notes from the backend read model
`workspace_board` share pages now also render a manual invite/join handoff summary:
- the page stays read-only
- joining still requires a separate invite token
- claim still stays in the separate invite/self-service flow
- when invite handoff redirect support is configured, the shell may show an `Open invite entry` CTA that points to a backend redirect boundary instead of the raw invite entry URL
`workspace_board` share pages may now also render a separate result-collect handoff summary:
- the page still cannot collect directly
- collecting papers still requires a separate digest or paper share token
- collect still stays in the separate result-share/self-service flow

## Group workspace admin web shell
- Install workspace-admin dependencies:
  - `make workspace-admin-install`
- Run the workspace-admin shell:
  - `make workspace-admin-dev`
- Run workspace-admin lint + typecheck:
  - `make workspace-admin-lint`
- Run workspace-admin tests:
  - `make workspace-admin-test`
- Build the workspace-admin shell:
  - `make workspace-admin-build`

The shell lives under `apps/group-workspace-admin-web` and uses:
- `GET /admin/group-workspaces`
- `POST /admin/group-workspaces`
- `GET /admin/group-workspaces/{workspace_id}`
- `PATCH /admin/group-workspaces/{workspace_id}`
- `GET /admin/group-workspaces/{workspace_id}/board`
- `POST /admin/group-workspaces/{workspace_id}/members`
- `DELETE /admin/group-workspaces/{workspace_id}/members/{member_id}`
- `POST /admin/group-workspaces/{workspace_id}/papers`
- `DELETE /admin/group-workspaces/{workspace_id}/papers/{paper_id}`
- `GET /admin/result-share-grants`
- `POST /admin/result-share-grants`
- `POST /admin/result-share-grants/{grant_id}/revoke`
- `GET /admin/result-share-aliases`
- `POST /admin/result-share-aliases`
- `GET /admin/result-share-aliases/{alias_id}`
- `POST /admin/result-share-aliases/{alias_id}/revoke`
- plus existing `GET /users` and `GET /papers` reads as internal lookup sources
- plus read-only conversion dashboards over:
  - `GET /admin/group-workspace-conversion-overview`
  - `GET /admin/group-workspace-conversion-drilldown`
  - `GET /admin/group-workspaces/{workspace_id}/conversion-overview`
  - `GET /admin/group-workspaces/{workspace_id}/conversion-drilldown`
- plus compact read-only filter controls for:
  - `date_from`
  - `date_to`
  - `share_kind`
  - `access_mode`
  - `event_type`
  - `outcome`
  - `limit` on drilldown recent/top sections only
- plus backend-only per-share drilldown reserve routes for future admin UI work:
- plus backend-only per-share drilldown reserve routes now consumed by the same shell:
  - `GET /admin/result-share-grants/{grant_id}/conversion-drilldown`
  - `GET /admin/result-share-aliases/{alias_id}/conversion-drilldown`

The shell now also includes a minimal read-only per-share dashboard:
- open a grant drilldown from the existing workspace share-grant list when practical
- open an alias drilldown from alias rows returned by a grant drilldown
- manual `grant_id` / `alias_id` launcher fields for operator lookup when needed
- a dedicated per-share filter bar for `date_from`, `date_to`, `access_mode`, `event_type`, `outcome`, and `limit`
- direct collect linkage stays visible only on grant drilldown; alias drilldown stays access-path scoped

The same shell now also includes a minimal read-only result-share registry:
- `GET /admin/result-share-grants`
- `GET /admin/result-share-aliases`
- safe global share-grant rows with linked alias counts
- safe global alias rows with linked grant hints
- quick-open actions that reuse the existing per-share drilldown panel instead of adding new write flows
- stronger registry filters for share kind, status, workspace, and linked grant
- stable frontend sort controls for `created_at`, `last_used_at`, `expires_at`, `share_kind`, and `status`
- applied filter/sort chips plus filtered zero-result explanations
- grant-to-alias quick filters and alias-to-underlying-grant quick-open actions
- local-only saved views that persist safe registry filter/sort state in browser storage only
- optional local preset extension that also carries safe per-share drilldown `date_from`, `date_to`, `access_mode`, `event_type`, `outcome`, and `limit`
- local-only preset JSON export/import with schema-version validation, unsafe-field rejection, preview-before-apply, and merge/replace scope handling
- local-only preset diagnostics and recovery, including corrupted-storage checks, validation-only dry-run preview, last-good backup snapshots, and scope-safe reset actions
- local-only preset activity history with safe action summaries, recent operations, and clear-audit controls for this browser only
- local-only preset workspace organization with pinned grant/alias presets, recent preset snippets, storage-health summary, stale pin cleanup, and organization-only reset controls
- local-only preset workspace JSON export/import for browser-local organization state only, with stale-pin preview, merge/replace handling, and workspace-only backup restore
- a deterministic local preset workspace health score with breakdown cards, findings, and recommended local actions over integrity, stale pins, backups, audit history, and workspace import/export state
- local threshold preferences for that health score, including threshold draft validation, before/after preview, reset-to-defaults, and browser-local storage only
- local JSON and Markdown health report export for that health score, with safe validation, threshold-source summary, diagnostics recap, findings/recommendations summary, and explicit safety exclusions
- local clipboard health-report summaries for score, findings, recommendations, compact Markdown, and compact JSON, with copy validation and safe local audit events only
- no admin bearer token, raw share token, or raw alias is stored in those presets
- the health score is browser-local hygiene only, not backend health, security scoring, or compliance scoring

The shell is internal/admin-only, keeps bearer tokens in memory only, and does not introduce end-user login or source-file sharing. Filter controls narrow overview/drilldown reads only and do not change attribution semantics.

This admin preset/report track is frozen:
- keep the completed code
- fix blockers only
- do not plan new feature phases in this area

## User workbench admin web shell
- Install user-workbench dependencies:
  - `make user-workbench-install`
- Run the user-workbench shell:
  - `make user-workbench-dev`
- Run user-workbench lint + typecheck:
  - `make user-workbench-lint`
- Run user-workbench tests:
  - `make user-workbench-test`
- Build the user-workbench shell:
  - `make user-workbench-build`

The shell lives under `apps/user-workbench-admin-web` and uses:
- `GET /admin/user-workbench/users`
- `GET /admin/user-workbench/users/{user_id}`
- `GET /admin/user-workbench/papers`
- `GET /admin/user-workbench/papers/{paper_id}`
- `GET /admin/user-workbench/watch-profiles`

The shell is internal/admin-only, keeps bearer tokens in memory only, and stays strictly read-only.

## Group workspace invite web shell
- Install invite-shell dependencies:
  - `make workspace-invite-install`
- Run the invite shell:
  - `make workspace-invite-dev`
- Run invite-shell lint + typecheck:
  - `make workspace-invite-lint`
- Run invite-shell tests:
  - `make workspace-invite-test`
- Build the invite shell:
  - `make workspace-invite-build`

The shell lives under `apps/group-workspace-invite-web` and uses only:
- `GET /workspace-invites/{invite_token}/bootstrap`
- `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
- `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
- `GET /subscription-self-service/workspace-memberships`

The shell is public + self-service-token-assisted, keeps invite/self-service tokens in memory only, and does not introduce end-user login, editing, or source-file sharing.
After membership is claimed or confirmed, the same shell may also show a manual result-collect handoff summary:
- joining does not automatically collect digest or paper shares
- collecting shared results still requires a separate result-share token
- result collect still stays in the existing self-service collect flow

## Group workspace and result sharing
- Admin-managed workspace routes:
  - `GET /admin/group-workspaces`
  - `POST /admin/group-workspaces`
  - `GET /admin/group-workspaces/{workspace_id}`
  - `PATCH /admin/group-workspaces/{workspace_id}`
  - `POST /admin/group-workspaces/{workspace_id}/members`
  - `DELETE /admin/group-workspaces/{workspace_id}/members/{member_id}`
  - `POST /admin/group-workspaces/{workspace_id}/papers`
  - `DELETE /admin/group-workspaces/{workspace_id}/papers/{paper_id}`
  - `GET /admin/group-workspaces/{workspace_id}/board`
- Admin-managed result share routes:
  - `GET /admin/result-share-grants`
  - `POST /admin/result-share-grants`
  - `POST /admin/result-share-grants/{grant_id}/revoke`
  - `GET /admin/result-share-grants/{grant_id}/conversion-drilldown`
  - `GET /admin/result-share-aliases/{alias_id}/conversion-drilldown`
- Admin-managed workspace invite routes:
  - `GET /admin/group-workspace-invite-grants`
  - `POST /admin/group-workspace-invite-grants`
  - `GET /admin/group-workspace-invite-grants/{grant_id}`
  - `POST /admin/group-workspace-invite-grants/{grant_id}/revoke`
  - `GET /admin/group-workspace-invite-claims`
- Public read-only share routes:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`
  - `GET /result-shares/{share_token}/invite-handoff`
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - `GET /share-aliases/{alias}/invite-handoff`
  - optional `GET /s/{alias}` redirect boundary
- Self-service result collect routes:
  - `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - `POST /subscription-self-service/result-shares/{share_token}/collect`
  - `GET /subscription-self-service/share-aliases/{alias}/collect-preview`
  - `POST /subscription-self-service/share-aliases/{alias}/collect`
  - `GET /subscription-self-service/workspace-result-collections`
- Public invite bootstrap route:
  - `GET /workspace-invites/{invite_token}/bootstrap`
- Self-service invite routes:
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`

The browser shell for that invite/join boundary now also supports:
- `/invite/<token>` path parsing when practical
- `?invite_token=` and `#invite_token=` fallbacks
- optional `?self_service_token=` and `#self_service_token=` local-dev fallbacks
- in-memory token handling only

This phase shares structured results only. It explicitly excludes PDFs, source files, local attachment paths, and local note contents.
Result collect now also stays inside that same structured-only boundary:
- only `digest_issue` and `paper_snapshot` are collectable
- collection adds `PaperProfile` objects to eligible workspaces only
- `workspace_board` remains non-collectable in v1
- source files, PDFs, local attachments, and local notes are still excluded
`workspace_board` shares now also carry a read-only `workspace_invite_handoff_reserve` summary:
- it is informational only
- it may include an invite shell entry URL hint
- it may include a redirect-backed `invite_handoff_url`
- it does not make the share page claim-capable
`workspace_board` shares may now also carry a read-only `result_collect_handoff_reserve` summary:
- it is informational only
- it may include a result-share shell entry URL hint
- it may include a redirect-backed `collect_handoff_url`
- it does not make the current board share collect-capable
Invite-facing responses now may also carry a read-only `result_collect_handoff_reserve` summary:
- it is informational only
- it may include a result-share shell entry URL hint
- it does not make the invite page collect-capable
The browser shell for that boundary now uses:
- `/share/<token>` path parsing when practical
- `/share-alias/<alias>` path parsing when practical
- `?share_token=` and `#share_token=` local-dev fallbacks
- `?share_alias=` and `#share_alias=` local-dev fallbacks
- optional `?self_service_token=` and `#self_service_token=` local-dev fallbacks
- in-memory token handling only
- backend-only analytics reserve admin reads through:
  - `GET /admin/result-share-analytics/summary`
  - `GET /admin/result-share-analytics/events`
- `workspace_board` browser pages may now also show an `Open result collect entry` CTA that targets a backend redirect boundary instead of the raw result-share shell entry URL

Desktop sync in this phase uses:
- `GET /sync/me`
- `POST /sync/push`
- `GET /sync/feed`
- `POST /sync/ack`

The desktop shell does not use admin login. It uses admin-issued device tokens, keeps the token on the Rust side, and persists local mutations into a SQLite outbox before attempting sync.

Desktop can now also emit lightweight `work_activity.record` mutations for local-only actions such as attachment import, note create/save, and review-note generation. These mutations carry summary metadata only and never upload local file or note contents.

Desktop Settings can now also edit synced `SubscriptionPolicy` delivery-control fields through the same mutation outbox. The Settings hint panel is local-only and does not call admin-only delivery-control preview or dispatch endpoints.

Mini read-only routes now also expose:
- `GET /mini/bootstrap`
- `GET /mini/today`
- `GET /mini/digest-issues/{digest_issue_id}`
- `GET /mini/subscription-reserve`

Mini routes stay read-only and require mini-read grant auth only.
`/mini/subscription-reserve` now also includes a read-only `binding_handoff_reserve` summary and still exposes no write/update affordance.
`/mini/subscription-reserve` now also includes a read-only `editor_handoff_reserve` summary plus two mini-protected handoff endpoints:
- `POST /mini/subscription-reserve/editor-handoff`
- `GET /mini/subscription-reserve/editor-handoff-status`

These mini endpoints only mint or inspect a short-lived editor handoff token. They do not make mini grants directly writable.
The new browser/webview-friendly shell in `apps/subscription-editor-web` is the intended local/manual consumer of that handoff token in this phase.
`/mini/subscription-reserve` now also includes a read-only `workspace_invite_reserve` summary that explains:
- mini grant still cannot claim workspace membership directly
- a separate self-service grant is required
- workspace invite claim remains self-service-only in this phase
`/mini/subscription-reserve` now also includes a read-only `workspace_collect_reserve` summary that explains:
- mini grant still cannot collect shared results into a workspace directly
- a separate self-service grant is required
- collect remains limited to `digest_issue` and `paper_snapshot` in this phase

## Pulse scoring knobs
- Defaults live in application settings and `.env.example`
- Per-user overrides can be applied through `SubscriptionPolicy.policy["pulse"]`
- See `docs/pulse_scoring.md` for the exact pipeline and supported knobs

## Scheduler knobs
- Daily auto-scheduling only applies to enabled `SubscriptionPolicy` rows with `frequency = daily`
- Supported policy JSON keys:
  - `schedule.timezone`
  - `schedule.send_hour_local`
  - `schedule.send_minute_local`
- If `schedule` is omitted, the service falls back to app-level defaults
- Event policies stay manual in v1

## Auth and admin boundary
- `UserProfile` remains a business entity and is not used for login.
- Human admins authenticate through `/auth/login` and receive:
  - a short-lived JWT access token
  - a server-revocable refresh token
- Internal service callers use `APP_INTERNAL_SERVICE_TOKEN`.
- Role matrix:
  - `viewer`: read-only business endpoints and pulse preview
  - `operator`: business writes, pulse run, scheduler tick, replay, and requeue
  - `super_admin`: operator permissions plus admin-account management and audit-log access
- `GET /health/live` stays public.
- `GET /health/ready` and `/ops/*` require operator/super_admin or the internal service token.

## Bootstrap flow
- Create or update the initial super admin:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!'`
- Optional display name:
  - `make bootstrap-admin EMAIL=admin@example.com PASSWORD='ChangeMe123!' DISPLAY_NAME='Ops Admin'`
- After bootstrap, obtain tokens from `/auth/login` before using protected business or admin routes.

## Database notes
- Production target is PostgreSQL.
- Tests use SQLite through `APP_DATABASE_URL`.
- Alembic migrations are the source of truth for schema evolution.

## Delivery adapter notes
- Console adapter is the safe default for local verification.
- Webhook adapter is the only network-shaped outbound adapter in current runtime flows.
- Legacy `dingtalk` and `wechat` enum values remain only for compatibility with old rows and are rejected for new policy writes.
- Future communication work should target:
  - official-account digest publishing
  - mini-program lightweight client access through sync

## Sync foundation
- Device tokens are created under `/admin/client-devices`.
- Device tokens can only access `/sync/*`.
- Incremental sync flow in v1:
  - `GET /sync/feed`
  - `POST /sync/ack`
  - `POST /sync/push`
- Sync defaults live in `.env.example`:
  - `APP_SYNC_DEVICE_TOKEN_TTL_DAYS`
  - `APP_SYNC_FEED_DEFAULT_LIMIT`
  - `APP_SYNC_FEED_MAX_LIMIT`
  - `APP_SYNC_PUSH_MAX_BATCH_SIZE`
- Conflict handling in v1 is last-write-wins for supported patch operations.
- `POST /sync/push` now also accepts `work_activity.record` for lightweight desktop activity capture.

## Desktop shell
- The desktop shell lives under `apps/desktop`.
- Tauri commands exposed to the frontend include:
  - `appBootstrap`
  - `connectDevice`
  - `disconnectDevice`
  - `clearLocalCache`
  - `queuePaperPatch`
  - `queueProgressEventCreate`
  - `queueSubscriptionPolicyPatch`
  - `syncNow`
  - `getSyncStatus`
  - `getTodayOverview`
  - `listPapers`
  - `getPaperDetail`
  - `listSubscriptionPolicies`
  - `getDeliveryControlSettings`
  - `getDeliveryControlLocalHint`
  - `listPendingMutations`
  - `listReviewRounds`
  - `createReviewRound`
  - `updateReviewRound`
  - `listReviewComments`
  - `addReviewComment`
  - `updateReviewComment`
  - `deleteReviewComment`
  - `generateReviewerMatrixNote`
  - `generateResponseLetterNote`
  - `getReviewRoundDetail`
- Local cache tables:
  - `sync_state`
  - `paper_cache`
  - `progress_event_cache`
  - `signal_snapshot_cache`
  - `subscription_policy_cache`
  - `digest_issue_cache`
  - `sync_event_cache`
  - `mutation_outbox`
  - `workspace_settings`
  - `paper_workspace_cache`
  - `paper_attachment_cache`
  - `paper_note_cache`
  - `paper_review_round_cache`
  - `review_comment_item_cache`
- Desktop sync now runs:
  - push queued mutations
  - pull feed pages
  - apply events
  - ack only after successful apply
- Desktop local actions now also queue `work_activity.record` for:
  - attachment import
  - note create
  - note save
  - review round create
  - reviewer-matrix note generation
  - response-letter note generation
- `progress_percentage` in desktop list/detail views is the same derived heuristic used by the mini read model, not a persisted workflow truth field.
- Desktop local workspace in v1:
  - choose a workspace root from Settings
  - ensure a deterministic paper workspace from Paper Detail
  - import attachments as managed local copies only
  - refresh attachment status when files disappear from disk
- Desktop local notes/templates in v1:
  - create markdown notes under `papers/<paper_id>/notes/`
  - create from built-in templates or as blank notes
  - save note content to disk from the Paper Detail editor
  - refresh note metadata when files are missing or changed outside the app
- Desktop local review matrix in v1:
  - create local review rounds per paper
  - store ordered reviewer comments with manual dispositions and response summaries
  - generate local `reviewer_matrix` and `response_letter` markdown notes from structured rows
  - update linked generated notes in place when regenerating the same round
- Desktop delivery-control settings in v1:
  - read cached `SubscriptionPolicy` rows through `getDeliveryControlSettings`
  - edit quiet-control fields from Settings
  - queue `subscription_policy.patch` mutations through the existing sync writeback path
  - show a local-only hint panel from `getDeliveryControlLocalHint`
- Desktop Today structured digest rendering in v1:
  - prefer synced `section_order`, `sections`, `quick_stats`, `focus_card`, and `publication_preview`
  - fall back to legacy `highlights` / `items` deterministically when structured fields are absent
  - stay read-only and avoid admin-only orchestration or dispatch APIs
- Changing or clearing the workspace root does not move or delete existing managed files.
- `clearLocalCache` and `disconnectDevice` do not delete managed workspace files, local note files, or generated review notes.

## Mini editor handoff reserve
- `SubscriptionEditorHandoffGrant` is a dedicated short-lived bearer token for `/subscription-editor/*`.
- Handoff grant routes:
  - `GET /subscription-editor/bootstrap`
  - `GET /subscription-editor/contract`
  - `POST /subscription-editor/settings/preview`
  - `PATCH /subscription-editor/settings`
- Handoff grant auth is separate from:
  - mini read grant auth
  - self-service grant auth
  - admin auth
- Mini read grant auth still cannot call `/subscription-editor/*`.
- Self-service grant auth still cannot call `/mini/*`.
- The editor web shell now consumes the handoff token directly and keeps it in memory only.

## Official-account digest reserve
- WeChat identity binding can now be created or reused through explicit admin paths or through official-account OAuth completion tied to a valid handshake session.
- Mini still stays read-only and does not implement its own OAuth/login flow.
- New admin endpoints:
  - `GET /admin/wechat-bindings`
  - `POST /admin/wechat-bindings`
  - `PATCH /admin/wechat-bindings/{binding_id}`
  - `GET /admin/digest-issues`
  - `GET /admin/digest-issues/{digest_issue_id}`
  - `POST /admin/digest-issues/build/{user_id}`
  - `POST /admin/digest-issues/orchestrate/{user_id}`
  - `GET /admin/digest-issues/{digest_issue_id}/daily-preview`
  - `POST /admin/digest-issues/{digest_issue_id}/prepare-publication`
  - `GET /admin/digest-publication-jobs`
- `PulseDigestIssue` is built from already selected `PulseCard` rows only.
- Daily digest orchestration now reshapes selected cards into a fixed section model:
  - `today_focus`
  - `yesterday_recap`
  - `signal_updates`
  - `related_papers`
  - `other_updates`
- Conservative orchestration caps come from:
  - `APP_DIGEST_SIGNAL_UPDATES_MAX_ITEMS`
  - `APP_DIGEST_RELATED_PAPERS_MAX_ITEMS`
  - `APP_DIGEST_OTHER_UPDATES_MAX_ITEMS`
- `APP_DIGEST_AUTO_PREPARE_OFFICIAL_ACCOUNT=true` only prepares publication jobs after orchestration; it does not dispatch sends.
- `APP_DIGEST_AUTO_DISPATCH_OFFICIAL_ACCOUNT=true` adds one issue-level dispatch step after orchestration only when the provider boundary allows it.
- `APP_DIGEST_AUTO_DISPATCH_REQUIRE_REAL_MODE=true` keeps auto-dispatch off in `dry_run`.
- `APP_DIGEST_DISPATCH_PREPARE_IF_MISSING=true` allows issue-level dispatch to prepare missing official-account jobs first.
- Official-account user-side delivery control now also reuses `SubscriptionPolicy`:
  - `quiet_hours` stays in `SubscriptionPolicy.quiet_hours`
  - supported `policy` keys are:
    - `timezone`
    - `allowed_weekdays`
    - `muted_until`
    - `minimum_selected_cards`
    - `skip_if_no_today_focus`
  - weekday numbering is `0 = Monday` through `6 = Sunday`
  - delivery control is evaluated before issue-level dispatch and is exposed separately from provider readiness through:
    - `GET /admin/digest-issues/{digest_issue_id}/delivery-control-preview`
    - `GET /admin/digest-delivery-decisions`
- User-side self-service reserve now adds a separate auth boundary on top of those same policy fields:
  - `GET /admin/subscription-self-service-grants`
  - `POST /admin/subscription-self-service-grants`
  - `POST /admin/subscription-self-service-grants/{grant_id}/revoke`
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
- Self-service grant tokens are valid only on `/subscription-self-service/*` and cannot access `/admin/*`, `/ops/*`, `/sync/*`, `/mini/*`, or business CRUD routes.
- Mini grant tokens remain valid only on `/mini/*` and cannot access `/subscription-self-service/*`.
- Self-service patching preserves unknown existing `SubscriptionPolicy.policy` keys while allowing only the supported safe subset to change.
- Preview-before-save now reuses the same normalization and validation path as save, but returns an authoritative preview without persisting draft state.
- Publication preparation is stub-only:
  - jobs move to `prepared`
  - no real external send occurs
- Future WeChat work remains:
  - official-account digest publishing
  - mini-program read-only landing with structured Today and read-only subscription reserve

## Mini-program read-only reserve
- Mini access is modeled as a separate read-only auth boundary.
- Operators and super admins can create preview grants under:
  - `GET /admin/mini-read-grants`
  - `POST /admin/mini-read-grants`
  - `POST /admin/mini-read-grants/{grant_id}/revoke`
- Mini grant tokens can only access:
  - `GET /mini/bootstrap`
  - `GET /mini/today`
  - `GET /mini/digest-issues/{digest_issue_id}`
  - `GET /mini/subscription-reserve`
  - `GET /mini/papers`
  - `GET /mini/papers/{paper_id}`
- Mini defaults live in `.env.example`:
  - `APP_MINI_READ_GRANT_DEFAULT_TTL_HOURS`
  - `APP_MINI_PAPERS_DEFAULT_LIMIT`
  - `APP_MINI_PAPERS_MAX_LIMIT`
- `progress_percentage` is a derived UI/read-model heuristic from `PaperProfile.type`, not a persisted workflow truth field.
- Preview grants can point at:
  - a user overview
  - a digest landing
  - a paper-detail landing
- `/mini/subscription-reserve` now also includes a read-only `self_service_entry` handoff summary that explains:
  - mini remains read-only
  - a separate self-service grant is required for edits
  - editor contract and preview APIs exist for future clients
- No real mini-program auth, session exchange, or frontend code exists in v1.

## Official-account provider boundary
- Official-account dispatch now has an explicit provider mode:
  - `disabled`
  - `dry_run`
  - `real`
- New provider settings live in `.env.example`:
  - `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE`
  - `APP_OFFICIAL_ACCOUNT_TRANSPORT_KIND`
  - `APP_WECHAT_OFFICIAL_APP_ID`
  - `APP_WECHAT_OFFICIAL_APP_SECRET`
  - `APP_WECHAT_OFFICIAL_DIGEST_TEMPLATE_ID`
  - `APP_WECHAT_OFFICIAL_CALLBACK_TOKEN`
  - `APP_WECHAT_OFFICIAL_CALLBACK_AES_KEY`
  - `APP_OFFICIAL_ACCOUNT_CALLBACK_ENABLED`
  - `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED`
  - `APP_OFFICIAL_ACCOUNT_ACCESS_TOKEN_REFRESH_SKEW_SECONDS`
  - `APP_OFFICIAL_ACCOUNT_HTTP_CONNECT_TIMEOUT_SECONDS`
  - `APP_OFFICIAL_ACCOUNT_HTTP_READ_TIMEOUT_SECONDS`
  - `APP_OFFICIAL_ACCOUNT_MAX_RETRIES`
  - `APP_OFFICIAL_ACCOUNT_TEMPLATE_FIELD_MAPPING_JSON`
  - `APP_OFFICIAL_ACCOUNT_DEFAULT_MINI_PROGRAM_APP_ID`
  - `APP_OFFICIAL_ACCOUNT_DEFAULT_ARTICLE_BASE_URL`
  - `APP_OFFICIAL_ACCOUNT_DISPATCH_TIMEOUT_SECONDS`
- Admin inspection and dispatch endpoints:
  - `GET /admin/digest-issues/{digest_issue_id}/dispatch-preview`
  - `POST /admin/digest-issues/{digest_issue_id}/dispatch`
  - `POST /admin/digest-publication-jobs/{publication_job_id}/dispatch`
  - `GET /admin/digest-publication-attempts`
  - `GET /admin/digest-dispatch-runs`
  - `GET /admin/digest-dispatch-runs/{dispatch_run_id}`
  - `GET /admin/official-account/provider-status`
  - `POST /admin/official-account/provider-token/refresh`
  - `GET /admin/official-account/callback-events`
- Provider ingress endpoints:
  - `GET /integrations/wechat/official-account/callback`
  - `POST /integrations/wechat/official-account/callback`
- `dry_run` dispatch creates preview attempts and never performs a live send.
- `real` dispatch is still opt-in and requires:
  - `APP_OFFICIAL_ACCOUNT_PROVIDER_MODE=real`
  - `APP_OFFICIAL_ACCOUNT_REAL_SEND_ENABLED=true`
  - configured app id, app secret, and digest template id
- Real mode uses a client-credential access-token flow with Redis-preferred caching and in-memory fallback for local/test.

## Pulse input layer
- New backend entities:
  - `WorkActivityEvent`
  - `ResearchWatchProfile`
  - `ExternalRetrievalPlan`
- New read/management endpoints:
  - `GET /work-activity-events`
  - `GET /research-watch-profiles`
  - `POST /research-watch-profiles`
  - `PATCH /research-watch-profiles/{profile_id}`
  - `DELETE /research-watch-profiles/{profile_id}`
  - `POST /research-watch-profiles/bootstrap/{paper_id}`
  - `GET /pulse/input-preview/{user_id}`
  - `GET /external-retrieval/input-preview/{user_id}`
  - `GET /external-retrieval/plans`
  - `POST /external-retrieval/plans/build/{user_id}`
- Cloud-side service actions auto-record work activity for:
  - `paper.patch`
  - `progress_event.create`
  - `subscription_policy.patch`
- Desktop-local attachment/note/review actions contribute through `work_activity.record`.
- `POST /pulse/preview/{user_id}` and `POST /pulse/run/{user_id}` now also accept an optional `timezone` query parameter for deterministic yesterday-summary inspection.
- `today_suggestion` is now a first-party pulse card type generated only from internal paper/progress/signal state.
- `yesterday_summary` is now a first-party pulse card type generated only from the previous local day of `WorkActivityEvent`.
- `related_paper` is now a first-party pulse card type generated only from persisted normalized `ExternalRetrievedRecord` rows.
- External retrieval now has a separate planning and execution boundary:
  - `ExternalRetrievalPlan` persists source-specific plan inputs
  - `ExternalRetrievalRun` persists one fetch attempt per plan
  - `ExternalRetrievedRecord` stores normalized official-source records
  - `GET /pulse/input-preview/{user_id}` includes compact planning and latest-run summaries
  - pulse preview/run consume normalized records only and never execute retrieval inline
- No AI summarization is enabled in this phase.
- Summary timezone resolution order is:
  - explicit request timezone
  - first enabled daily policy timezone
  - app default timezone

### Today-suggestion scoring knobs
- `APP_PULSE_WEIGHT_TODAY_SUGGESTION`
- `APP_PULSE_TODAY_SUGGESTION_STALE_DAYS_THRESHOLD`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_PRIORITY`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_HAS_NEXT_ACTION`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_REVISION_STAGE`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_STALE_PROGRESS`
- `APP_PULSE_MODIFIER_TODAY_SUGGESTION_BLOCKER_PRESENT`

### Yesterday-summary scoring knobs
- `APP_PULSE_WEIGHT_YESTERDAY_SUMMARY`
- `APP_PULSE_YESTERDAY_SUMMARY_MIN_EVENTS`
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_ACTIVITY_DIVERSITY`
- `APP_PULSE_MODIFIER_YESTERDAY_SUMMARY_MULTI_PAPER`

### Related-paper scoring knobs
- `APP_PULSE_WEIGHT_RELATED_PAPER`
- `APP_PULSE_MODIFIER_RELATED_PAPER_HAS_DOI`
- `APP_PULSE_MODIFIER_RELATED_PAPER_MATCH_REASON_COUNT`
- `APP_PULSE_MODIFIER_RELATED_PAPER_LINKED_PAPER`
- `APP_PULSE_MODIFIER_RELATED_PAPER_RECENT_RETRIEVAL`
- `APP_PULSE_RELATED_PAPER_LOOKBACK_DAYS`
- `APP_PULSE_RELATED_PAPER_MAX_CANDIDATES_PER_RUN`
- `APP_PULSE_RELATED_PAPER_DEDUPE_DAYS`

### External retrieval planning knobs
- `APP_EXTERNAL_RETRIEVAL_MODE`
- `APP_EXTERNAL_RETRIEVAL_ENABLED_SOURCES`
- `APP_EXTERNAL_RETRIEVAL_MAX_PLANS_PER_USER`
- `APP_EXTERNAL_RETRIEVAL_MAX_KEYWORDS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_MAX_TOPICS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_LOOKBACK_DAYS_FOR_ACTIVITY_CONTEXT`
- `APP_EXTERNAL_RETRIEVAL_HTTP_CONNECT_TIMEOUT_SECONDS`
- `APP_EXTERNAL_RETRIEVAL_HTTP_READ_TIMEOUT_SECONDS`
- `APP_EXTERNAL_RETRIEVAL_MAX_RESULTS_PER_PLAN`
- `APP_EXTERNAL_RETRIEVAL_EXECUTION_DEDUPE_MINUTES`
- `APP_EXTERNAL_RETRIEVAL_OPENALEX_API_KEY`
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_MAILTO`
- `APP_EXTERNAL_RETRIEVAL_CROSSREF_USER_AGENT_APP_NAME`
- `plan_only` keeps execution blocked while preserving plan preview/build.
- `execute` enables official-source fetches for persisted plans.
- Unknown callback identities are stored for review and do not auto-create bindings.
- Official-account binding handshake reserve settings:
  - `APP_OFFICIAL_ACCOUNT_BINDING_HANDSHAKE_TTL_MINUTES`
  - `APP_OFFICIAL_ACCOUNT_BINDING_RECONCILIATION_LOOKBACK_HOURS`
  - `APP_OFFICIAL_ACCOUNT_BINDING_REQUIRE_SIGNATURE_VALID`
- `APP_OFFICIAL_ACCOUNT_BINDING_DEFAULT_DIGEST_ENABLED`
- `APP_OFFICIAL_ACCOUNT_OAUTH_ENABLED`
- `APP_OFFICIAL_ACCOUNT_OAUTH_DEFAULT_SCOPE`
- `APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PUBLIC_BASE_URL`
- `APP_OFFICIAL_ACCOUNT_OAUTH_CALLBACK_PATH`
- `APP_OFFICIAL_ACCOUNT_OAUTH_FETCH_USERINFO_WHEN_SCOPE_USERINFO`
- `APP_OFFICIAL_ACCOUNT_OAUTH_LANG`
- `APP_OFFICIAL_ACCOUNT_OAUTH_SUCCESS_REDIRECT_URL`
- `APP_OFFICIAL_ACCOUNT_OAUTH_FAILURE_REDIRECT_URL`

### Official-account binding handshake reserve endpoints
- Admin:
  - `GET /admin/official-account-binding-handshake-sessions`
  - `POST /admin/official-account-binding-handshake-sessions`
  - `GET /admin/official-account-binding-handshake-sessions/{session_id}`
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/cancel`
  - `GET /admin/official-account-binding-reconciliation/candidates`
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/claim`
- Self-service:
  - `GET /subscription-self-service/wechat-binding-reserve/bootstrap`
  - `POST /subscription-self-service/wechat-binding-reserve/session`
  - `GET /subscription-self-service/wechat-binding-reserve/session`
  - `POST /subscription-self-service/wechat-binding-reserve/session/cancel`
  - `POST /subscription-self-service/wechat-binding-reserve/oauth-start`
  - `GET /subscription-self-service/wechat-binding-reserve/oauth-status`
- OAuth completion is now added on top of the reserve:
  - `POST /admin/official-account-binding-handshake-sessions/{session_id}/oauth-authorize-url`
  - `GET /admin/official-account/oauth-status`
  - `GET /integrations/wechat/official-account/oauth/callback`
- This still does not create a generic app login/session system or mini-side write path.

### External retrieval endpoints
- `GET /external-retrieval/input-preview/{user_id}`
- `GET /external-retrieval/provider-status`
- `GET /external-retrieval/plans`
- `POST /external-retrieval/plans/build/{user_id}`
- `POST /external-retrieval/plans/execute/{plan_id}`
- `GET /external-retrieval/runs`
- `GET /external-retrieval/runs/{run_id}`
- `GET /external-retrieval/results`
- Retrieval execution remains separate from pulse preview/run:
  - no inline retrieval during pulse generation
  - no related-news cards yet
  - no AI ranking
  - no scraping

## Ops endpoints
- `GET /health/live`: lightweight process liveness
- `GET /health/ready`: database readiness and component details, protected by operator/admin or internal service auth
- `GET /ops/metrics`: Prometheus-style counters
- `GET /ops/heartbeats`: scheduler and worker heartbeat rows
- `GET /ops/pulse-jobs`: pulse job lifecycle inspection
- `GET /ops/delivery-jobs`: delivery job inspection
- `GET /ops/delivery-attempts`: one row per delivery send attempt
- `POST /ops/scheduler/tick`: local manual scheduler trigger
- `POST /ops/delivery-jobs/{delivery_job_id}/requeue`: requeue failed or dead-letter delivery work
- `POST /ops/pulse-jobs/{pulse_job_id}/replay`: create or reuse a replay job

## Observability notes
- Worker heartbeats are stored in the database for local and low-volume deployments.
- Delivery attempts are append-only and tied to the existing outbox flow.
- Metrics are process-local counters in v1; treat them as lightweight local observability, not a distributed metrics backend.
- Replay and requeue are idempotent where practical and will not silently duplicate active work.

## Next extension points
- Replace `DummyModelProvider` with a real provider adapter.
- Expand deterministic facts into richer signal scoring and portfolio context.
- Add richer official-account digest sending strategy on top of persisted pulse, digest, and issue-dispatch data.
- Add real mini-program auth and landing handoff on top of the read-only reserve.
- Add customer-facing auth separately from `AdminAccount`.
- Add SSO/OIDC only after the internal admin boundary stabilizes.
