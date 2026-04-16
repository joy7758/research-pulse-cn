"""Public read-only routes for structured result share grants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from research_pulse_cn.api.dependencies import get_group_workspace_service
from research_pulse_cn.core.errors import AuthenticationError, ValidationFailedError
from research_pulse_cn.domain.enums import (
    ResultShareHandoffTargetKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
    ResultShareViewOutcome,
)
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
    request: Request,
    service: WorkspaceServiceDep,
) -> ShareGrantBootstrapRead:
    try:
        grant = service.authenticate_share_token(share_token)
        payload = ShareGrantBootstrapRead(
            **service.share_bootstrap(
                grant,
                access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
                access_value=share_token,
            )
        )
    except AuthenticationError:
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
            event_type=ResultShareViewEventType.BOOTSTRAP_VIEW,
            outcome=ResultShareViewOutcome.REJECTED,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            raw_share_token=share_token,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
        event_type=ResultShareViewEventType.BOOTSTRAP_VIEW,
        outcome=ResultShareViewOutcome.RESOLVED,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant,
    )
    return payload


@router.get("/result-shares/{share_token}/content", response_model=SharedResultContentRead)
def get_result_share_content(
    share_token: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> SharedResultContentRead:
    try:
        grant = service.authenticate_share_token(share_token)
        payload = service.share_content(grant)
    except AuthenticationError:
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
            event_type=ResultShareViewEventType.CONTENT_VIEW,
            outcome=ResultShareViewOutcome.REJECTED,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            raw_share_token=share_token,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
        event_type=ResultShareViewEventType.CONTENT_VIEW,
        outcome=ResultShareViewOutcome.RESOLVED,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant,
    )
    return payload


@router.get("/share-aliases/{alias}/bootstrap", response_model=ShareGrantBootstrapRead)
def get_result_share_alias_bootstrap(
    alias: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> ShareGrantBootstrapRead:
    try:
        alias_context = service.authenticate_share_alias(alias)
        grant = service.get_result_share_grant(alias_context.grant_id)
        grant_context = service._result_share_grant_context(grant)
        payload = ShareGrantBootstrapRead(
            **service.share_bootstrap(
                grant_context,
                access_mode=ResultShareViewAccessMode.ALIAS,
                access_value=alias,
            )
        )
    except AuthenticationError:
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.ALIAS,
            event_type=ResultShareViewEventType.BOOTSTRAP_VIEW,
            outcome=ResultShareViewOutcome.REJECTED,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            raw_alias=alias,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.ALIAS,
        event_type=ResultShareViewEventType.BOOTSTRAP_VIEW,
        outcome=ResultShareViewOutcome.RESOLVED,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant_context,
        alias_context=alias_context,
    )
    return payload


@router.get("/share-aliases/{alias}/content", response_model=SharedResultContentRead)
def get_result_share_alias_content(
    alias: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> SharedResultContentRead:
    try:
        alias_context = service.authenticate_share_alias(alias)
        grant = service.get_result_share_grant(alias_context.grant_id)
        grant_context = service._result_share_grant_context(grant)
        payload = service.share_content(grant_context)
    except AuthenticationError:
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.ALIAS,
            event_type=ResultShareViewEventType.CONTENT_VIEW,
            outcome=ResultShareViewOutcome.REJECTED,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            raw_alias=alias,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.ALIAS,
        event_type=ResultShareViewEventType.CONTENT_VIEW,
        outcome=ResultShareViewOutcome.RESOLVED,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant_context,
        alias_context=alias_context,
    )
    return payload


@router.get("/result-shares/{share_token}/invite-handoff", response_class=RedirectResponse)
def redirect_result_share_invite_handoff(
    share_token: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> RedirectResponse:
    grant_context = None
    try:
        grant_context = service.authenticate_share_token(share_token)
        redirect_url = service.build_result_share_invite_handoff_redirect_url(
            share_kind=grant_context.share_kind
        )
    except (AuthenticationError, ValidationFailedError):
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
            event_type=ResultShareViewEventType.INVITE_HANDOFF_REDIRECT,
            outcome=ResultShareViewOutcome.REJECTED,
            handoff_target_kind=ResultShareHandoffTargetKind.GROUP_WORKSPACE_INVITE_ENTRY,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            grant_context=grant_context,
            raw_share_token=share_token,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.SHARE_TOKEN,
        event_type=ResultShareViewEventType.INVITE_HANDOFF_REDIRECT,
        outcome=ResultShareViewOutcome.RESOLVED,
        handoff_target_kind=ResultShareHandoffTargetKind.GROUP_WORKSPACE_INVITE_ENTRY,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant_context,
    )
    return RedirectResponse(url=redirect_url, status_code=307)


@router.get("/share-aliases/{alias}/invite-handoff", response_class=RedirectResponse)
def redirect_result_share_alias_invite_handoff(
    alias: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> RedirectResponse:
    alias_context = None
    grant_context = None
    try:
        alias_context = service.authenticate_share_alias(alias)
        grant = service.get_result_share_grant(alias_context.grant_id)
        grant_context = service._result_share_grant_context(grant)
        redirect_url = service.build_result_share_invite_handoff_redirect_url(
            share_kind=grant_context.share_kind
        )
    except (AuthenticationError, ValidationFailedError):
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.ALIAS,
            event_type=ResultShareViewEventType.INVITE_HANDOFF_REDIRECT,
            outcome=ResultShareViewOutcome.REJECTED,
            handoff_target_kind=ResultShareHandoffTargetKind.GROUP_WORKSPACE_INVITE_ENTRY,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            grant_context=grant_context,
            alias_context=alias_context,
            raw_alias=alias,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.ALIAS,
        event_type=ResultShareViewEventType.INVITE_HANDOFF_REDIRECT,
        outcome=ResultShareViewOutcome.RESOLVED,
        handoff_target_kind=ResultShareHandoffTargetKind.GROUP_WORKSPACE_INVITE_ENTRY,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        grant_context=grant_context,
        alias_context=alias_context,
    )
    return RedirectResponse(url=redirect_url, status_code=307)


@router.get("/s/{alias}", response_class=RedirectResponse)
def redirect_result_share_alias(
    alias: str,
    request: Request,
    service: WorkspaceServiceDep,
) -> RedirectResponse:
    try:
        redirect_url = service.build_share_alias_redirect_url(alias)
    except (AuthenticationError, ValidationFailedError):
        service.safe_record_result_share_view_event(
            access_mode=ResultShareViewAccessMode.ALIAS_REDIRECT,
            event_type=ResultShareViewEventType.REDIRECT,
            outcome=ResultShareViewOutcome.REJECTED,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            client_host=None if request.client is None else request.client.host,
            accept_language=request.headers.get("accept-language"),
            raw_alias=alias,
        )
        raise
    service.safe_record_result_share_view_event(
        access_mode=ResultShareViewAccessMode.ALIAS_REDIRECT,
        event_type=ResultShareViewEventType.REDIRECT,
        outcome=ResultShareViewOutcome.RESOLVED,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
        client_host=None if request.client is None else request.client.host,
        accept_language=request.headers.get("accept-language"),
        raw_alias=alias,
    )
    return RedirectResponse(url=redirect_url, status_code=307)
