"""Read-only admin routes for the internal user workbench shell."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from research_pulse_cn.api.dependencies import get_user_workbench_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, PaperType
from research_pulse_cn.schemas.user_workbench import (
    UserWorkbenchPaperDetailRead,
    UserWorkbenchPaperSummaryRead,
    UserWorkbenchUserDetailRead,
    UserWorkbenchUserSummaryRead,
    UserWorkbenchWatchProfileRead,
)
from research_pulse_cn.services.user_workbench import UserWorkbenchService

router = APIRouter(prefix="/admin/user-workbench", tags=["admin"])
WorkbenchServiceDep = Annotated[UserWorkbenchService, Depends(get_user_workbench_service)]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]


@router.get("/users", response_model=list[UserWorkbenchUserSummaryRead])
def list_user_workbench_users(
    _actor: ViewerDep,
    service: WorkbenchServiceDep,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
) -> list[UserWorkbenchUserSummaryRead]:
    return [UserWorkbenchUserSummaryRead(**item) for item in service.list_users(q=q, limit=limit)]


@router.get("/users/{user_id}", response_model=UserWorkbenchUserDetailRead)
def get_user_workbench_user_detail(
    user_id: UUID,
    _actor: ViewerDep,
    service: WorkbenchServiceDep,
) -> UserWorkbenchUserDetailRead:
    return UserWorkbenchUserDetailRead(**service.get_user_detail(user_id))


@router.get("/papers", response_model=list[UserWorkbenchPaperSummaryRead])
def list_user_workbench_papers(
    _actor: ViewerDep,
    service: WorkbenchServiceDep,
    q: Annotated[str | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
    paper_type: Annotated[PaperType | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[UserWorkbenchPaperSummaryRead]:
    return [
        UserWorkbenchPaperSummaryRead(**item)
        for item in service.list_papers(
            q=q,
            user_id=user_id,
            stage=stage,
            paper_type=paper_type,
            limit=limit,
        )
    ]


@router.get("/papers/{paper_id}", response_model=UserWorkbenchPaperDetailRead)
def get_user_workbench_paper_detail(
    paper_id: UUID,
    _actor: ViewerDep,
    service: WorkbenchServiceDep,
) -> UserWorkbenchPaperDetailRead:
    return UserWorkbenchPaperDetailRead(**service.get_paper_detail(paper_id))


@router.get("/watch-profiles", response_model=list[UserWorkbenchWatchProfileRead])
def list_user_workbench_watch_profiles(
    _actor: ViewerDep,
    service: WorkbenchServiceDep,
    user_id: Annotated[UUID | None, Query()] = None,
    paper_id: Annotated[UUID | None, Query()] = None,
    enabled: Annotated[bool | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
) -> list[UserWorkbenchWatchProfileRead]:
    return [
        UserWorkbenchWatchProfileRead(**item)
        for item in service.list_watch_profiles(
            user_id=user_id,
            paper_id=paper_id,
            enabled=enabled,
            q=q,
        )
    ]
