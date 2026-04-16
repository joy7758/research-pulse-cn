# Result Share Web Shell v1

## Why A Public Read-Only Web Shell Is Added After Result-Sharing Boundary Exists
- Phase 37 already established the backend-only boundary for safe structured result sharing.
- This phase turns those opaque share tokens into a browser-openable surface that can be demoed and forwarded.
- The shell stays strictly read-only:
  - no login
  - no editing
  - no source-file access

## Token Bootstrap Flow
- The shell lives under `apps/result-share-web`.
- It accepts share tokens from:
  - `/share/<token>` pathnames
  - `?share_token=...` query fallback
  - `#share_token=...` fragment fallback
  - manual paste
- Query and fragment tokens are moved into in-memory state and immediately cleared from the visible URL.
- The shell then calls:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`

## Read-Only Result Types
- Supported share kinds in v1:
  - `digest_issue`
  - `paper_snapshot`
  - `workspace_board`
- The shell renders only structured read models already exposed by the backend.
- The shell does not derive new business logic or reconstruct hidden data.

## Structured Digest Rendering Vs Fallback Behavior
- `digest_issue` share pages prefer:
  - `section_order`
  - `sections`
  - `quick_stats`
  - `focus_card`
  - `publication_preview`
- If older digest rows only expose legacy compatibility fields, the shell deterministically falls back to:
  - `highlights`
  - `items`
- Fallback sections still render in the stable public order:
  1. `today_focus`
  2. `yesterday_recap`
  3. `signal_updates`
  4. `related_papers`
  5. `other_updates`

## Safety Exclusions
- This shell does not expose:
  - source files or PDFs
  - local attachment paths
  - local note contents
  - local reviewer-matrix drafts
  - openid / unionid
  - provider secrets
- Internal deep links are treated as informational unless they are already safe external URLs in backend payloads.

## Current Non-Goals
- source-file or attachment sharing
- local note-file or note-content sharing
- editing through share pages
- desktop UI or mini UI work
- campaign or referral behavior
- generic user login/session system

## Future Work
- richer public share UX
- optional signed short links
- later source-file sharing as explicit opt-in
- potential workspace invite or handoff flows if justified

The internal admin/operator shell for creating and revoking `workspace_board` shares now lives separately under `apps/group-workspace-admin-web`, so this public shell stays strictly read-only.
Workspace invite bootstrap and self-service claim now also have their own separate thin shell under `apps/group-workspace-invite-web`, so result sharing and membership growth remain distinct browser surfaces.
