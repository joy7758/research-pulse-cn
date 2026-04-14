"""Pulse routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from research_pulse_cn.api.dependencies import get_pulse_service
from research_pulse_cn.schemas.pulse import (
    PulseCandidateRead,
    PulseFactRead,
    PulsePreviewResponse,
    PulseRunResponse,
)
from research_pulse_cn.services.pulse import PulseService

router = APIRouter(prefix="/pulse", tags=["pulse"])
PulseServiceDep = Annotated[PulseService, Depends(get_pulse_service)]


@router.post("/preview/{user_id}", response_model=PulsePreviewResponse)
def preview_pulse(
    user_id: UUID,
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
def run_pulse(user_id: UUID, service: PulseServiceDep) -> PulseRunResponse:
    job, pipeline = service.run_with_pipeline(user_id)
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
