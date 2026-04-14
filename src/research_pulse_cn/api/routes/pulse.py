"""Pulse routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_pulse_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.pulse import (
    PulseCandidateRead,
    PulseFactRead,
    PulsePreviewResponse,
    PulseRunResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.pulse import PulseService

router = APIRouter(prefix="/pulse", tags=["pulse"])
PulseServiceDep = Annotated[PulseService, Depends(get_pulse_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]


@router.post("/preview/{user_id}", response_model=PulsePreviewResponse)
def preview_pulse(
    user_id: UUID,
    _actor: ViewerDep,
    service: PulseServiceDep,
) -> PulsePreviewResponse:
    pipeline = service.preview(user_id)
    selected_cards = service.build_preview_cards(pipeline.selected_candidates)
    return PulsePreviewResponse(
        user_id=user_id,
        fact_summary=pipeline.fact_summary,
        facts=[PulseFactRead(**fact.to_dict()) for fact in pipeline.facts],
        candidates=[PulseCandidateRead(**candidate.to_dict()) for candidate in pipeline.candidates],
        selected_cards=selected_cards,
        suppressed_candidates=[
            PulseCandidateRead(**candidate.to_dict())
            for candidate in pipeline.suppressed_candidates
        ],
        ordering_explanation=pipeline.ordering_explanation,
        cards=selected_cards,
    )


@router.post("/run/{user_id}", response_model=PulseRunResponse)
def run_pulse(
    user_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: PulseServiceDep,
    audit_service: AuditServiceDep,
) -> PulseRunResponse:
    job, pipeline = service.run_with_pipeline(user_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="pulse.run",
        resource_type="pulse_job",
        resource_id=str(job.id),
        status_code=200,
        metadata={"user_id": str(user_id), "selected_cards": len(job.cards)},
    )
    return PulseRunResponse(
        job=job,
        fact_summary=pipeline.fact_summary,
        suppressed_candidates=[
            PulseCandidateRead(**candidate.to_dict())
            for candidate in pipeline.suppressed_candidates
        ],
        ordering_explanation=pipeline.ordering_explanation,
        cards=job.cards,
        delivery_jobs=job.delivery_jobs,
    )
