"""Admin routes for group workspace invite grants and claim audit views."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_group_workspace_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
)
from research_pulse_cn.schemas.group_workspace import (
    GroupWorkspaceInviteClaimRead,
    GroupWorkspaceInviteGrantCreateRequest,
    GroupWorkspaceInviteGrantIssueResponse,
    GroupWorkspaceInviteGrantRead,
    GroupWorkspaceInviteGrantRevokeResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.group_workspace import GroupWorkspaceService

router = APIRouter(prefix="/admin", tags=["admin"])
WorkspaceServiceDep = Annotated[GroupWorkspaceService, Depends(get_group_workspace_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]


@router.get(
    "/group-workspace-invite-grants",
    response_model=list[GroupWorkspaceInviteGrantRead],
)
def list_group_workspace_invite_grants(
    _actor: ViewerDep,
    service: WorkspaceServiceDep,
    workspace_id: Annotated[UUID | None, Query()] = None,
    status_value: Annotated[GroupWorkspaceInviteGrantStatus | None, Query(alias="status")] = None,
    role_to_assign: Annotated[GroupWorkspaceInviteRole | None, Query()] = None,
) -> list[GroupWorkspaceInviteGrantRead]:
    return [
        GroupWorkspaceInviteGrantRead(**service.serialize_invite_grant(grant))
        for grant in service.list_invite_grants(
            workspace_id=workspace_id,
            status=status_value,
            role_to_assign=role_to_assign,
        )
    ]


@router.post(
    "/group-workspace-invite-grants",
    response_model=GroupWorkspaceInviteGrantIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group_workspace_invite_grant(
    payload: GroupWorkspaceInviteGrantCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceInviteGrantIssueResponse:
    grant, issued = service.create_invite_grant(
        workspace_id=payload.workspace_id,
        role_to_assign=payload.role_to_assign,
        display_label=payload.display_label,
        max_claims=payload.max_claims,
        expires_at=payload.expires_at,
        issued_by_admin_id=actor.actor_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_invite_grant.create",
        resource_type="group_workspace_invite_grant",
        resource_id=str(grant.id),
        status_code=201,
        metadata={
            "workspace_id": str(grant.workspace_id),
            "role_to_assign": grant.role_to_assign.value,
            "status": grant.status.value,
        },
    )
    return GroupWorkspaceInviteGrantIssueResponse(
        grant=GroupWorkspaceInviteGrantRead(**service.serialize_invite_grant(grant)),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
    )


@router.get(
    "/group-workspace-invite-grants/{grant_id}",
    response_model=GroupWorkspaceInviteGrantRead,
)
def get_group_workspace_invite_grant(
    grant_id: UUID,
    _actor: ViewerDep,
    service: WorkspaceServiceDep,
) -> GroupWorkspaceInviteGrantRead:
    return GroupWorkspaceInviteGrantRead(
        **service.serialize_invite_grant(service.get_invite_grant(grant_id))
    )


@router.post(
    "/group-workspace-invite-grants/{grant_id}/revoke",
    response_model=GroupWorkspaceInviteGrantRevokeResponse,
)
def revoke_group_workspace_invite_grant(
    grant_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceInviteGrantRevokeResponse:
    grant = service.revoke_invite_grant(grant_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_invite_grant.revoke",
        resource_type="group_workspace_invite_grant",
        resource_id=str(grant.id),
        status_code=200,
        metadata={"workspace_id": str(grant.workspace_id)},
    )
    return GroupWorkspaceInviteGrantRevokeResponse(
        grant=GroupWorkspaceInviteGrantRead(**service.serialize_invite_grant(grant)),
        revoked_at=service.now_provider(),
    )


@router.get(
    "/group-workspace-invite-claims",
    response_model=list[GroupWorkspaceInviteClaimRead],
)
def list_group_workspace_invite_claims(
    _actor: ViewerDep,
    service: WorkspaceServiceDep,
    workspace_id: Annotated[UUID | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    claim_status: Annotated[GroupWorkspaceInviteClaimStatus | None, Query()] = None,
) -> list[GroupWorkspaceInviteClaimRead]:
    return [
        GroupWorkspaceInviteClaimRead(**service.serialize_invite_claim(claim))
        for claim in service.list_invite_claims(
            workspace_id=workspace_id,
            user_id=user_id,
            claim_status=claim_status,
        )
    ]
