"""Inbound official-account callback ingress routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import PlainTextResponse

from research_pulse_cn.api.dependencies import get_audit_service, get_digest_service
from research_pulse_cn.core.errors import ConflictError
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.digest import DigestService

router = APIRouter(prefix="/integrations/wechat/official-account", tags=["integrations"])
DigestServiceDep = Annotated[DigestService, Depends(get_digest_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


@router.get("/callback", response_class=PlainTextResponse)
async def verify_official_account_callback(
    service: DigestServiceDep,
    echostr: Annotated[str, Query()],
    signature: Annotated[str | None, Query()] = None,
    timestamp: Annotated[str | None, Query()] = None,
    nonce: Annotated[str | None, Query()] = None,
) -> PlainTextResponse:
    if not service.settings.official_account_callback_enabled:
        return PlainTextResponse(
            "official-account callback handling is disabled",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    try:
        challenge = service.verify_callback_handshake(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            echostr=echostr,
        )
    except ConflictError:
        return PlainTextResponse("invalid signature", status_code=status.HTTP_403_FORBIDDEN)
    return PlainTextResponse(challenge)


@router.post("/callback", response_class=PlainTextResponse)
async def ingest_official_account_callback(
    request: Request,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
    signature: Annotated[str | None, Query()] = None,
    timestamp: Annotated[str | None, Query()] = None,
    nonce: Annotated[str | None, Query()] = None,
) -> PlainTextResponse:
    if not service.settings.official_account_callback_enabled:
        return PlainTextResponse(
            "official-account callback handling is disabled",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    raw_payload = (await request.body()).decode("utf-8", errors="replace")
    result = service.ingest_callback(
        raw_payload=raw_payload,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )
    if result.binding_updated and result.linked_binding is not None:
        audit_service.safe_record(
            actor=ActorContext(
                actor_type=AuditActorType.SERVICE,
                actor_label="official_account_callback",
                is_active=True,
            ),
            action="wechat_binding.subscription_update",
            resource_type="wechat_binding",
            resource_id=str(result.linked_binding.id),
            request_id=getattr(request.state, "request_id", None),
            route=request.url.path,
            method=request.method,
            status_code=200,
            metadata={
                "subscribed": result.linked_binding.subscribed,
                "action_result": result.action,
                "callback_event_id": str(result.callback_event.id),
            },
        )

    if result.action == "signature_invalid":
        return PlainTextResponse("invalid signature", status_code=status.HTTP_403_FORBIDDEN)
    return PlainTextResponse("success")
