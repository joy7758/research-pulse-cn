# Workspace Board Invite Handoff Summary v1

## Why A Manual Handoff Summary Is Added Before A True Integrated Join Flow
- `workspace_board` share pages already expose safe read-only workspace summaries.
- The repository already has a separate invite/join reserve and a separate invite web shell.
- This phase adds only a handoff summary so a shared board can point a viewer toward the correct membership flow without mixing share tokens and invite tokens.

## Workspace-Board Share Remains Read-Only
- The share page still cannot:
  - claim membership
  - accept an invite token
  - mutate workspace membership
- It continues to show only safe workspace/member/paper summaries.

## Invite/Join Stays A Separate Flow
- Membership still requires:
  - a separate invite token
  - the existing self-service claim boundary
- The share page only explains that boundary.
- The share page does not reuse collect or share auth as invite auth.

## Handoff Summary Fields
- `supported`
- `share_kind`
- `separate_invite_token_required`
- `invite_bootstrap_available`
- `self_service_claim_supported`
- `direct_claim_via_share_page`
- `source_files_included`
- `invite_shell_entry_url`
- `notes`

## Optional Invite Entry URL Hint
- The handoff summary may include an `invite_shell_entry_url`.
- This value points only to the invite shell entry page.
- It never includes an invite token or a self-service token.
- If not configured, it remains `null`.

## Current Non-Goals
- direct join from `workspace_board` share pages
- source-file or PDF sharing
- local attachment or note sharing
- mini or desktop invite UX
- generic login/session behavior

## Future Work
- integrated invite token handoff into share pages
- self-service guided join flow from `workspace_board`
- later workspace onboarding UX
- still no source-file sharing by default
