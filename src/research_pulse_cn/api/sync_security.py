"""Device-token auth dependencies for sync endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_pulse_cn.api.dependencies import get_sync_service
from research_pulse_cn.core.errors import AuthenticationError
from research_pulse_cn.domain.sync import DeviceContext
from research_pulse_cn.services.sync import SyncService

sync_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Device sync bearer token.",
)


def get_current_device(
    request: Request,
    service: Annotated[SyncService, Depends(get_sync_service)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(sync_bearer_scheme),
    ] = None,
) -> DeviceContext:
    cached_device = getattr(request.state, "sync_device", None)
    if cached_device is not None:
        return cached_device
    if credentials is None:
        raise AuthenticationError("device authentication is required")
    device = service.authenticate_device_token(credentials.credentials)
    request.state.sync_device = device
    return device
