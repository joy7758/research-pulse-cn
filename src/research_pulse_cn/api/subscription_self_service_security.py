"""Auth dependency for subscription self-service reserve endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_pulse_cn.api.dependencies import get_subscription_self_service_service
from research_pulse_cn.core.errors import AuthenticationError
from research_pulse_cn.domain.subscription_self_service import (
    SubscriptionSelfServiceGrantContext,
)
from research_pulse_cn.services.subscription_self_service import (
    SubscriptionSelfServiceService,
)

self_service_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Subscription self-service grant bearer token.",
)


def get_current_subscription_self_service_grant(
    request: Request,
    service: Annotated[
        SubscriptionSelfServiceService,
        Depends(get_subscription_self_service_service),
    ],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(self_service_bearer_scheme),
    ] = None,
) -> SubscriptionSelfServiceGrantContext:
    cached_grant = getattr(request.state, "subscription_self_service_grant", None)
    if cached_grant is not None:
        return cached_grant
    if credentials is None:
        raise AuthenticationError("subscription self-service authentication is required")
    grant = service.authenticate_grant_token(credentials.credentials)
    request.state.subscription_self_service_grant = grant
    return grant
