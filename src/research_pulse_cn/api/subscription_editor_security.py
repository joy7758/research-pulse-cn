"""Auth dependency for short-lived subscription editor handoff grants."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_pulse_cn.api.dependencies import get_subscription_editor_handoff_service
from research_pulse_cn.core.errors import AuthenticationError
from research_pulse_cn.domain.subscription_self_service import (
    SubscriptionEditorHandoffGrantContext,
)
from research_pulse_cn.services.subscription_editor_handoff import (
    SubscriptionEditorHandoffService,
)

subscription_editor_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Subscription editor handoff bearer token.",
)


def get_current_subscription_editor_handoff_grant(
    request: Request,
    service: Annotated[
        SubscriptionEditorHandoffService,
        Depends(get_subscription_editor_handoff_service),
    ],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(subscription_editor_bearer_scheme),
    ] = None,
) -> SubscriptionEditorHandoffGrantContext:
    cached_grant = getattr(request.state, "subscription_editor_handoff_grant", None)
    if cached_grant is not None:
        return cached_grant
    if credentials is None:
        raise AuthenticationError("subscription editor handoff authentication is required")
    grant = service.authenticate_grant_token(credentials.credentials)
    request.state.subscription_editor_handoff_grant = grant
    return grant
