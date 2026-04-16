# Result Share Collect Web Shell v1

## Why Collect Is Added To The Share Web Shell After Collect Reserve Exists
- The repository already had a thin public share shell under `apps/result-share-web`.
- Phase 43 added the backend reserve for self-service result collection into eligible group workspaces.
- This phase connects the existing shell to that reserve so a browser user can move from read-only share inspection to an explicit collect action without introducing source-file sharing or a generic login system.

## Public Bootstrap Vs Self-Service Collect Boundary
- Public share bootstrap and share content remain token-based and read-only.
- The same shell may reach those read-only models through an additive alias layer when a raw share token should not be exposed in the browser URL.
- Collect-preview, collect, and workspace-result-collection history require a separate self-service grant token.
- Both the raw share token or alias and the self-service token stay in memory only.
- Query and fragment token or alias hints are moved into memory and cleared from the visible URL immediately.
- Backend-only analytics reserve may observe bootstrap/content/redirect access, but it does not change collect request semantics or add browser trackers.

## Supported Collectable Share Kinds
- `paper_snapshot`
  - exposes exactly one collectable paper summary
  - may be collected without explicit paper selection
- `digest_issue`
  - may expose multiple collectable paper summaries
  - preserves backend first-seen deduped order
  - requires explicit `paper_ids` selection when more than one collectable paper exists
- `workspace_board`
  - remains non-collectable in v1
  - is shown as an informational state only
  - may also show a separate invite/join handoff summary
  - may also show a separate result-collect handoff summary that points back to the existing digest/paper share shell entry

## Multiple-Paper Digest Handling
- The shell shows all collectable digest papers in stable preview order.
- The workspace selector is shown alongside the paper list.
- When the preview reports multiple collectable papers, the collect button stays blocked until at least one paper is selected.
- After collect, the shell refreshes:
  - collect preview
  - workspace-result-collections history
- The current public share view stays visible throughout the collect flow.

## Safety Exclusions
- no source-file or PDF sharing
- no local attachment sharing
- no local note-file or note-content sharing
- no browser token persistence
- no generic end-user login/session system
- no desktop or mini UI additions in this phase

## Current Non-Goals
- auto-collect or autosubmit behavior
- richer workspace onboarding or curation UX
- mini collect actions
- real-time collaboration
- AI-assisted collect ranking or copy generation

## Future Work
- mini handoff into collect flow
- richer workspace selection UX
- later explicit source-file opt-in flows
- workspace curation improvements after collect
