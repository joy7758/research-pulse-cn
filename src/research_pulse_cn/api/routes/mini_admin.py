"""Admin routes for mini read grant preview and lifecycle management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_mini_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, MiniReadGrantStatus, MiniReadGrantType
from research_pulse_cn.schemas.mini import (
    MiniReadGrantCreateRequest,
    MiniReadGrantIssueResponse,
    MiniReadGrantRead,
    MiniReadGrantRevokeResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.mini import MiniService

router = APIRouter(prefix="/admin", tags=["admin"])
MiniServiceDep = Annotated[MiniService, Depends(get_mini_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("/mini-read-grants", response_model=list[MiniReadGrantRead])
def list_mini_read_grants(
    _actor: OperatorDep,
    service: MiniServiceDep,
    user_id: UserIdQuery = None,
    status: Annotated[MiniReadGrantStatus | None, Query()] = None,
    grant_type: Annotated[MiniReadGrantType | None, Query()] = None,
    digest_issue_id: Annotated[UUID | None, Query()] = None,
    binding_id: Annotated[UUID | None, Query()] = None,
) -> list[MiniReadGrantRead]:
    return [
        MiniReadGrantRead(**service.serialize_grant(grant))
        for grant in service.list_grants(
            user_id=user_id,
            status=status,
            grant_type=grant_type,
            digest_issue_id=digest_issue_id,
            binding_id=binding_id,
        )
    ]


@router.post(
    "/mini-read-grants",
    response_model=MiniReadGrantIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_mini_read_grant(
    payload: MiniReadGrantCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: MiniServiceDep,
    audit_service: AuditServiceDep,
) -> MiniReadGrantIssueResponse:
    grant, issued = service.create_grant(
        user_id=payload.user_id,
        binding_id=payload.binding_id,
        digest_issue_id=payload.digest_issue_id,
        grant_type=payload.grant_type,
        scope=payload.scope,
        expires_at=payload.expires_at,
        created_by_admin_id=actor.actor_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="mini_read_grant.create",
        resource_type="mini_read_grant",
        resource_id=str(grant.id),
        status_code=201,
        metadata={
            "user_id": str(grant.user_id),
            "grant_type": grant.grant_type.value,
            "digest_issue_id": (
                None if grant.digest_issue_id is None else str(grant.digest_issue_id)
            ),
            "binding_id": None if grant.binding_id is None else str(grant.binding_id),
        },
    )
    return MiniReadGrantIssueResponse(
        grant=MiniReadGrantRead(**service.serialize_grant(grant)),
        plain_text_token=issued.plain_text_token,
        preview_landing_path=issued.preview_landing_path,
        expires_at=issued.expires_at,
    )


@router.post("/mini-read-grants/{grant_id}/revoke", response_model=MiniReadGrantRevokeResponse)
def revoke_mini_read_grant(
    grant_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: MiniServiceDep,
    audit_service: AuditServiceDep,
) -> MiniReadGrantRevokeResponse:
    grant = service.revoke_grant(grant_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="mini_read_grant.revoke",
        resource_type="mini_read_grant",
        resource_id=str(grant.id),
        status_code=200,
    )
    return MiniReadGrantRevokeResponse(
        grant=MiniReadGrantRead(**service.serialize_grant(grant)),
        revoked_at=grant.updated_at,
    )
