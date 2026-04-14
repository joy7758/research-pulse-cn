"""FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from research_pulse_cn.core.errors import ConflictError, NotFoundError, ValidationFailedError


def register_exception_handlers(app: FastAPI) -> None:
    """Register API exception mappings."""

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ValidationFailedError)
    async def handle_validation(_: Request, exc: ValidationFailedError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})
