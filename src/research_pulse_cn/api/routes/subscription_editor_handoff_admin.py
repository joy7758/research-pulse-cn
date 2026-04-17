"""Admin routes for mini-to-editor handoff grants."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_subscription_editor_handoff_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    ChannelType,
    SubscriptionEditorHandoffGrantStatus,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionEditorHandoffGrantRead,
    SubscriptionEditorHandoffGrantRevokeResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.subscription_editor_handoff import (
    SubscriptionEditorHandoffService,
)

router = APIRouter(prefix="/admin", tags=["admin"])
HandoffServiceDep = Annotated[
    SubscriptionEditorHandoffService,
    Depends(get_subscription_editor_handoff_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get(
    "/subscription-editor-handoff-grants",
    response_model=list[SubscriptionEditorHandoffGrantRead],
)
def list_subscription_editor_handoff_grants(
    _actor: OperatorDep,
    service: HandoffServiceDep,
    user_id: UserIdQuery = None,
    channel: Annotated[ChannelType | None, Query()] = None,
    status: Annotated[SubscriptionEditorHandoffGrantStatus | None, Query()] = None,
    mini_grant_id: Annotated[UUID | None, Query()] = None,
    self_service_grant_id: Annotated[UUID | None, Query()] = None,
) -> list[SubscriptionEditorHandoffGrantRead]:
    return [
        SubscriptionEditorHandoffGrantRead(**service.serialize_grant(grant))
        for grant in service.list_grants(
            user_id=user_id,
            channel=channel,
            status=status,
            mini_grant_id=mini_grant_id,
            self_service_grant_id=self_service_grant_id,
        )
    ]


@router.post(
    "/subscription-editor-handoff-grants/{grant_id}/revoke",
    response_model=SubscriptionEditorHandoffGrantRevokeResponse,
)
def revoke_subscription_editor_handoff_grant(
    grant_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: HandoffServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionEditorHandoffGrantRevokeResponse:
    grant = service.revoke_grant(grant_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="subscription_editor_handoff_grant.revoke",
        resource_type="subscription_editor_handoff_grant",
        resource_id=str(grant.id),
        status_code=200,
        metadata={
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
            "mini_grant_id": None if grant.mini_grant_id is None else str(grant.mini_grant_id),
            "self_service_grant_id": str(grant.self_service_grant_id),
        },
    )
    return SubscriptionEditorHandoffGrantRevokeResponse(
        grant=SubscriptionEditorHandoffGrantRead(**service.serialize_grant(grant)),
        revoked_at=grant.updated_at,
    )
