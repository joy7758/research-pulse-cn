# Group Workspace Result Collect Reserve v1

## Why Result Collect Reserve Is Added Before Source-File Sharing
- The repository already supports read-only result sharing for `digest_issue`, `paper_snapshot`, and `workspace_board`.
- The next safe step is to collect structured paper objects into a workspace without exposing source files.
- This phase therefore adds a narrow collect reserve before any file-sharing or local-attachment semantics.

## Collectable Share Kinds
- `paper_snapshot`
  - exactly one collectable paper
  - the shared paper snapshot target is the collectable object
- `digest_issue`
  - one or more collectable papers may be derived from the digest payload
  - only items with `source_paper_id` are collectable
  - duplicate papers are deduped by first-seen order
- `workspace_board`
  - not collectable in v1

## Collect-Preview Vs Collect Action
- `GET /subscription-self-service/result-shares/{share_token}/collect-preview`
  - self-service only
  - returns share summary, collectable paper summaries, eligible workspaces, and reason codes
- `POST /subscription-self-service/result-shares/{share_token}/collect`
  - self-service only
  - accepts `workspace_id` and optional `paper_ids`
  - adds selected papers to an eligible workspace without touching source files
- `GET /subscription-self-service/workspace-result-collections`
  - self-service only
  - returns the caller's collect records with safe workspace and paper summaries

## Eligible Workspace Role Rules
- The collecting user is always the self-service grant user.
- Eligible target workspaces are current memberships where:
  - workspace status is `active`
  - role is `owner` or `editor`
- `viewer` membership is not collect-capable in v1.
- Mini grant auth remains informational only and cannot call collect routes.

## GroupWorkspaceResultCollectRecord Model
- `GroupWorkspaceResultCollectRecord` persists one audit-friendly collect outcome per:
  - user
  - workspace
  - share context
  - collected paper
- Fields:
  - `id`
  - `workspace_id`
  - `user_id`
  - `result_share_grant_id`
  - `share_kind`
  - `digest_issue_id`
  - `source_pulse_card_id`
  - `source_paper_id`
  - `collected_paper_id`
  - `idempotency_key`
  - `status`
  - `reason_codes`
  - `created_at`
  - `updated_at`
- Statuses in v1:
  - `collected`
  - `already_present`
  - `rejected`

## Public Bootstrap Collection Reserve Summary
- `GET /result-shares/{share_token}/bootstrap` now includes a compact `collection_reserve` block.
- That block is informational only.
- It tells a public reader:
  - whether the current share kind is collectable
  - whether collection is routed through self-service
  - that source files are not included

## Current Non-Goals
- source-file or PDF sharing
- local attachment sharing
- local note-file or note-content sharing
- workspace board collect/import
- mini collect action
- new channels
- real-time collaboration

## Future Work
- richer collect UI inside share pages
- mini handoff into collect flow
- later source-file sharing as explicit opt-in
- richer workspace curation and review flows

The existing public share shell under `apps/result-share-web` is now the minimal browser consumer of this reserve: it keeps public share reads read-only, adds self-service-token-assisted collect-preview and collect panels, and still excludes source files and local attachments.
