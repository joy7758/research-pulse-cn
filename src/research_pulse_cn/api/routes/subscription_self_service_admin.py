"""Admin routes for subscription self-service reserve grants."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_subscription_self_service_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    ChannelType,
    SubscriptionSelfServiceGrantStatus,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionSelfServiceGrantCreateRequest,
    SubscriptionSelfServiceGrantIssueResponse,
    SubscriptionSelfServiceGrantRead,
    SubscriptionSelfServiceGrantRevokeResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.subscription_self_service import (
    SubscriptionSelfServiceService,
)

router = APIRouter(prefix="/admin", tags=["admin"])
SelfServiceDep = Annotated[
    SubscriptionSelfServiceService,
    Depends(get_subscription_self_service_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get(
    "/subscription-self-service-grants",
    response_model=list[SubscriptionSelfServiceGrantRead],
)
def list_subscription_self_service_grants(
    _actor: OperatorDep,
    service: SelfServiceDep,
    user_id: UserIdQuery = None,
    channel: Annotated[ChannelType | None, Query()] = None,
    status: Annotated[SubscriptionSelfServiceGrantStatus | None, Query()] = None,
    binding_id: Annotated[UUID | None, Query()] = None,
) -> list[SubscriptionSelfServiceGrantRead]:
    return [
        SubscriptionSelfServiceGrantRead(**service.serialize_grant(grant))
        for grant in service.list_grants(
            user_id=user_id,
            channel=channel,
            status=status,
            binding_id=binding_id,
        )
    ]


@router.post(
    "/subscription-self-service-grants",
    response_model=SubscriptionSelfServiceGrantIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription_self_service_grant(
    payload: SubscriptionSelfServiceGrantCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: SelfServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceGrantIssueResponse:
    grant, issued = service.create_grant(
        user_id=payload.user_id,
        binding_id=payload.binding_id,
        channel=payload.channel,
        grant_scope=payload.grant_scope,
        display_label=payload.display_label,
        expires_at=payload.expires_at,
        issued_by_admin_id=actor.actor_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_self_service_grant.create",
        resource_type="subscription_self_service_grant",
        resource_id=str(grant.id),
        status_code=201,
        metadata={
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
            "binding_id": None if grant.binding_id is None else str(grant.binding_id),
        },
    )
    return SubscriptionSelfServiceGrantIssueResponse(
        grant=SubscriptionSelfServiceGrantRead(**service.serialize_grant(grant)),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
    )


@router.post(
    "/subscription-self-service-grants/{grant_id}/revoke",
    response_model=SubscriptionSelfServiceGrantRevokeResponse,
)
def revoke_subscription_self_service_grant(
    grant_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: SelfServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceGrantRevokeResponse:
    grant = service.revoke_grant(grant_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_self_service_grant.revoke",
        resource_type="subscription_self_service_grant",
        resource_id=str(grant.id),
        status_code=200,
        metadata={
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
        },
    )
    return SubscriptionSelfServiceGrantRevokeResponse(
        grant=SubscriptionSelfServiceGrantRead(**service.serialize_grant(grant)),
        revoked_at=grant.updated_at,
    )
