"""Authentication routes for admin users."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from research_pulse_cn.api.dependencies import get_auth_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.auth import (
    AdminLoginRequest,
    AdminLogoutRequest,
    AdminRefreshRequest,
    AuthMeResponse,
    AuthTokenPairResponse,
    LogoutResponse,
)
from research_pulse_cn.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
AnyAdminDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]


@router.post("/login", response_model=AuthTokenPairResponse)
def login(
    payload: AdminLoginRequest,
    request: Request,
    service: AuthServiceDep,
) -> AuthTokenPairResponse:
    issued = service.login(
        email=payload.email,
        password=payload.password,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )
    return AuthTokenPairResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        expires_in_seconds=issued.expires_in_seconds,
        admin=issued.admin_account,
    )


@router.post("/refresh", response_model=AuthTokenPairResponse)
def refresh_token(
    payload: AdminRefreshRequest,
    request: Request,
    service: AuthServiceDep,
) -> AuthTokenPairResponse:
    issued = service.refresh(
        refresh_token=payload.refresh_token,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )
    return AuthTokenPairResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        expires_in_seconds=issued.expires_in_seconds,
        admin=issued.admin_account,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    payload: AdminLogoutRequest,
    request: Request,
    actor: AnyAdminDep,
    service: AuthServiceDep,
) -> LogoutResponse:
    status = service.logout(
        actor=actor,
        refresh_token=payload.refresh_token,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )
    return LogoutResponse(status=status)


@router.get("/me", response_model=AuthMeResponse)
def me(actor: AnyAdminDep, service: AuthServiceDep) -> AuthMeResponse:
    admin_account = service.admin_repository.get(actor.actor_id) if actor.actor_id else None
    if admin_account is None:
        raise NotFoundError("authenticated admin account was not found")
    return AuthMeResponse(actor_type=actor.actor_type.value, admin=admin_account)
