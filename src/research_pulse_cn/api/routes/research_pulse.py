"""Research pulse draft routes for imported papers."""

from typing import Annotated

from fastapi import APIRouter, Depends

from research_pulse_cn.api.dependencies import SessionDep
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.official_account_daily_summary import (
    OfficialAccountDailySummaryRequest,
    OfficialAccountDailySummaryResult,
)
from research_pulse_cn.schemas.research_pulse import ResearchPulseRequest, ResearchPulseResult
from research_pulse_cn.services.official_account_daily_summary import (
    OfficialAccountDailySummaryService,
)
from research_pulse_cn.services.research_pulse import ResearchPulseService

router = APIRouter(prefix="/pulse", tags=["pulse"])
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]


def get_research_pulse_service(session: SessionDep) -> ResearchPulseService:
    return ResearchPulseService(session)


ResearchPulseServiceDep = Annotated[
    ResearchPulseService,
    Depends(get_research_pulse_service),
]


def get_official_account_daily_summary_service(
    session: SessionDep,
) -> OfficialAccountDailySummaryService:
    return OfficialAccountDailySummaryService(session)


OfficialAccountDailySummaryServiceDep = Annotated[
    OfficialAccountDailySummaryService,
    Depends(get_official_account_daily_summary_service),
]


@router.post("/papers/daily", response_model=ResearchPulseResult)
def generate_research_pulse_from_imported_papers(
    payload: ResearchPulseRequest,
    _actor: ViewerDep,
    service: ResearchPulseServiceDep,
) -> ResearchPulseResult:
    return service.generate_daily_pulse(payload)


@router.post(
    "/papers/official-account/daily-summary",
    response_model=OfficialAccountDailySummaryResult,
)
def generate_official_account_daily_summary_from_imported_papers(
    payload: OfficialAccountDailySummaryRequest,
    _actor: ViewerDep,
    service: OfficialAccountDailySummaryServiceDep,
) -> OfficialAccountDailySummaryResult:
    return service.build_daily_summary(payload)
