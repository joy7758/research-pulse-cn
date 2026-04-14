"""Paper routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from research_pulse_cn.api.dependencies import get_paper_service
from research_pulse_cn.schemas.paper import (
    PaperProfileCreate,
    PaperProfileRead,
    PaperProfileUpdate,
    ProgressEventCreate,
    ProgressEventRead,
    SignalSnapshotCreate,
    SignalSnapshotRead,
)
from research_pulse_cn.services.paper import PaperService

router = APIRouter(prefix="/papers", tags=["papers"])
PaperServiceDep = Annotated[PaperService, Depends(get_paper_service)]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[PaperProfileRead])
def list_papers(
    service: PaperServiceDep,
    user_id: UserIdQuery = None,
) -> list[PaperProfileRead]:
    return service.list_papers(user_id=user_id)


@router.post("", response_model=PaperProfileRead, status_code=status.HTTP_201_CREATED)
def create_paper(
    payload: PaperProfileCreate,
    service: PaperServiceDep,
) -> PaperProfileRead:
    return service.create_paper(payload)


@router.get("/{paper_id}", response_model=PaperProfileRead)
def get_paper(paper_id: UUID, service: PaperServiceDep) -> PaperProfileRead:
    return service.get_paper(paper_id)


@router.put("/{paper_id}", response_model=PaperProfileRead)
def update_paper(
    paper_id: UUID,
    payload: PaperProfileUpdate,
    service: PaperServiceDep,
) -> PaperProfileRead:
    return service.update_paper(paper_id, payload)


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(paper_id: UUID, service: PaperServiceDep) -> Response:
    service.delete_paper(paper_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{paper_id}/progress-events",
    response_model=ProgressEventRead,
    status_code=status.HTTP_201_CREATED,
)
def add_progress_event(
    paper_id: UUID,
    payload: ProgressEventCreate,
    service: PaperServiceDep,
) -> ProgressEventRead:
    return service.add_progress_event(paper_id, payload)


@router.get("/{paper_id}/progress-events", response_model=list[ProgressEventRead])
def list_progress_events(
    paper_id: UUID,
    service: PaperServiceDep,
) -> list[ProgressEventRead]:
    return service.list_progress_events(paper_id)


@router.post(
    "/{paper_id}/signal-snapshots",
    response_model=SignalSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def add_signal_snapshot(
    paper_id: UUID,
    payload: SignalSnapshotCreate,
    service: PaperServiceDep,
) -> SignalSnapshotRead:
    return service.add_signal_snapshot(paper_id, payload)


@router.get("/{paper_id}/signal-snapshots", response_model=list[SignalSnapshotRead])
def list_signal_snapshots(
    paper_id: UUID,
    service: PaperServiceDep,
) -> list[SignalSnapshotRead]:
    return service.list_signal_snapshots(paper_id)
