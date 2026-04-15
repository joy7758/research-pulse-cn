"""Inbound official-account callback ingress routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_digest_service,
    get_official_account_oauth_service,
)
from research_pulse_cn.core.errors import ConflictError, NotFoundError, ValidationFailedError
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.official_account_oauth import OfficialAccountOAuthService

router = APIRouter(prefix="/integrations/wechat/official-account", tags=["integrations"])
DigestServiceDep = Annotated[DigestService, Depends(get_digest_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OAuthServiceDep = Annotated[
    OfficialAccountOAuthService,
    Depends(get_official_account_oauth_service),
]


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


@router.get("/oauth/callback")
def complete_official_account_oauth_callback(
    request: Request,
    service: OAuthServiceDep,
    audit_service: AuditServiceDep,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
):
    request_id = getattr(request.state, "request_id", None)
    try:
        result = service.complete_callback(code=code or "", state=state or "")
    except (ConflictError, NotFoundError, ValidationFailedError) as exc:
        session = None if not state else service.get_safe_session_for_state(state)
        audit_service.safe_record(
            actor=ActorContext(
                actor_type=AuditActorType.SERVICE,
                actor_label="official_account_oauth_callback",
                is_active=True,
            ),
            action="official_account_oauth.callback_failed",
            resource_type="official_account_binding_handshake_session",
            resource_id=None if session is None else str(session["id"]),
            request_id=request_id,
            route=request.url.path,
            method=request.method,
            status_code=409 if isinstance(exc, ConflictError) else 422,
            metadata={
                "session_id": None if session is None else str(session["id"]),
                "action_result": "failed",
            },
        )
        redirect_url = (service.settings.official_account_oauth_failure_redirect_url or "").strip()
        if redirect_url:
            return RedirectResponse(
                url=f"{redirect_url}?status=failed",
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            )
        payload = {
            "action": "failed",
            "detail": str(exc),
            "session": session,
        }
        if isinstance(exc, ConflictError):
            response_status = 409
        elif isinstance(exc, NotFoundError):
            response_status = 404
        else:
            response_status = 422
        return JSONResponse(status_code=response_status, content=jsonable_encoder(payload))

    audit_service.safe_record(
        actor=ActorContext(
            actor_type=AuditActorType.SERVICE,
            actor_label="official_account_oauth_callback",
            is_active=True,
        ),
        action="official_account_oauth.callback_completed",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(result["session"]["id"]),
        request_id=request_id,
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "user_id": str(result["session"]["user_id"]),
            "claimed_binding_id": str(result["claimed_binding"]["id"]),
            "callback_event_id": (
                None
                if result["callback_event"] is None
                else str(result["callback_event"]["callback_event_id"])
            ),
        },
    )
    redirect_url = (service.settings.official_account_oauth_success_redirect_url or "").strip()
    if redirect_url:
        return RedirectResponse(
            url=f"{redirect_url}?status=claimed",
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return JSONResponse(status_code=200, content=jsonable_encoder(result))
