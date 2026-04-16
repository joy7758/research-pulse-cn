# Workspace Board Result Collect Handoff Summary v1

## Why A Manual Handoff Summary Is Added Before A True Integrated Board-To-Collect Flow
- `workspace_board` share pages already expose safe read-only workspace summaries.
- The repository already has a separate result collect reserve and a separate result-share collect shell.
- This phase adds only a handoff summary so a shared board can point a viewer toward the correct collect flow without mixing board share tokens with digest or paper share tokens.

## Workspace-Board Share Remains Read-Only
- The share page still cannot:
  - collect papers directly
  - accept a digest or paper share token
  - mutate workspace membership or workspace papers
- It continues to show only safe workspace/member/paper summaries.

## Result Collect Stays A Separate Flow
- Collecting papers into the workspace still requires:
  - a separate `digest_issue` or `paper_snapshot` share token
  - the existing self-service collect boundary
- The board page only explains that boundary.
- The board page does not reuse invite auth or current board-share auth as collect auth.

## Handoff Summary Fields
- `supported`
- `share_kind`
- `separate_result_share_token_required`
- `result_share_bootstrap_available`
- `collect_supported_via_self_service`
- `direct_collect_via_current_share`
- `source_files_included`
- `supported_share_kinds`
- `result_share_shell_entry_url`
- `notes`

## Optional Result-Share Shell Entry URL Hint
- The handoff summary may include a `result_share_shell_entry_url`.
- This value points only to the existing result-share shell entry page.
- It never includes a share token or a self-service token.
- If not configured, it remains `null`.

## Current Non-Goals
- direct collect from `workspace_board` share pages
- source-file or PDF sharing
- local attachment or note sharing
- mini or desktop collect UX
- generic login/session behavior

## Future Work
- integrated board-to-collect UX
- context handoff from `workspace_board` into collect flow
- mini handoff into result collect
- still no source-file sharing by default
