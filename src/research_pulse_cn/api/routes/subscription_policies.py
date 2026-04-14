"""Subscription policy routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from research_pulse_cn.api.dependencies import get_subscription_policy_service
from research_pulse_cn.schemas.subscription_policy import (
    SubscriptionPolicyCreate,
    SubscriptionPolicyRead,
    SubscriptionPolicyUpdate,
)
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService

router = APIRouter(prefix="/subscription-policies", tags=["subscription-policies"])
PolicyServiceDep = Annotated[
    SubscriptionPolicyService,
    Depends(get_subscription_policy_service),
]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[SubscriptionPolicyRead])
def list_policies(
    service: PolicyServiceDep,
    user_id: UserIdQuery = None,
) -> list[SubscriptionPolicyRead]:
    return service.list_policies(user_id=user_id)


@router.post("", response_model=SubscriptionPolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: SubscriptionPolicyCreate,
    service: PolicyServiceDep,
) -> SubscriptionPolicyRead:
    return service.create_policy(payload)


@router.get("/{policy_id}", response_model=SubscriptionPolicyRead)
def get_policy(
    policy_id: UUID,
    service: PolicyServiceDep,
) -> SubscriptionPolicyRead:
    return service.get_policy(policy_id)


@router.put("/{policy_id}", response_model=SubscriptionPolicyRead)
def update_policy(
    policy_id: UUID,
    payload: SubscriptionPolicyUpdate,
    service: PolicyServiceDep,
) -> SubscriptionPolicyRead:
    return service.update_policy(policy_id, payload)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: UUID,
    service: PolicyServiceDep,
) -> Response:
    service.delete_policy(policy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
