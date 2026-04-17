# Desktop Today Structured Pulse v1

## Why The Desktop Today Page Is Being Upgraded After Digest Orchestration Exists
- The cloud already produces deterministic sectioned daily digests through `PulseDigestIssue.content_payload`.
- Desktop should consume that authoritative digest shape instead of re-deriving pulse structure locally.
- This keeps the Today page read-only, synced, and aligned with the official-account daily digest model.

## Structured Today Read Models
- Desktop Today now prefers structured read models built from synced digest cache data:
  - `TodaySectionKindRead`
  - `TodaySectionItemRead`
  - `TodaySectionRead`
  - `TodayQuickStatsRead`
  - `TodayFocusCardRead`
  - `TodayPublicationPreviewRead`
- `TodayOverviewRead` now carries:
  - `is_structured`
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
  - `fallback_mode`
- Existing `highlights` remain for backward compatibility.

## Preferred Structured Path Vs Fallback Path
- Preferred path:
  - use synced `content_payload.section_order`
  - use synced `content_payload.sections`
  - use synced `content_payload.quick_stats`
  - use synced `content_payload.focus_card`
  - use synced `content_payload.publication_preview`
- Fallback path:
  - if structured fields are absent, desktop derives a minimal sectioned view from legacy `highlights` and `items`
  - fallback remains deterministic and conservative
  - desktop does not invent new pulse cards or call orchestration/admin endpoints

## Supported Section Kinds
- Stable section order is:
  1. `today_focus`
  2. `yesterday_recap`
  3. `signal_updates`
  4. `related_papers`
  5. `other_updates`
- Empty sections are hidden in the UI.
- `sourcePaperId = null` remains valid, especially for `yesterday_summary`.

## Quick Stats And Publication Preview Handling
- When available, desktop shows compact digest stats:
  - selected card count
  - related paper count
  - signal update count
  - touched paper count
- Desktop also shows compact publication-preview metadata when present:
  - digest title
  - digest subtitle
  - primary CTA text/path
- This remains informational only and does not expose send actions.

## Current Non-Goals
- no direct desktop calls to admin-only orchestration or dispatch endpoints
- no local pulse-card computation
- no editable digest actions
- no external retrieval execution from desktop
- no AI summarization or ranking

## Future Work
- richer desktop interaction on related-paper items
- open related papers in browser/app from the Today page
- section collapse state or personal layout preferences
- browsing previous digest issues when issue history is exposed cleanly
