# Result Share Alias Boundary v1

## Why An Alias Layer Is Added After Result-Share Boundaries Exist
- `ResultShareGrant` already defines the underlying read-only sharing boundary.
- This phase adds a second public access layer so browsers can open shorter opaque aliases without exposing the underlying raw share token.
- Alias resolution stays additive: it does not replace the original grant model, collect rules, or source-of-truth share semantics.

## ResultShareAlias Model
- `ResultShareAlias` stores:
  - `id`
  - `result_share_grant_id`
  - `alias_hash`
  - `alias_prefix`
  - `status`
  - `display_label`
  - `issued_by_admin_id`
  - `expires_at`
  - `last_used_at`
  - `created_at`
  - `updated_at`
- Plaintext aliases are returned only once at issuance time.
- Only alias hashes are stored at rest.
- Multiple aliases over time may point to the same `ResultShareGrant`.

## Admin Issuance And Revocation Flow
- Admin/operator routes:
  - `GET /admin/result-share-aliases`
  - `POST /admin/result-share-aliases`
  - `GET /admin/result-share-aliases/{alias_id}`
  - `POST /admin/result-share-aliases/{alias_id}/revoke`
- Safe admin alias summaries expose:
  - `id`
  - `result_share_grant_id`
  - `share_kind`
  - `status`
  - `display_label`
  - `alias_prefix`
  - `expires_at`
  - `last_used_at`
  - `created_at`
- Raw aliases are not re-exposed after creation.

## Public Alias Bootstrap And Content
- Public alias routes:
  - `GET /share-aliases/{alias}/bootstrap`
  - `GET /share-aliases/{alias}/content`
  - `GET /share-aliases/{alias}/invite-handoff` for allowed `workspace_board` shares only
- Alias resolution returns the same safe read-only bootstrap/content models as the underlying `ResultShareGrant`.
- Alias resolution fails cleanly when:
  - the alias is revoked
  - the alias is expired
  - the underlying share grant is revoked
  - the underlying share grant is expired

## Optional Redirect Boundary
- Optional redirect route:
  - `GET /s/{alias}`
- When enabled, the redirect points browsers to the existing `apps/result-share-web` shell using the alias only.
- The redirect never includes the raw share token.
- When redirect support is disabled or the result-share shell entry URL is not configured, the route fails cleanly.
- Backend-only analytics reserve may also observe alias bootstrap/content/redirect traffic without changing the public alias contract.

## Alias-Scoped Drilldown Reserve
- Admin-only per-alias drilldown now adds:
  - `GET /admin/result-share-aliases/{alias_id}/conversion-drilldown`
- The alias drilldown is read-only and safe:
  - it surfaces alias-scoped access-mode, event-type, and outcome counts
  - it exposes recent safe event rows for that alias only
  - it returns grant-safe summary context without re-exposing a raw token
- Alias drilldown remains intentionally narrower than grant drilldown:
  - it describes access-path behavior for one alias
  - it does not claim direct collect attribution when persisted collect rows are only linked at grant level
  - it does not expose source files, attachments, notes, or raw browser identity data

## Alias Mode In Result-Share-Web
- The existing `apps/result-share-web` shell now accepts aliases from:
  - `/share-alias/<alias>`
  - `?share_alias=...`
  - `#share_alias=...`
  - manual paste
- Raw share token mode remains supported.
- Query and fragment alias hints are moved into in-memory state and cleared from the visible URL immediately.
- Alias mode renders the same safe `digest_issue`, `paper_snapshot`, and `workspace_board` views.
- When the alias resolves to a collectable share kind, the existing self-service collect flow still works through alias-aware endpoints.

## Current Non-Goals
- source-file or PDF sharing
- local attachment sync
- local note-content sharing
- generic user login/session flows
- custom vanity slugs
- AI-generated share copy

## Future Work
- signed short links
- richer alias-vs-token analytics views
- admin per-alias drilldown UI over the existing reserve
- later custom share slugs if ever justified
- still no source-file sharing by default
