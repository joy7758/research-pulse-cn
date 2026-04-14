"""Subscription policy routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_subscription_policy_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.subscription_policy import (
    SubscriptionPolicyCreate,
    SubscriptionPolicyRead,
    SubscriptionPolicyUpdate,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService

router = APIRouter(prefix="/subscription-policies", tags=["subscription-policies"])
PolicyServiceDep = Annotated[
    SubscriptionPolicyService,
    Depends(get_subscription_policy_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[SubscriptionPolicyRead])
def list_policies(
    _actor: ViewerDep,
    service: PolicyServiceDep,
    user_id: UserIdQuery = None,
) -> list[SubscriptionPolicyRead]:
    return service.list_policies(user_id=user_id)


@router.post("", response_model=SubscriptionPolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: SubscriptionPolicyCreate,
    request: Request,
    actor: OperatorDep,
    service: PolicyServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionPolicyRead:
    policy = service.create_policy(payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_policy.create",
        resource_type="subscription_policy",
        resource_id=str(policy.id),
        status_code=201,
    )
    return policy


@router.get("/{policy_id}", response_model=SubscriptionPolicyRead)
def get_policy(
    policy_id: UUID,
    _actor: ViewerDep,
    service: PolicyServiceDep,
) -> SubscriptionPolicyRead:
    return service.get_policy(policy_id)


@router.put("/{policy_id}", response_model=SubscriptionPolicyRead)
def update_policy(
    policy_id: UUID,
    payload: SubscriptionPolicyUpdate,
    request: Request,
    actor: OperatorDep,
    service: PolicyServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionPolicyRead:
    policy = service.update_policy(policy_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_policy.update",
        resource_type="subscription_policy",
        resource_id=str(policy.id),
        status_code=200,
    )
    return policy


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: PolicyServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.delete_policy(policy_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_policy.delete",
        resource_type="subscription_policy",
        resource_id=str(policy_id),
        status_code=204,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
