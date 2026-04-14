"""Mini read-grant auth dependencies for /mini endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_pulse_cn.api.dependencies import get_mini_service
from research_pulse_cn.core.errors import AuthenticationError
from research_pulse_cn.domain.mini import MiniGrantContext
from research_pulse_cn.services.mini import MiniService

mini_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Mini read grant bearer token.",
)


def get_current_mini_grant(
    request: Request,
    service: Annotated[MiniService, Depends(get_mini_service)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(mini_bearer_scheme),
    ] = None,
) -> MiniGrantContext:
    cached_grant = getattr(request.state, "mini_grant", None)
    if cached_grant is not None:
        return cached_grant
    if credentials is None:
        raise AuthenticationError("mini read grant authentication is required")
    grant = service.authenticate_grant_token(credentials.credentials)
    request.state.mini_grant = grant
    return grant
