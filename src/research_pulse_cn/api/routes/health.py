"""Health and readiness endpoints."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from research_pulse_cn import __version__
from research_pulse_cn.core.config import Settings, get_settings

router = APIRouter()


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
