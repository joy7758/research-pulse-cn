"""Paper routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_paper_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.paper import (
    PaperProfileCreate,
    PaperProfileRead,
    PaperProfileUpdate,
    ProgressEventCreate,
    ProgressEventRead,
    SignalSnapshotCreate,
    SignalSnapshotRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.paper import PaperService

router = APIRouter(prefix="/papers", tags=["papers"])
PaperServiceDep = Annotated[PaperService, Depends(get_paper_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[PaperProfileRead])
def list_papers(
    _actor: ViewerDep,
    service: PaperServiceDep,
    user_id: UserIdQuery = None,
) -> list[PaperProfileRead]:
    return service.list_papers(user_id=user_id)


@router.post("", response_model=PaperProfileRead, status_code=status.HTTP_201_CREATED)
def create_paper(
    payload: PaperProfileCreate,
    request: Request,
    actor: OperatorDep,
    service: PaperServiceDep,
    audit_service: AuditServiceDep,
) -> PaperProfileRead:
    paper = service.create_paper(payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="paper_profile.create",
        resource_type="paper_profile",
        resource_id=str(paper.id),
        status_code=201,
    )
    return paper


@router.get("/{paper_id}", response_model=PaperProfileRead)
def get_paper(
    paper_id: UUID,
    _actor: ViewerDep,
    service: PaperServiceDep,
) -> PaperProfileRead:
    return service.get_paper(paper_id)


@router.put("/{paper_id}", response_model=PaperProfileRead)
def update_paper(
    paper_id: UUID,
    payload: PaperProfileUpdate,
    request: Request,
    actor: OperatorDep,
    service: PaperServiceDep,
    audit_service: AuditServiceDep,
) -> PaperProfileRead:
    paper = service.update_paper(paper_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="paper_profile.update",
        resource_type="paper_profile",
        resource_id=str(paper.id),
        status_code=200,
    )
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: PaperServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.delete_paper(paper_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="paper_profile.delete",
        resource_type="paper_profile",
        resource_id=str(paper_id),
        status_code=204,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{paper_id}/progress-events",
    response_model=ProgressEventRead,
    status_code=status.HTTP_201_CREATED,
)
def add_progress_event(
    paper_id: UUID,
    payload: ProgressEventCreate,
    request: Request,
    actor: OperatorDep,
    service: PaperServiceDep,
    audit_service: AuditServiceDep,
) -> ProgressEventRead:
    event = service.add_progress_event(paper_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="progress_event.create",
        resource_type="progress_event",
        resource_id=str(event.id),
        status_code=201,
        metadata={"paper_id": str(paper_id)},
    )
    return event


@router.get("/{paper_id}/progress-events", response_model=list[ProgressEventRead])
def list_progress_events(
    paper_id: UUID,
    _actor: ViewerDep,
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
    request: Request,
    actor: OperatorDep,
    service: PaperServiceDep,
    audit_service: AuditServiceDep,
) -> SignalSnapshotRead:
    snapshot = service.add_signal_snapshot(paper_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="signal_snapshot.create",
        resource_type="signal_snapshot",
        resource_id=str(snapshot.id),
        status_code=201,
        metadata={"paper_id": str(paper_id)},
    )
    return snapshot


@router.get("/{paper_id}/signal-snapshots", response_model=list[SignalSnapshotRead])
def list_signal_snapshots(
    paper_id: UUID,
    _actor: ViewerDep,
    service: PaperServiceDep,
) -> list[SignalSnapshotRead]:
    return service.list_signal_snapshots(paper_id)
