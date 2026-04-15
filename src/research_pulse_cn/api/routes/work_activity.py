"""Work activity event routes."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from research_pulse_cn.api.dependencies import get_work_activity_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, WorkActivityType
from research_pulse_cn.schemas.pulse_input import WorkActivityEventRead
from research_pulse_cn.services.work_activity import WorkActivityService

router = APIRouter(prefix="/work-activity-events", tags=["work-activity-events"])
WorkActivityServiceDep = Annotated[WorkActivityService, Depends(get_work_activity_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]
UserIdQuery = Annotated[UUID | None, Query()]
PaperIdQuery = Annotated[UUID | None, Query()]
ActivityTypeQuery = Annotated[WorkActivityType | None, Query()]
DateFromQuery = Annotated[date | None, Query()]
DateToQuery = Annotated[date | None, Query()]


@router.get("", response_model=list[WorkActivityEventRead])
def list_work_activity_events(
    _actor: ViewerDep,
    service: WorkActivityServiceDep,
    user_id: UserIdQuery = None,
    paper_id: PaperIdQuery = None,
    activity_type: ActivityTypeQuery = None,
    date_from: DateFromQuery = None,
    date_to: DateToQuery = None,
) -> list[WorkActivityEventRead]:
    return service.list_events(
        user_id=user_id,
        paper_id=paper_id,
        activity_type=activity_type,
        date_from=date_from,
        date_to=date_to,
    )
