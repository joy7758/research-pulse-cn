# Group Workspace Invite Join Reserve v1

## Why Invite Join Reserve Is Added After Group Workspace Boundary Exists
- Group workspaces and result sharing already expose structured read-only outcomes.
- The next safe growth step is controlled membership expansion, not raw-file access.
- Invite and join now reuse the existing workspace model plus the existing self-service auth boundary instead of introducing a generic login system.

## GroupWorkspaceInviteGrant Model
- `GroupWorkspaceInviteGrant` is an opaque-token admin-issued invite for one workspace.
- Fields:
  - `id`
  - `workspace_id`
  - `role_to_assign`
  - `token_hash`
  - `status`
  - `display_label`
  - `max_claims`
  - `claim_count`
  - `expires_at`
  - `last_used_at`
  - `issued_by_admin_id`
  - `created_at`
  - `updated_at`
- Statuses in v1:
  - `active`
  - `revoked`
  - `expired`
  - `exhausted`
- Only `editor` and `viewer` are assignable through invites in v1.
- `owner` is intentionally excluded from invite-based assignment.

## GroupWorkspaceInviteClaim Model
- `GroupWorkspaceInviteClaim` records the audited outcome of one user claiming one invite.
- Fields:
  - `id`
  - `invite_grant_id`
  - `workspace_id`
  - `user_id`
  - `membership_id`
  - `role_assigned`
  - `claim_status`
  - `reason_codes`
  - `created_at`
  - `updated_at`
  - `claimed_at`
- Statuses in v1:
  - `claimed`
  - `already_member`
  - `rejected`
- Claims are unique per `invite_grant_id + user_id`.

## Public Bootstrap Vs Self-Service Claim Boundary
- Public bootstrap is read-only and token-based:
  - `GET /workspace-invites/{invite_token}/bootstrap`
- Self-service claim stays behind an existing `SubscriptionSelfServiceGrant`:
  - `GET /subscription-self-service/workspace-invites/{invite_token}/claim-preview`
  - `POST /subscription-self-service/workspace-invites/{invite_token}/claim`
  - `GET /subscription-self-service/workspace-memberships`
- Mini read grants remain informational only:
  - mini can surface reserve hints
  - mini cannot claim membership directly in this phase

## Role Restrictions
- Invite grants may assign only:
  - `editor`
  - `viewer`
- Claim requires:
  - invites enabled
  - a valid active invite
  - an active workspace
  - a current self-service grant
- Deterministic result codes in v1 include:
  - `invites_disabled`
  - `invite_not_found`
  - `invite_revoked`
  - `invite_expired`
  - `invite_exhausted`
  - `workspace_archived`
  - `already_member`
  - `no_self_service_grant`
  - `role_not_assignable`

## Safe Summary Model
- Public bootstrap exposes only:
  - safe invite summary
  - safe workspace summary
  - role-to-assign
  - remaining-claims hint
  - expiration metadata
- Self-service membership reads expose only:
  - `member_id`
  - `workspace_id`
  - `user_id`
  - `role`
  - `joined_at`
  - safe workspace summary
- Invite/join flows exclude:
  - plaintext tokens after creation
  - token hashes
  - local filesystem paths
  - local note contents
  - local attachment paths
  - source-file contents
  - provider secrets
  - `openid`
  - `unionid`

## Current Non-Goals
- source-file or PDF sharing
- local attachment sharing
- note-file or note-content sharing
- real-time collaboration
- mini or desktop invite UI
- generic end-user login/session system
- marketing/referral behavior

## Future Work
- invite/join public UI
- mini self-service join handoff
- multi-use invite administration UX
- later user-managed workspace invites if justified
