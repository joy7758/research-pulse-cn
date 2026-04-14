"""User routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_user_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.user import UserProfileCreate, UserProfileRead, UserProfileUpdate
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]


@router.get("", response_model=list[UserProfileRead])
def list_users(_actor: ViewerDep, service: UserServiceDep) -> list[UserProfileRead]:
    return service.list_users()


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserProfileCreate,
    request: Request,
    actor: OperatorDep,
    service: UserServiceDep,
    audit_service: AuditServiceDep,
) -> UserProfileRead:
    user = service.create_user(payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="user_profile.create",
        resource_type="user_profile",
        resource_id=str(user.id),
        status_code=201,
    )
    return user


@router.get("/{user_id}", response_model=UserProfileRead)
def get_user(user_id: UUID, _actor: ViewerDep, service: UserServiceDep) -> UserProfileRead:
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserProfileRead)
def update_user(
    user_id: UUID,
    payload: UserProfileUpdate,
    request: Request,
    actor: OperatorDep,
    service: UserServiceDep,
    audit_service: AuditServiceDep,
) -> UserProfileRead:
    user = service.update_user(user_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="user_profile.update",
        resource_type="user_profile",
        resource_id=str(user.id),
        status_code=200,
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: UserServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.delete_user(user_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="user_profile.delete",
        resource_type="user_profile",
        resource_id=str(user_id),
        status_code=204,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
