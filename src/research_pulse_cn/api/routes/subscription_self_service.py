"""User-side self-service reserve routes for subscription controls."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_official_account_binding_handshake_service,
    get_subscription_self_service_service,
)
from research_pulse_cn.api.subscription_self_service_security import (
    get_current_subscription_self_service_grant,
)
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.domain.subscription_self_service import (
    SubscriptionSelfServiceGrantContext,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionSelfServiceBootstrapResponse,
    SubscriptionSelfServiceDeliveryControlPreviewRead,
    SubscriptionSelfServiceHandshakeBootstrapResponse,
    SubscriptionSelfServiceHandshakeSessionCreateRequest,
    SubscriptionSelfServiceHandshakeSessionIssueResponse,
    SubscriptionSelfServiceHandshakeSessionResponse,
    SubscriptionSelfServiceSettingsPatchRequest,
    SubscriptionSelfServiceSettingsRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.official_account_binding_handshake import (
    OfficialAccountBindingHandshakeService,
)
from research_pulse_cn.services.subscription_self_service import (
    SubscriptionSelfServiceService,
)

router = APIRouter(prefix="/subscription-self-service", tags=["subscription-self-service"])
SelfServiceDep = Annotated[
    SubscriptionSelfServiceService,
    Depends(get_subscription_self_service_service),
]
HandshakeDep = Annotated[
    OfficialAccountBindingHandshakeService,
    Depends(get_official_account_binding_handshake_service),
]
GrantDep = Annotated[
    SubscriptionSelfServiceGrantContext,
    Depends(get_current_subscription_self_service_grant),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


def _self_service_actor(grant: SubscriptionSelfServiceGrantContext) -> ActorContext:
    return ActorContext(
        actor_type=AuditActorType.ANONYMOUS,
        actor_label=f"subscription_self_service:{grant.grant_id}",
        is_active=True,
    )


@router.get("/bootstrap", response_model=SubscriptionSelfServiceBootstrapResponse)
def subscription_self_service_bootstrap(
    grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSelfServiceBootstrapResponse:
    return SubscriptionSelfServiceBootstrapResponse(**service.bootstrap(grant))


@router.get("/settings", response_model=SubscriptionSelfServiceSettingsRead)
def get_subscription_self_service_settings(
    grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSelfServiceSettingsRead:
    return SubscriptionSelfServiceSettingsRead(**service.get_settings(grant))


@router.patch("/settings", response_model=SubscriptionSelfServiceSettingsRead)
def patch_subscription_self_service_settings(
    payload: SubscriptionSelfServiceSettingsPatchRequest,
    request: Request,
    grant: GrantDep,
    service: SelfServiceDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceSettingsRead:
    explicit_fields = set(payload.model_fields_set)
    settings = service.patch_settings(
        grant,
        enabled=payload.enabled,
        quiet_hours=payload.quiet_hours,
        timezone=payload.timezone,
        allowed_weekdays=payload.allowed_weekdays,
        muted_until=payload.muted_until,
        minimum_selected_cards=payload.minimum_selected_cards,
        skip_if_no_today_focus=payload.skip_if_no_today_focus,
        update_fields=explicit_fields,
    )
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.settings_patch",
        resource_type="subscription_policy",
        resource_id=(
            None
            if settings["subscription_policy_id"] is None
            else str(settings["subscription_policy_id"])
        ),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
            "updated_fields": sorted(explicit_fields),
        },
    )
    return SubscriptionSelfServiceSettingsRead(**settings)


@router.get(
    "/delivery-control-preview",
    response_model=SubscriptionSelfServiceDeliveryControlPreviewRead,
)
def get_subscription_self_service_delivery_control_preview(
    grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSelfServiceDeliveryControlPreviewRead:
    return SubscriptionSelfServiceDeliveryControlPreviewRead(
        **service.get_delivery_control_preview(grant)
    )


@router.get(
    "/wechat-binding-reserve/bootstrap",
    response_model=SubscriptionSelfServiceHandshakeBootstrapResponse,
)
def subscription_self_service_wechat_binding_reserve_bootstrap(
    grant: GrantDep,
    service: HandshakeDep,
) -> SubscriptionSelfServiceHandshakeBootstrapResponse:
    return SubscriptionSelfServiceHandshakeBootstrapResponse(
        **service.self_service_bootstrap(
            grant_id=grant.grant_id,
            user_id=grant.user_id,
            binding_id=grant.binding_id,
        )
    )


@router.post(
    "/wechat-binding-reserve/session",
    response_model=SubscriptionSelfServiceHandshakeSessionIssueResponse,
    status_code=201,
)
def create_subscription_self_service_wechat_binding_session(
    payload: SubscriptionSelfServiceHandshakeSessionCreateRequest,
    request: Request,
    grant: GrantDep,
    service: HandshakeDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceHandshakeSessionIssueResponse:
    session, issued = service.create_self_service_session(
        grant_id=grant.grant_id,
        user_id=grant.user_id,
        app_id=payload.app_id,
        display_label=payload.display_label,
    )
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.binding_handshake_session_create",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(session.id),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
        },
    )
    return SubscriptionSelfServiceHandshakeSessionIssueResponse(
        session=service.serialize_session(session),
        plain_text_state_token=issued.plain_text_state_token,
        expires_at=issued.expires_at,
    )


@router.get(
    "/wechat-binding-reserve/session",
    response_model=SubscriptionSelfServiceHandshakeSessionResponse,
)
def get_subscription_self_service_wechat_binding_session(
    grant: GrantDep,
    service: HandshakeDep,
) -> SubscriptionSelfServiceHandshakeSessionResponse:
    return SubscriptionSelfServiceHandshakeSessionResponse(
        session=service.get_self_service_session(
            grant_id=grant.grant_id,
            user_id=grant.user_id,
        )
    )


@router.post(
    "/wechat-binding-reserve/session/cancel",
    response_model=SubscriptionSelfServiceHandshakeSessionResponse,
)
def cancel_subscription_self_service_wechat_binding_session(
    request: Request,
    grant: GrantDep,
    service: HandshakeDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceHandshakeSessionResponse:
    session = service.cancel_self_service_session(
        grant_id=grant.grant_id,
        user_id=grant.user_id,
    )
    if session is not None:
        audit_service.safe_record(
            actor=_self_service_actor(grant),
            action="subscription_self_service.binding_handshake_session_cancel",
            resource_type="official_account_binding_handshake_session",
            resource_id=str(session["id"]),
            request_id=getattr(request.state, "request_id", None),
            route=request.url.path,
            method=request.method,
            status_code=200,
            metadata={
                "grant_id": str(grant.grant_id),
                "user_id": str(grant.user_id),
                "channel": grant.channel.value,
            },
        )
    return SubscriptionSelfServiceHandshakeSessionResponse(session=session)
