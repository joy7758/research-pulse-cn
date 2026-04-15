"""Pulse routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_external_retrieval_service,
    get_pulse_service,
    get_research_watch_profile_service,
    get_work_activity_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.pulse import (
    PulseCandidateRead,
    PulseFactRead,
    PulsePreviewResponse,
    PulseRunResponse,
)
from research_pulse_cn.schemas.pulse_input import PulseInputPreviewResponse
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.external_retrieval import ExternalRetrievalService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.research_watch import ResearchWatchProfileService
from research_pulse_cn.services.work_activity import WorkActivityService

router = APIRouter(prefix="/pulse", tags=["pulse"])
PulseServiceDep = Annotated[PulseService, Depends(get_pulse_service)]
ExternalRetrievalServiceDep = Annotated[
    ExternalRetrievalService,
    Depends(get_external_retrieval_service),
]
WorkActivityServiceDep = Annotated[WorkActivityService, Depends(get_work_activity_service)]
ResearchWatchServiceDep = Annotated[
    ResearchWatchProfileService,
    Depends(get_research_watch_profile_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]


@router.post("/preview/{user_id}", response_model=PulsePreviewResponse)
def preview_pulse(
    user_id: UUID,
    _actor: ViewerDep,
    service: PulseServiceDep,
    timezone: Annotated[str | None, Query()] = None,
) -> PulsePreviewResponse:
    pipeline = service.preview(user_id, timezone_name=timezone)
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


@router.get("/input-preview/{user_id}", response_model=PulseInputPreviewResponse)
def preview_pulse_inputs(
    user_id: UUID,
    _actor: ViewerDep,
    work_activity_service: WorkActivityServiceDep,
    research_watch_service: ResearchWatchServiceDep,
    external_retrieval_service: ExternalRetrievalServiceDep,
) -> PulseInputPreviewResponse:
    preview_date, started_at, ended_at, work_summary, events = (
        work_activity_service.summary_and_events_for_previous_day(user_id=user_id)
    )
    enabled_profiles = [
        profile
        for profile in research_watch_service.list_profiles(user_id=user_id)
        if profile.enabled
    ]
    effective_watch_seeds = research_watch_service.effective_watch_seeds_from_profiles(
        enabled_profiles
    )
    retrieval_input_preview = external_retrieval_service.compact_preview(user_id=user_id)
    get_metrics().increment("pulse_input_previews_total")
    with bind_log_context(user_id=user_id):
        return PulseInputPreviewResponse(
            user_id=user_id,
            preview_date=preview_date,
            window_started_at=started_at,
            window_ended_at=ended_at,
            work_activity_summary=work_summary,
            work_activity_events=events,
            enabled_watch_profiles=enabled_profiles,
            effective_watch_seeds=effective_watch_seeds,
            retrieval_input_preview=retrieval_input_preview,
            notes=[
                "This preview shows only current pulse inputs.",
                (
                    "External retrieval will later use effective watch seeds plus "
                    "recent work activity."
                ),
                "Retrieval planning below is still plan-only and does not execute external calls.",
            ],
        )


@router.post("/run/{user_id}", response_model=PulseRunResponse)
def run_pulse(
    user_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: PulseServiceDep,
    audit_service: AuditServiceDep,
    timezone: Annotated[str | None, Query()] = None,
) -> PulseRunResponse:
    job, pipeline = service.run_with_pipeline(user_id, timezone_name=timezone)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="pulse.run",
        resource_type="pulse_job",
        resource_id=str(job.id),
        status_code=200,
        metadata={
            "user_id": str(user_id),
            "selected_cards": len(job.cards),
            "timezone": timezone,
        },
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
