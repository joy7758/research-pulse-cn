# Desktop Tauri Skeleton v1

## Why Tauri Was Chosen
- The desktop shell needs a small, fast, cross-platform container for a read-only research workbench.
- Tauri 2 keeps the desktop app isolated from the Python backend while reusing the system web renderer instead of bundling Chromium.
- This phase is intentionally a shell, not a bundled local backend.

## Repository Layout
- `apps/desktop`: React + TypeScript + Vite frontend plus `src-tauri` Rust host
- `apps/desktop/src`: desktop UI shell and typed Tauri command wrappers
- `apps/desktop/src-tauri`: Rust commands, local cache, secret boundary, and pull-sync client
- `src/research_pulse_cn`: cloud/backend application

## Desktop Connection Model
- The desktop shell authenticates with the existing device-token sync boundary.
- Connection bootstrap requires:
  - backend base URL
  - device token
  - optional local display label
- The desktop validates the token with `GET /sync/me`.
- It persists:
  - connection metadata in local SQLite
  - the device token behind a Rust-side secret store abstraction
- It does not reuse admin login and does not store the device token in `localStorage` or `sessionStorage`.

## Local Cache Model
- Local cache uses SQLite from the Rust side under the app data directory.
- Cache tables in v1:
  - `sync_state`
  - `paper_cache`
  - `progress_event_cache`
  - `signal_snapshot_cache`
  - `digest_issue_cache`
  - `sync_event_cache`
- The cache is read-focused and intentionally small.
- `clearLocalCache` preserves the connection boundary but resets local event/apply state so the next sync can rebuild from the feed.

## Pull-Sync Flow
1. Desktop reads the local sync cursor from `sync_state`.
2. Rust-side HTTP calls `GET /sync/feed` after the local cursor.
3. Events are applied sequentially to local SQLite.
4. `POST /sync/ack` is sent only after the local page applies successfully.
5. The loop repeats until `has_more=false`.

## Read Models
- `SyncStatusRead`
- `UserConnectionRead`
- `TodayOverviewRead`
- `TodaySectionRead`
- `TodayQuickStatsRead`
- `TodayFocusCardRead`
- `TodayPublicationPreviewRead`
- `PaperListItemRead`
- `PaperDetailRead`

The frontend consumes typed Tauri commands instead of embedding HTTP or sync logic directly into React components.

`TodayOverviewRead` now prefers synced structured digest content when available:
- `section_order`
- `sections`
- `quick_stats`
- `focus_card`
- `publication_preview`

If older cached digests only expose `highlights` / `items`, desktop derives a conservative fallback Today layout instead of failing.

## Derived Progress Percentage Heuristic
- Desktop views expose `progress_percentage` as a derived read-model heuristic only.
- Mapping:
  - `published -> 100`
  - `revision -> 80`
  - `under_review -> 65`
  - `in_prep -> 35`
  - `paused -> 0`
- Workflow truth still lives in paper type, stage, and event history.

## Local Developer Commands
- `make desktop-install`
- `make desktop-dev`
- `make desktop-lint`
- `make desktop-test`
- `make desktop-build-web`

Direct app-local commands:
- `cd apps/desktop && npm install`
- `cd apps/desktop && npm run tauri dev`
- `cd apps/desktop && npm run lint`
- `cd apps/desktop && npm run typecheck`
- `cd apps/desktop && npm run test`
- `cd apps/desktop && cargo test --manifest-path src-tauri/Cargo.toml`

## Current Non-Goals
- no desktop write-back sync beyond the limited Phase 14 mutation set
- no cloud-synced paper/file workspace
- no PDF import or annotation
- no embedded backend or bundled server mode
- no auto-update, signing, packaging, or release hardening
- no Electron

## Future Work
- richer desktop write-back sync beyond paper patch, progress events, and subscription policy patch
- stronger secret storage beyond the local dev file-backed abstraction
- local paper/file workspace and annotation features beyond the v1 managed-copy layer
- packaging, signing, and distribution workflows
- richer desktop UX and offline conflict handling
