"""External retrieval planning and execution routes."""

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
    ExternalRetrievalRunStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
)
from research_pulse_cn.schemas.pulse_input import (
    ExternalRetrievalExecuteResponse,
    ExternalRetrievalInputPreviewResponse,
    ExternalRetrievalPlanBuildResponse,
    ExternalRetrievalPlanRead,
    ExternalRetrievalProviderStatusRead,
    ExternalRetrievalRunDetailRead,
    ExternalRetrievalRunRead,
    ExternalRetrievedRecordRead,
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
RunStatusQuery = Annotated[ExternalRetrievalRunStatus | None, Query()]
PaperIdQuery = Annotated[UUID | None, Query()]
PlanIdQuery = Annotated[UUID | None, Query()]
RunIdQuery = Annotated[UUID | None, Query()]


@router.get("/provider-status", response_model=ExternalRetrievalProviderStatusRead)
def get_external_retrieval_provider_status(
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
) -> ExternalRetrievalProviderStatusRead:
    return service.provider_status()


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
            "Plan build does not perform any external execution by itself.",
        ],
    )


@router.post("/plans/execute/{plan_id}", response_model=ExternalRetrievalExecuteResponse)
def execute_external_retrieval_plan(
    plan_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: ExternalRetrievalServiceDep,
    audit_service: AuditServiceDep,
    force: Annotated[bool, Query()] = False,
) -> ExternalRetrievalExecuteResponse:
    outcome = service.execute_plan(plan_id=plan_id, force=force)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="external_retrieval_plan.execute",
        resource_type="external_retrieval_plan",
        resource_id=str(plan_id),
        status_code=200,
        metadata={
            "plan_id": str(plan_id),
            "run_id": str(outcome.run.id),
            "source_kind": outcome.run.source_kind.value,
            "retrieval_scope": outcome.run.retrieval_scope.value,
            "deduped": outcome.deduped,
            "force": force,
            "normalized_result_count": outcome.run.normalized_result_count,
        },
    )
    return outcome.to_response(mode=service.settings.external_retrieval_mode)


@router.get("/runs", response_model=list[ExternalRetrievalRunRead])
def list_external_retrieval_runs(
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
    user_id: UserIdQuery = None,
    source_kind: SourceKindQuery = None,
    retrieval_scope: RetrievalScopeQuery = None,
    status: RunStatusQuery = None,
    plan_id: PlanIdQuery = None,
) -> list[ExternalRetrievalRunRead]:
    return service.list_runs(
        user_id=user_id,
        source_kind=source_kind,
        retrieval_scope=retrieval_scope,
        status=status,
        plan_id=plan_id,
    )


@router.get("/runs/{run_id}", response_model=ExternalRetrievalRunDetailRead)
def get_external_retrieval_run_detail(
    run_id: UUID,
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
) -> ExternalRetrievalRunDetailRead:
    return service.get_run_detail(run_id)


@router.get("/results", response_model=list[ExternalRetrievedRecordRead])
def list_external_retrieval_results(
    _actor: ViewerDep,
    service: ExternalRetrievalServiceDep,
    user_id: UserIdQuery = None,
    run_id: RunIdQuery = None,
    plan_id: PlanIdQuery = None,
    source_kind: SourceKindQuery = None,
    retrieval_scope: RetrievalScopeQuery = None,
) -> list[ExternalRetrievedRecordRead]:
    return service.list_results(
        user_id=user_id,
        run_id=run_id,
        plan_id=plan_id,
        source_kind=source_kind,
        retrieval_scope=retrieval_scope,
    )
