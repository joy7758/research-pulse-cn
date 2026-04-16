# Mini Frontend Migration Reserve v1

## Why A Shared Editor Core Is Added Before A True Mini Native UI
- The repository already has:
  - short-lived `SubscriptionEditorHandoffGrant`
  - `/subscription-editor/*` APIs
  - a thin browser/WebView shell in `apps/subscription-editor-web`
- This phase extracts the reusable editor logic into a host-agnostic core so future mini/native work does not have to reimplement:
  - bootstrap shaping
  - contract interpretation
  - draft serialization
  - preview/save response shaping
- The backend contract stays authoritative.

## Package Layout
- `packages/subscription-editor-core`
  - pure TypeScript only
  - no React
  - no DOM or browser globals
- `apps/subscription-editor-web`
  - now acts as the reference host implementation
  - keeps URL fragment handling, token entry, and fetch transport

## Pure Core Vs Host Adapter Split
- Core package owns:
  - editor domain/read types mirroring backend responses
  - form-state shaping from bootstrap payloads
  - weekday normalization and serialization helpers
  - patch payload builder
  - preview/save display shaping
  - host/runtime metadata types
  - host adapter and transport interfaces
- Host implementations own:
  - token ingestion
  - visible URL cleanup
  - API base resolution
  - concrete transport calls
  - UI rendering

## Web Shell As Reference Host
- The current web shell remains a thin client over:
  - `@research-pulse/subscription-editor-core`
  - a web-specific host adapter
  - a web-specific transport client
- The browser shell still:
  - accepts manual token paste or `#handoff_token=...`
  - keeps the token in memory only
  - calls only `/subscription-editor/*`

## Future Mini Native Migration Path
- Future mini/native work can reuse the core package for:
  - handoff-token launch input shaping
  - bootstrap to draft state
  - preview/save result shaping
  - field/section contract interpretation
- A future mini host only needs to add:
  - native token injection
  - native transport adapter
  - native UI rendering

## Current Non-Goals
- real mini-program native UI
- new delivery channels
- generic app login/session system
- desktop UI work
- browser token persistence

## Future Work
- real mini/native editor UI on top of the shared core
- richer runtime adapters for WebView and native bridge handoff
- optional shared presentation primitives if they become justified
- deeper mobile UX polish after the native host exists
