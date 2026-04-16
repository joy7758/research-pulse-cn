# Group Workspace Invite Web Shell v1

## Why A Public Invite Web Shell Is Added After Invite Join Reserve Exists
- Phase 41 already established the backend-only invite and join reserve boundary.
- This phase turns that reserve into a browser-openable growth loop without introducing a generic end-user login system.
- The shell stays thin:
  - public bootstrap is read-only
  - claim still goes through the existing self-service grant boundary
  - no source files or local attachments are exposed

## Public Bootstrap Flow
- The shell lives under `apps/group-workspace-invite-web`.
- It accepts invite tokens from:
  - `/invite/<token>` pathnames
  - `?invite_token=...` query fallback
  - `#invite_token=...` fragment fallback
  - manual paste
- Query and fragment invite hints are moved into in-memory state and immediately cleared from the visible URL.
- The shell then calls:
  - `GET /workspace-invites/{invite_token}/bootstrap`

## Self-Service Token-Assisted Claim Flow
- The shell optionally accepts an existing self-service token from:
  - manual paste
  - `?self_service_token=...` local-dev query fallback
  - `#self_service_token=...` local-dev fragment fallback
- Query and fragment self-service hints are also moved into in-memory state and immediately cleared from the visible URL.
- With both invite token and self-service token in memory, the shell calls:
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
- The shell never persists either token in localStorage, sessionStorage, or cookies.

## Safe Data Model
- The shell renders only safe summaries already exposed by the backend:
  - workspace name, slug, description, status
  - invite role, status, remaining claim hint, expiration
  - claim-preview reason codes
  - current-membership summary
  - current workspace-membership list
  - informational result-collect handoff summary after claimed / already_member / membership states
- The shell excludes:
  - token hashes
  - plaintext tokens after initial entry
  - source files
  - local filesystem paths
  - local attachments or notes
  - `openid`
  - `unionid`
  - provider secrets

## Current Non-Goals
- direct result collect inside the invite shell
- source-file or PDF sharing
- local attachment sharing
- note-file or note-content sharing
- real-time collaboration
- desktop or mini invite UI
- generic end-user login/session system
- campaign or referral behavior

## Future Work
- richer public invite/join UI polish
- integrated invite-to-collect UX
- mini handoff into invite claim flow
- richer membership onboarding
- later workspace board handoff if justified
