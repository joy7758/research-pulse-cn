"""External retrieval input planning routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_external_retrieval_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    ExternalRetrievalPlanStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
)
from research_pulse_cn.schemas.pulse_input import (
    ExternalRetrievalInputPreviewResponse,
    ExternalRetrievalPlanBuildResponse,
    ExternalRetrievalPlanRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.external_retrieval import ExternalRetrievalService

router = APIRouter(prefix="/external-retrieval", tags=["external-retrieval"])
ExternalRetrievalServiceDep = Annotated[
    ExternalRetrievalService,
    Depends(get_external_retrieval_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]
SourceKindQuery = Annotated[ExternalRetrievalSourceKind | None, Query()]
RetrievalScopeQuery = Annotated[ExternalRetrievalScope | None, Query()]
StatusQuery = Annotated[ExternalRetrievalPlanStatus | None, Query()]
PaperIdQuery = Annotated[UUID | None, Query()]


@router.get("/input-preview/{user_id}", response_model=ExternalRetrievalInputPreviewResponse)
def preview_external_retrieval_inputs(
    user_id: UUID,
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
) -> ExternalRetrievalInputPreviewResponse:
    return service.preview_input(user_id=user_id)


@router.get("/plans", response_model=list[ExternalRetrievalPlanRead])
def list_external_retrieval_plans(
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
    user_id: UserIdQuery = None,
    source_kind: SourceKindQuery = None,
    retrieval_scope: RetrievalScopeQuery = None,
    status: StatusQuery = None,
    paper_id: PaperIdQuery = None,
) -> list[ExternalRetrievalPlanRead]:
    return service.list_plans(
        user_id=user_id,
        source_kind=source_kind,
        retrieval_scope=retrieval_scope,
        status=status,
        paper_id=paper_id,
    )


@router.post("/plans/build/{user_id}", response_model=ExternalRetrievalPlanBuildResponse)
def build_external_retrieval_plans(
    user_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: ExternalRetrievalServiceDep,
    audit_service: AuditServiceDep,
) -> ExternalRetrievalPlanBuildResponse:
    plans = service.build_and_persist_plans(user_id=user_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="external_retrieval_plan.build",
        resource_type="external_retrieval_plan",
        resource_id=str(user_id),
        status_code=200,
        metadata={"user_id": str(user_id), "plan_count": len(plans)},
    )
    return ExternalRetrievalPlanBuildResponse(
        user_id=user_id,
        mode=service.settings.external_retrieval_mode,
        built_plans=plans,
        notes=[
            "Plans were persisted with deterministic plan_hash upsert semantics.",
            "No external execution occurred in this phase.",
        ],
    )
