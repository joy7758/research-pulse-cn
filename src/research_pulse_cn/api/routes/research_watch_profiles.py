"""Research watch profile routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_research_watch_profile_service,
)
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.pulse_input import (
    ResearchWatchProfileCreate,
    ResearchWatchProfileRead,
    ResearchWatchProfileUpdate,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.research_watch import ResearchWatchProfileService

router = APIRouter(prefix="/research-watch-profiles", tags=["research-watch-profiles"])
ResearchWatchServiceDep = Annotated[
    ResearchWatchProfileService,
    Depends(get_research_watch_profile_service),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]


@router.get("", response_model=list[ResearchWatchProfileRead])
def list_research_watch_profiles(
    _actor: ViewerDep,
    service: ResearchWatchServiceDep,
    user_id: UserIdQuery = None,
) -> list[ResearchWatchProfileRead]:
    return service.list_profiles(user_id=user_id)


@router.post("", response_model=ResearchWatchProfileRead, status_code=status.HTTP_201_CREATED)
def create_research_watch_profile(
    payload: ResearchWatchProfileCreate,
    request: Request,
    actor: OperatorDep,
    service: ResearchWatchServiceDep,
    audit_service: AuditServiceDep,
) -> ResearchWatchProfileRead:
    profile = service.create_profile(payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="research_watch_profile.create",
        resource_type="research_watch_profile",
        resource_id=str(profile.id),
        status_code=201,
        metadata={
            "user_id": str(profile.user_id),
            "paper_id": str(profile.paper_id) if profile.paper_id else None,
        },
    )
    return profile


@router.patch("/{profile_id}", response_model=ResearchWatchProfileRead)
def update_research_watch_profile(
    profile_id: UUID,
    payload: ResearchWatchProfileUpdate,
    request: Request,
    actor: OperatorDep,
    service: ResearchWatchServiceDep,
    audit_service: AuditServiceDep,
) -> ResearchWatchProfileRead:
    profile = service.update_profile(profile_id, payload)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="research_watch_profile.update",
        resource_type="research_watch_profile",
        resource_id=str(profile.id),
        status_code=200,
    )
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_research_watch_profile(
    profile_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: ResearchWatchServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.delete_profile(profile_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="research_watch_profile.delete",
        resource_type="research_watch_profile",
        resource_id=str(profile_id),
        status_code=204,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bootstrap/{paper_id}", response_model=ResearchWatchProfileRead)
def bootstrap_research_watch_profile(
    paper_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: ResearchWatchServiceDep,
    audit_service: AuditServiceDep,
) -> ResearchWatchProfileRead:
    profile = service.bootstrap_from_paper(paper_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="research_watch_profile.bootstrap",
        resource_type="research_watch_profile",
        resource_id=str(profile.id),
        status_code=200,
        metadata={"paper_id": str(paper_id), "user_id": str(profile.user_id)},
    )
    return profile
