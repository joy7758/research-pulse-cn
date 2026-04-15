"""Admin routes for official-account binding handshake reserve workflows."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_official_account_binding_handshake_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    ChannelType,
    OfficialAccountBindingHandshakeSessionStatus,
)
from research_pulse_cn.schemas.digest import (
    OfficialAccountBindingHandshakeClaimRequest,
    OfficialAccountBindingHandshakeClaimResponse,
    OfficialAccountBindingHandshakeSessionCancelResponse,
    OfficialAccountBindingHandshakeSessionCreateRequest,
    OfficialAccountBindingHandshakeSessionIssueResponse,
    OfficialAccountBindingHandshakeSessionRead,
    OfficialAccountBindingReconciliationCandidateRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.official_account_binding_handshake import (
    OfficialAccountBindingHandshakeService,
)

router = APIRouter(prefix="/admin", tags=["admin"])
HandshakeDep = Annotated[
    OfficialAccountBindingHandshakeService,
    Depends(get_official_account_binding_handshake_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get(
    "/official-account-binding-handshake-sessions",
    response_model=list[OfficialAccountBindingHandshakeSessionRead],
)
def list_official_account_binding_handshake_sessions(
    _actor: OperatorDep,
    service: HandshakeDep,
    user_id: UserIdQuery = None,
    channel: Annotated[ChannelType | None, Query()] = None,
    status: Annotated[OfficialAccountBindingHandshakeSessionStatus | None, Query()] = None,
    self_service_grant_id: Annotated[UUID | None, Query()] = None,
    app_id: Annotated[str | None, Query()] = None,
) -> list[OfficialAccountBindingHandshakeSessionRead]:
    return [
        OfficialAccountBindingHandshakeSessionRead(**service.serialize_session(session))
        for session in service.list_sessions(
            user_id=user_id,
            channel=channel,
            status=status,
            self_service_grant_id=self_service_grant_id,
            app_id=app_id,
        )
    ]


@router.post(
    "/official-account-binding-handshake-sessions",
    response_model=OfficialAccountBindingHandshakeSessionIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_official_account_binding_handshake_session(
    payload: OfficialAccountBindingHandshakeSessionCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: HandshakeDep,
    audit_service: AuditServiceDep,
) -> OfficialAccountBindingHandshakeSessionIssueResponse:
    session, issued = service.create_session(
        user_id=payload.user_id,
        app_id=payload.app_id,
        display_label=payload.display_label,
        self_service_grant_id=payload.self_service_grant_id,
        issued_by_admin_id=actor.actor_id,
        expires_at=payload.expires_at,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="official_account_binding_handshake_session.create",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(session.id),
        status_code=201,
        metadata={
            "user_id": str(session.user_id),
            "app_id": session.app_id,
            "self_service_grant_id": (
                None
                if session.self_service_grant_id is None
                else str(session.self_service_grant_id)
            ),
        },
    )
    return OfficialAccountBindingHandshakeSessionIssueResponse(
        session=OfficialAccountBindingHandshakeSessionRead(**service.serialize_session(session)),
        plain_text_state_token=issued.plain_text_state_token,
        expires_at=issued.expires_at,
    )


@router.get(
    "/official-account-binding-handshake-sessions/{session_id}",
    response_model=OfficialAccountBindingHandshakeSessionRead,
)
def get_official_account_binding_handshake_session(
    session_id: UUID,
    _actor: OperatorDep,
    service: HandshakeDep,
) -> OfficialAccountBindingHandshakeSessionRead:
    return OfficialAccountBindingHandshakeSessionRead(
        **service.serialize_session(service.get_session(session_id))
    )


@router.post(
    "/official-account-binding-handshake-sessions/{session_id}/cancel",
    response_model=OfficialAccountBindingHandshakeSessionCancelResponse,
)
def cancel_official_account_binding_handshake_session(
    session_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: HandshakeDep,
    audit_service: AuditServiceDep,
) -> OfficialAccountBindingHandshakeSessionCancelResponse:
    session = service.cancel_session(session_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="official_account_binding_handshake_session.cancel",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(session.id),
        status_code=200,
        metadata={
            "user_id": str(session.user_id),
            "app_id": session.app_id,
        },
    )
    return OfficialAccountBindingHandshakeSessionCancelResponse(
        session=OfficialAccountBindingHandshakeSessionRead(**service.serialize_session(session)),
        cancelled_at=session.updated_at,
    )


@router.get(
    "/official-account-binding-reconciliation/candidates",
    response_model=list[OfficialAccountBindingReconciliationCandidateRead],
)
def list_official_account_binding_reconciliation_candidates(
    _actor: OperatorDep,
    service: HandshakeDep,
    app_id: Annotated[str, Query(min_length=1)],
    signature_valid: Annotated[bool | None, Query()] = None,
    event_type: Annotated[str | None, Query()] = None,
    unmatched_only: Annotated[bool, Query()] = True,
) -> list[OfficialAccountBindingReconciliationCandidateRead]:
    return [
        OfficialAccountBindingReconciliationCandidateRead(**candidate)
        for candidate in service.list_reconciliation_candidates(
            app_id=app_id,
            signature_valid=signature_valid,
            event_type=event_type,
            unmatched_only=unmatched_only,
        )
    ]


@router.post(
    "/official-account-binding-handshake-sessions/{session_id}/claim",
    response_model=OfficialAccountBindingHandshakeClaimResponse,
)
def claim_official_account_binding_handshake_session(
    session_id: UUID,
    payload: OfficialAccountBindingHandshakeClaimRequest,
    request: Request,
    actor: OperatorDep,
    service: HandshakeDep,
    audit_service: AuditServiceDep,
) -> OfficialAccountBindingHandshakeClaimResponse:
    result = service.claim_session(
        session_id,
        callback_event_id=payload.callback_event_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="official_account_binding_handshake_session.claim",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(session_id),
        status_code=200,
        metadata={
            "user_id": str(result["session"]["user_id"]),
            "callback_event_id": str(result["callback_event"]["callback_event_id"]),
            "claimed_binding_id": str(result["claimed_binding"]["id"]),
        },
    )
    return OfficialAccountBindingHandshakeClaimResponse(
        session=OfficialAccountBindingHandshakeSessionRead(**result["session"]),
        claimed_binding=result["claimed_binding"],
        callback_event=OfficialAccountBindingReconciliationCandidateRead(
            **result["callback_event"]
        ),
    )
