"""Admin management routes."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.dependencies import get_admin_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, AuditActorType
from research_pulse_cn.schemas.admin import (
    AdminAccountCreate,
    AdminAccountRead,
    AdminAccountUpdate,
    AdminPasswordSetRequest,
    AuditLogRead,
)
from research_pulse_cn.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]
SuperAdminDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.SUPER_ADMIN))]
SinceHoursQuery = Annotated[int | None, Query(ge=1, le=24 * 30)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


@router.get("/admin-accounts", response_model=list[AdminAccountRead])
def list_admin_accounts(
    _actor: SuperAdminDep,
    service: AdminServiceDep,
) -> list[AdminAccountRead]:
    return service.list_accounts()


@router.post(
    "/admin-accounts",
    response_model=AdminAccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_account(
    payload: AdminAccountCreate,
    request: Request,
    actor: SuperAdminDep,
    service: AdminServiceDep,
) -> AdminAccountRead:
    return service.create_account(
        email=str(payload.email),
        password=payload.password,
        role=payload.role,
        display_name=payload.display_name,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
        actor=actor,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )


@router.patch("/admin-accounts/{admin_account_id}", response_model=AdminAccountRead)
def update_admin_account(
    admin_account_id: UUID,
    payload: AdminAccountUpdate,
    request: Request,
    actor: SuperAdminDep,
    service: AdminServiceDep,
) -> AdminAccountRead:
    return service.update_account(
        admin_account_id,
        role=payload.role,
        display_name=payload.display_name,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
        actor=actor,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )


@router.post(
    "/admin-accounts/{admin_account_id}/set-password",
    response_model=AdminAccountRead,
)
def set_admin_password(
    admin_account_id: UUID,
    payload: AdminPasswordSetRequest,
    request: Request,
    actor: SuperAdminDep,
    service: AdminServiceDep,
) -> AdminAccountRead:
    return service.set_password(
        admin_account_id,
        password=payload.password,
        must_change_password=payload.must_change_password,
        actor=actor,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
    )


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    _actor: SuperAdminDep,
    service: AdminServiceDep,
    actor_type: Annotated[AuditActorType | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    since_hours: SinceHoursQuery = None,
    limit: LimitQuery = 100,
) -> list[AuditLogRead]:
    since = None if since_hours is None else utcnow() - timedelta(hours=since_hours)
    return service.list_audit_logs(
        actor_type=actor_type,
        action=action,
        since=since,
        limit=limit,
    )
