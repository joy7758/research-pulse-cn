"""Public read-only routes for structured result share grants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

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


@router.get("/share-aliases/{alias}/bootstrap", response_model=ShareGrantBootstrapRead)
def get_result_share_alias_bootstrap(
    alias: str,
    service: WorkspaceServiceDep,
) -> ShareGrantBootstrapRead:
    alias_context = service.authenticate_share_alias(alias)
    grant = service.get_result_share_grant(alias_context.grant_id)
    grant_context = service._result_share_grant_context(grant)
    return ShareGrantBootstrapRead(**service.share_bootstrap(grant_context))


@router.get("/share-aliases/{alias}/content", response_model=SharedResultContentRead)
def get_result_share_alias_content(
    alias: str,
    service: WorkspaceServiceDep,
) -> SharedResultContentRead:
    alias_context = service.authenticate_share_alias(alias)
    grant = service.get_result_share_grant(alias_context.grant_id)
    grant_context = service._result_share_grant_context(grant)
    return service.share_content(grant_context)


@router.get("/s/{alias}", response_class=RedirectResponse)
def redirect_result_share_alias(
    alias: str,
    service: WorkspaceServiceDep,
) -> RedirectResponse:
    return RedirectResponse(url=service.build_share_alias_redirect_url(alias), status_code=307)
