"""Mini read-only reserve routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_mini_service,
    get_subscription_editor_handoff_service,
)
from research_pulse_cn.api.mini_security import get_current_mini_grant
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType, PaperType
from research_pulse_cn.domain.mini import MiniGrantContext
from research_pulse_cn.schemas.mini import (
    MiniBootstrapResponse,
    MiniDigestIssueDetailRead,
    MiniPaperDetailRead,
    MiniPaperSummaryRead,
    MiniSubscriptionReserveRead,
    MiniTodayResponse,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionEditorHandoffIssueResponse,
    SubscriptionEditorHandoffStatusResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.mini import MiniService
from research_pulse_cn.services.subscription_editor_handoff import (
    SUBSCRIPTION_EDITOR_ENDPOINTS,
    SubscriptionEditorHandoffService,
)

router = APIRouter(prefix="/mini", tags=["mini"])
MiniServiceDep = Annotated[MiniService, Depends(get_mini_service)]
MiniGrantDep = Annotated[MiniGrantContext, Depends(get_current_mini_grant)]
HandoffServiceDep = Annotated[
    SubscriptionEditorHandoffService,
    Depends(get_subscription_editor_handoff_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
LimitQuery = Annotated[int | None, Query(ge=1)]


def _mini_handoff_actor(grant: MiniGrantContext) -> ActorContext:
    return ActorContext(
        actor_type=AuditActorType.ANONYMOUS,
        actor_label=f"mini_read:{grant.grant_id}",
        is_active=True,
    )


@router.get("/bootstrap", response_model=MiniBootstrapResponse)
def mini_bootstrap(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniBootstrapResponse:
    return MiniBootstrapResponse(**service.bootstrap(grant))


@router.get("/today", response_model=MiniTodayResponse)
def mini_today(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniTodayResponse:
    return MiniTodayResponse(**service.today(grant))


@router.get("/subscription-reserve", response_model=MiniSubscriptionReserveRead)
def mini_subscription_reserve(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniSubscriptionReserveRead:
    return MiniSubscriptionReserveRead(**service.subscription_reserve(grant))


@router.post(
    "/subscription-reserve/editor-handoff",
    response_model=SubscriptionEditorHandoffIssueResponse,
    status_code=201,
)
def mini_create_subscription_editor_handoff(
    request: Request,
    grant: MiniGrantDep,
    service: HandoffServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionEditorHandoffIssueResponse:
    handoff_grant, issued = service.create_handoff_from_mini(grant)
    audit_service.safe_record(
        actor=_mini_handoff_actor(grant),
        action="mini.subscription_editor_handoff.create",
        resource_type="subscription_editor_handoff_grant",
        resource_id=str(handoff_grant.id),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=201,
        metadata={
            "handoff_grant_id": str(handoff_grant.id),
            "mini_grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "channel": handoff_grant.channel.value,
        },
    )
    return SubscriptionEditorHandoffIssueResponse(
        handoff_grant=service.serialize_grant(handoff_grant),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
        supported_editor_endpoints=list(SUBSCRIPTION_EDITOR_ENDPOINTS),
        notes=[
            "Use this short-lived token only on /subscription-editor/* endpoints.",
            "Mini read grants still cannot call editor endpoints directly.",
        ],
    )


@router.get(
    "/subscription-reserve/editor-handoff-status",
    response_model=SubscriptionEditorHandoffStatusResponse,
)
def mini_get_subscription_editor_handoff_status(
    request: Request,
    grant: MiniGrantDep,
    service: HandoffServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionEditorHandoffStatusResponse:
    payload = service.get_handoff_status_for_mini(grant)
    audit_service.safe_record(
        actor=_mini_handoff_actor(grant),
        action="mini.subscription_editor_handoff.status",
        resource_type="subscription_editor_handoff_grant",
        resource_id=(
            None if payload["handoff_grant"] is None else str(payload["handoff_grant"]["id"])
        ),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "mini_grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
        },
    )
    return SubscriptionEditorHandoffStatusResponse(**payload)


@router.get("/digest-issues/{digest_issue_id}", response_model=MiniDigestIssueDetailRead)
def mini_digest_issue_detail(
    digest_issue_id: UUID,
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniDigestIssueDetailRead:
    return MiniDigestIssueDetailRead(**service.get_digest_issue_detail(grant, digest_issue_id))


@router.get("/papers", response_model=list[MiniPaperSummaryRead])
def mini_list_papers(
    grant: MiniGrantDep,
    service: MiniServiceDep,
    limit: LimitQuery = None,
    paper_type: Annotated[PaperType | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
) -> list[MiniPaperSummaryRead]:
    return [
        MiniPaperSummaryRead(**paper)
        for paper in service.list_papers(
            grant,
            limit=limit,
            paper_type=paper_type,
            stage=stage,
        )
    ]


@router.get("/papers/{paper_id}", response_model=MiniPaperDetailRead)
def mini_get_paper(
    paper_id: UUID,
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniPaperDetailRead:
    return MiniPaperDetailRead(**service.get_paper_detail(grant, paper_id))
