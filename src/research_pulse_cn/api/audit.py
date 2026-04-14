"""API-layer audit helpers."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.services.audit import AuditService


def audit_request_action(
    *,
    audit_service: AuditService,
    request: Request,
    actor: ActorContext,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status_code: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist a best-effort audit record for an API action."""
    audit_service.safe_record(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=status_code,
        metadata=metadata,
    )
