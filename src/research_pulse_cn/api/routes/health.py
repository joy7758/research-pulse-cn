"""Health and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from research_pulse_cn import __version__
from research_pulse_cn.api.dependencies import get_ops_service
from research_pulse_cn.api.security import require_admin_or_service
from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.ops import ReadinessResponse
from research_pulse_cn.services.ops import OpsService

router = APIRouter()
OpsServiceDep = Annotated[OpsService, Depends(get_ops_service)]
OperatorOrServiceDep = Annotated[
    ActorContext,
    Depends(require_admin_or_service(AdminRole.OPERATOR)),
]


class HealthResponse(BaseModel):
    """Response model for application health."""

    status: str
    service: str
    environment: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    """Return a lightweight service health response."""
    settings: Settings = getattr(request.app.state, "settings", get_settings())
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=__version__,
    )


@router.get("/health/live", response_model=HealthResponse)
def live(request: Request) -> HealthResponse:
    """Return a process liveness response without dependency checks."""
    return health(request)


@router.get("/health/ready", response_model=ReadinessResponse)
def ready(
    response: Response,
    _actor: OperatorOrServiceDep,
    service: OpsServiceDep,
) -> ReadinessResponse:
    """Return dependency readiness details for operators."""
    payload, healthy = service.readiness()
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(**payload)
