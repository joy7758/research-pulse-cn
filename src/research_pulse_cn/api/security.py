"""Reusable authentication and authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_pulse_cn.api.dependencies import SessionDep
from research_pulse_cn.core.errors import AuthenticationError, AuthorizationError
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, AuditActorType
from research_pulse_cn.services.auth import AuthService

admin_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Admin access token or internal service bearer token.",
)

ROLE_ORDER: dict[AdminRole, int] = {
    AdminRole.VIEWER: 1,
    AdminRole.OPERATOR: 2,
    AdminRole.SUPER_ADMIN: 3,
}


def get_current_actor(
    request: Request,
    session: SessionDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(admin_bearer_scheme),
    ] = None,
) -> ActorContext:
    """Resolve the caller as admin, internal service, or anonymous."""
    cached_actor = getattr(request.state, "actor", None)
    if cached_actor is not None:
        return cached_actor

    if credentials is None:
        actor = ActorContext(actor_type=AuditActorType.ANONYMOUS)
        request.state.actor = actor
        return actor

    token = credentials.credentials
    auth_service = AuthService(session)
    actor = auth_service.authenticate_internal_service_token(token)
    if actor is None:
        actor = auth_service.authenticate_access_token(token)
    request.state.actor = actor
    return actor


def require_admin_role(minimum_role: AdminRole) -> Callable[[ActorContext], ActorContext]:
    """Require an authenticated admin with at least the requested role."""

    def dependency(
        actor: Annotated[ActorContext, Depends(get_current_actor)],
    ) -> ActorContext:
        if actor.is_anonymous:
            raise AuthenticationError("authentication is required")
        if actor.is_service:
            raise AuthorizationError("internal service token is not allowed on this route")
        if actor.admin_role is None:
            raise AuthenticationError("admin authentication is required")
        if ROLE_ORDER[actor.admin_role] < ROLE_ORDER[minimum_role]:
            raise AuthorizationError("insufficient admin role for this action")
        return actor

    return dependency


def require_admin_or_service(minimum_role: AdminRole) -> Callable[[ActorContext], ActorContext]:
    """Allow either an internal service token or an admin with the requested role."""

    def dependency(
        actor: Annotated[ActorContext, Depends(get_current_actor)],
    ) -> ActorContext:
        if actor.is_service:
            return actor
        if actor.is_anonymous:
            raise AuthenticationError("authentication is required")
        if actor.admin_role is None:
            raise AuthenticationError("admin authentication is required")
        if ROLE_ORDER[actor.admin_role] < ROLE_ORDER[minimum_role]:
            raise AuthorizationError("insufficient admin role for this action")
        return actor

    return dependency
