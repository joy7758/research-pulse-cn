# Mini Self-Service Editor UI v1

## Why A Thin Web Shell Is Added Before A True Mini-Program UI
- The repository already has:
  - mini read-only reserve
  - self-service editor reserve
  - short-lived handoff grants for `/subscription-editor/*`
- This phase adds a browser/webview-friendly shell so the handoff flow becomes visible and manually testable without building a real mini-program UI yet.
- The shell stays thin and keeps all authoritative policy logic on the backend.

## Token Bootstrap Flow
- The shell supports two startup paths:
  - manual token paste
  - URL fragment ingestion via `#handoff_token=...`
- When the token comes from the URL fragment:
  - the shell moves it into in-memory React state
  - clears it from the visible URL immediately
- The shell also supports:
  - `VITE_SUBSCRIPTION_EDITOR_API_BASE_URL`
  - manual API base override in the connect form

## In-Memory Handoff Token Handling
- The handoff token is never written to:
  - `localStorage`
  - `sessionStorage`
  - cookies
- The shell keeps the bearer token only in memory for the current tab/session.
- Clearing the shell state drops the token immediately.

## Supported Editor Fields
- The shell renders the current safe editable subset only:
  - `enabled`
  - `quiet_hours`
  - `timezone`
  - `allowed_weekdays`
  - `muted_until`
  - `minimum_selected_cards`
  - `skip_if_no_today_focus`
- It also shows read-only context from bootstrap/contract:
  - safe user summary
  - safe official-account binding summary
  - current handoff-grant summary
  - self-service grant status
  - latest digest summary
  - authoritative preview support

## Preview Save Flow
- `GET /subscription-editor/bootstrap` validates the handoff token and loads the current draft.
- `GET /subscription-editor/contract` provides section/field metadata.
- `POST /subscription-editor/settings/preview` returns:
  - normalized draft
  - changed fields
  - structured validation issues
  - authoritative preview
- `PATCH /subscription-editor/settings?include_preview=true` returns:
  - saved server state
  - changed fields
  - post-save authoritative preview
- The shell keeps local edits separate from:
  - the last previewed draft
  - the last saved server state

## Error States
- missing token
- invalid or expired handoff grant
- network/bootstrap failure
- preview validation errors
- save failure
- missing digest context for authoritative preview

## Current Non-Goals
- real mini-program native UI
- new delivery channels
- generic user login/session system
- desktop UI work
- campaign or broadcast behavior

## Future Work
- real mini-program editing UI
- tighter handoff UX from mini reserve
- richer field rendering and section UX
- better continuity beyond one in-memory browser tab if later justified
