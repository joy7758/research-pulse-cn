"""Application factory for Research Pulse CN."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from research_pulse_cn import __version__
from research_pulse_cn.api.errors import register_exception_handlers
from research_pulse_cn.api.router import api_router
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
        redoc_url="/redoc",
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app
