"""Public read-only routes for structured result share grants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from research_pulse_cn.api.dependencies import get_group_workspace_service
from research_pulse_cn.schemas.group_workspace import (
    SharedResultContentRead,
    ShareGrantBootstrapRead,
)
from research_pulse_cn.services.group_workspace import GroupWorkspaceService

router = APIRouter(tags=["result-shares"])
WorkspaceServiceDep = Annotated[GroupWorkspaceService, Depends(get_group_workspace_service)]


@router.get("/result-shares/{share_token}/bootstrap", response_model=ShareGrantBootstrapRead)
def get_result_share_bootstrap(
    share_token: str,
    service: WorkspaceServiceDep,
) -> ShareGrantBootstrapRead:
    grant = service.authenticate_share_token(share_token)
    return ShareGrantBootstrapRead(**service.share_bootstrap(grant))


@router.get("/result-shares/{share_token}/content", response_model=SharedResultContentRead)
def get_result_share_content(
    share_token: str,
    service: WorkspaceServiceDep,
) -> SharedResultContentRead:
    grant = service.authenticate_share_token(share_token)
    return service.share_content(grant)
