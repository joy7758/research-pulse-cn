"""Public read-only bootstrap routes for group workspace invite grants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from research_pulse_cn.api.dependencies import get_group_workspace_service
from research_pulse_cn.schemas.group_workspace import GroupWorkspaceInviteBootstrapRead
from research_pulse_cn.services.group_workspace import GroupWorkspaceService

router = APIRouter(tags=["workspace-invites"])
WorkspaceServiceDep = Annotated[GroupWorkspaceService, Depends(get_group_workspace_service)]


@router.get(
    "/workspace-invites/{invite_token}/bootstrap",
    response_model=GroupWorkspaceInviteBootstrapRead,
)
def get_group_workspace_invite_bootstrap(
    invite_token: str,
    service: WorkspaceServiceDep,
) -> GroupWorkspaceInviteBootstrapRead:
    grant = service.authenticate_invite_token(invite_token)
    return GroupWorkspaceInviteBootstrapRead(**service.invite_bootstrap(grant))
