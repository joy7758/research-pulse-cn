"""Mini read-only reserve routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from research_pulse_cn.api.dependencies import get_mini_service
from research_pulse_cn.api.mini_security import get_current_mini_grant
from research_pulse_cn.domain.enums import PaperType
from research_pulse_cn.domain.mini import MiniGrantContext
from research_pulse_cn.schemas.mini import (
    MiniBootstrapResponse,
    MiniDigestIssueDetailRead,
    MiniPaperDetailRead,
    MiniPaperSummaryRead,
    MiniSubscriptionReserveRead,
    MiniTodayResponse,
)
from research_pulse_cn.services.mini import MiniService

router = APIRouter(prefix="/mini", tags=["mini"])
MiniServiceDep = Annotated[MiniService, Depends(get_mini_service)]
MiniGrantDep = Annotated[MiniGrantContext, Depends(get_current_mini_grant)]
LimitQuery = Annotated[int | None, Query(ge=1)]


@router.get("/bootstrap", response_model=MiniBootstrapResponse)
def mini_bootstrap(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniBootstrapResponse:
    return MiniBootstrapResponse(**service.bootstrap(grant))


@router.get("/today", response_model=MiniTodayResponse)
def mini_today(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniTodayResponse:
    return MiniTodayResponse(**service.today(grant))


@router.get("/subscription-reserve", response_model=MiniSubscriptionReserveRead)
def mini_subscription_reserve(
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniSubscriptionReserveRead:
    return MiniSubscriptionReserveRead(**service.subscription_reserve(grant))


@router.get("/digest-issues/{digest_issue_id}", response_model=MiniDigestIssueDetailRead)
def mini_digest_issue_detail(
    digest_issue_id: UUID,
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniDigestIssueDetailRead:
    return MiniDigestIssueDetailRead(**service.get_digest_issue_detail(grant, digest_issue_id))


@router.get("/papers", response_model=list[MiniPaperSummaryRead])
def mini_list_papers(
    grant: MiniGrantDep,
    service: MiniServiceDep,
    limit: LimitQuery = None,
    paper_type: Annotated[PaperType | None, Query()] = None,
    stage: Annotated[str | None, Query()] = None,
) -> list[MiniPaperSummaryRead]:
    return [
        MiniPaperSummaryRead(**paper)
        for paper in service.list_papers(
            grant,
            limit=limit,
            paper_type=paper_type,
            stage=stage,
        )
    ]


@router.get("/papers/{paper_id}", response_model=MiniPaperDetailRead)
def mini_get_paper(
    paper_id: UUID,
    grant: MiniGrantDep,
    service: MiniServiceDep,
) -> MiniPaperDetailRead:
    return MiniPaperDetailRead(**service.get_paper_detail(grant, paper_id))
