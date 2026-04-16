# Group Workspace Invite Collect Handoff Summary v1

## Why A Manual Handoff Summary Is Added Before An Integrated Invite-To-Collect Flow
- The repository already has a separate invite/join reserve and a separate result-collect reserve.
- This phase adds only a manual handoff summary after membership-facing states so the browser shell can point users toward the correct next step without mixing invite tokens and share tokens.
- The handoff stays informational and does not turn the invite shell into a collect surface.

## Invite/Join And Result Collect Remain Separate Flows
- Invite/bootstrap/claim still focus only on workspace membership.
- Result collect still requires:
  - a separate result-share token
  - the existing self-service collect boundary
- The invite shell only explains that next step after membership is established or confirmed.

## Handoff Summary Fields
- `supported`
- `separate_result_share_token_required`
- `result_share_bootstrap_available`
- `collect_supported_via_self_service`
- `direct_collect_via_invite_page`
- `source_files_included`
- `supported_share_kinds`
- `result_share_shell_entry_url`
- `notes`

## Optional Result-Share Shell Entry URL Hint
- The handoff summary may include a `result_share_shell_entry_url`.
- This value points only to the result-share shell entry page.
- It never includes a share token or self-service token.
- If not configured, it remains `null`.

## Current Non-Goals
- direct result collect inside the invite shell
- source-file or PDF sharing
- local attachment or note sharing
- mini or desktop collect UX
- generic login/session behavior

## Future Work
- integrated invite-to-collect UX
- share-token handoff from membership success
- mini handoff into result collect
- still no source-file sharing by default
