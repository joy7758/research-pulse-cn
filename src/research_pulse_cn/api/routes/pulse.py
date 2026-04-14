"""Pulse routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from research_pulse_cn.api.dependencies import get_pulse_service
from research_pulse_cn.schemas.pulse import PulsePreviewResponse, PulseRunResponse
from research_pulse_cn.services.pulse import PulseService

router = APIRouter(prefix="/pulse", tags=["pulse"])
PulseServiceDep = Annotated[PulseService, Depends(get_pulse_service)]


@router.post("/preview/{user_id}", response_model=PulsePreviewResponse)
def preview_pulse(
    user_id: UUID,
    service: PulseServiceDep,
) -> PulsePreviewResponse:
    cards = [draft.to_preview() for draft in service.preview(user_id)]
    return PulsePreviewResponse(user_id=user_id, cards=cards)


@router.post("/run/{user_id}", response_model=PulseRunResponse)
def run_pulse(user_id: UUID, service: PulseServiceDep) -> PulseRunResponse:
    job = service.run_now(user_id)
    return PulseRunResponse(job=job, cards=job.cards, delivery_jobs=job.delivery_jobs)
