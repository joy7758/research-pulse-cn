# Group Workspace Result Sharing v1

## Why Result Sharing Is Added Before Source-File Sharing
- The product needs a safe growth surface that can expose useful outcomes before it exposes raw research assets.
- Structured results are easier to audit, revoke, and keep within existing backend boundaries.
- This phase intentionally shares:
  - digest issues
  - safe paper snapshots
  - safe workspace boards
- This phase intentionally does not share:
  - PDFs
  - local attachments
  - local note contents
  - local reviewer-matrix drafts

## GroupWorkspace Model
- `GroupWorkspace` is an admin-managed shared container for structured research outputs.
- Fields:
  - `id`
  - `slug`
  - `name`
  - `description`
  - `status`
  - `created_by_admin_id`
  - `created_at`
  - `updated_at`
- Statuses in v1:
  - `active`
  - `archived`

## Role Model
- `GroupWorkspaceMember` links one `UserProfile` into one workspace.
- Fields:
  - `id`
  - `workspace_id`
  - `user_id`
  - `role`
  - `joined_at`
  - `created_at`
  - `updated_at`
- Roles in v1:
  - `owner`
  - `editor`
  - `viewer`
- Membership is unique per `workspace_id + user_id`.
- Workspace management remains admin-operated in this phase; there is no user-side membership UI yet.

## Workspace Board Concept
- `GroupWorkspacePaper` includes a paper in one shared workspace without copying files.
- Fields:
  - `id`
  - `workspace_id`
  - `paper_id`
  - `added_by_admin_id`
  - `created_at`
  - `updated_at`
- Inclusion is unique per `workspace_id + paper_id`.
- The read-only workspace board exposes:
  - workspace summary
  - member count
  - paper count
  - safe member summaries
  - safe paper snapshots
  - compact quick stats
- Paper snapshots stay intentionally narrow:
  - `paper_id`
  - `user_id`
  - optional owner name/email in admin board context only
  - `title`
  - `type`
  - `stage`
  - `venue`
  - `priority`
  - `next_action`
  - `blocker`
  - `last_touch_at`
  - heuristic `progress_percentage`
  - optional latest signal summary

## ResultShareGrant Model
- `ResultShareGrant` is an opaque-token read-only grant for structured result sharing.
- Fields:
  - `id`
  - `share_kind`
  - `workspace_id`
  - `digest_issue_id`
  - `paper_id`
  - `token_hash`
  - `status`
  - `display_label`
  - `issued_by_admin_id`
  - `expires_at`
  - `last_used_at`
  - `created_at`
  - `updated_at`
- Only token hashes are stored at rest.
- Plaintext share tokens are returned only once at issuance time.
- Statuses in v1:
  - `active`
  - `revoked`
  - `expired`

## Supported Share Kinds
- `digest_issue`
  - resolves a safe structured digest issue view
  - prefers sectioned digest payloads when present
  - falls back to legacy digest highlights/items when needed
- `paper_snapshot`
  - resolves a safe paper snapshot only
  - excludes local paths, note contents, and attachment data
- `workspace_board`
  - resolves the shared workspace board
  - includes safe member summaries and safe paper snapshots only

## Public Read-Only Share Endpoints
- Public/token routes in v1:
  - `GET /result-shares/{share_token}/bootstrap`
  - `GET /result-shares/{share_token}/content`
- Admin routes in v1:
  - `GET /admin/group-workspaces`
  - `POST /admin/group-workspaces`
  - `GET /admin/group-workspaces/{workspace_id}`
  - `PATCH /admin/group-workspaces/{workspace_id}`
  - `POST /admin/group-workspaces/{workspace_id}/members`
  - `DELETE /admin/group-workspaces/{workspace_id}/members/{member_id}`
  - `POST /admin/group-workspaces/{workspace_id}/papers`
  - `DELETE /admin/group-workspaces/{workspace_id}/papers/{paper_id}`
  - `GET /admin/group-workspaces/{workspace_id}/board`
  - `GET /admin/result-share-grants`
  - `POST /admin/result-share-grants`
  - `POST /admin/result-share-grants/{grant_id}/revoke`
- In this phase, workspace and share management are restricted to `operator` and `super_admin`.
- Share links are sensitive because the token is embedded in the path; treat them as bearer secrets.
- A thin browser shell under `apps/result-share-web` now consumes those public endpoints directly for demo and forwarding use cases while staying strictly read-only.
- A separate internal browser shell under `apps/group-workspace-admin-web` now consumes the admin-managed workspace routes for operator workflows:
  - workspace list/detail
  - member add/remove
  - paper add/remove
  - `workspace_board` share grant create/revoke
- A separate public/browser self-service shell under `apps/group-workspace-invite-web` now consumes invite bootstrap plus membership-claim routes without turning result sharing into a login or file-sharing surface.
- Invite and join now remain a separate reserve boundary:
  - public invite bootstrap is read-only
  - membership claim stays behind `/subscription-self-service/*`
  - invites are not interchangeable with result share grants

## Current Non-Goals
- source-file or PDF sharing
- local attachment sharing
- local note-file or note-content sharing
- review-matrix or response-letter draft sharing
- real-time collaboration
- desktop or mini UI work
- new delivery channels
- generic user login/session system

## Future Work
- user-managed workspace membership
- source-file sharing as explicit opt-in
- richer workspace analytics
- later collaboration features if justified
