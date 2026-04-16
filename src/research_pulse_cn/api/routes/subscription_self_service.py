"""User-side self-service reserve routes for subscription controls."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_group_workspace_service,
    get_official_account_binding_handshake_service,
    get_official_account_oauth_service,
    get_subscription_self_service_service,
)
from research_pulse_cn.api.subscription_self_service_security import (
    get_current_subscription_self_service_grant,
)
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType, GroupWorkspaceResultCollectStatus
from research_pulse_cn.domain.subscription_self_service import (
    SubscriptionSelfServiceGrantContext,
)
from research_pulse_cn.schemas.group_workspace import (
    GroupWorkspaceInviteClaimPreviewRead,
    GroupWorkspaceInviteClaimResponse,
    GroupWorkspaceMembershipSummaryRead,
    GroupWorkspaceResultCollectionRead,
    ResultShareCollectPreviewRead,
    ResultShareCollectRequest,
    ResultShareCollectResponse,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionSelfServiceBootstrapResponse,
    SubscriptionSelfServiceDeliveryControlPreviewRead,
    SubscriptionSelfServiceEditorBootstrapRead,
    SubscriptionSelfServiceEditorContractRead,
    SubscriptionSelfServiceHandshakeBootstrapResponse,
    SubscriptionSelfServiceHandshakeSessionCreateRequest,
    SubscriptionSelfServiceHandshakeSessionIssueResponse,
    SubscriptionSelfServiceHandshakeSessionResponse,
    SubscriptionSelfServiceOAuthStartRequest,
    SubscriptionSelfServiceOAuthStartResponse,
    SubscriptionSelfServiceOAuthStatusResponse,
    SubscriptionSelfServiceSettingsPatchRequest,
    SubscriptionSelfServiceSettingsRead,
    SubscriptionSettingsPreviewRead,
    SubscriptionSettingsSaveResultRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.group_workspace import GroupWorkspaceService
from research_pulse_cn.services.official_account_binding_handshake import (
    OfficialAccountBindingHandshakeService,
)
from research_pulse_cn.services.official_account_oauth import OfficialAccountOAuthService
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
OAuthDep = Annotated[
    OfficialAccountOAuthService,
    Depends(get_official_account_oauth_service),
]
WorkspaceServiceDep = Annotated[
    GroupWorkspaceService,
    Depends(get_group_workspace_service),
]


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


@router.get(
    "/editor-bootstrap",
    response_model=SubscriptionSelfServiceEditorBootstrapRead,
)
def get_subscription_self_service_editor_bootstrap(
    grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSelfServiceEditorBootstrapRead:
    return SubscriptionSelfServiceEditorBootstrapRead(**service.get_editor_bootstrap(grant))


@router.get(
    "/editor-contract",
    response_model=SubscriptionSelfServiceEditorContractRead,
)
def get_subscription_self_service_editor_contract(
    _grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSelfServiceEditorContractRead:
    return SubscriptionSelfServiceEditorContractRead(**service.get_editor_contract())


@router.post(
    "/settings/preview",
    response_model=SubscriptionSettingsPreviewRead,
)
def preview_subscription_self_service_settings(
    payload: SubscriptionSelfServiceSettingsPatchRequest,
    grant: GrantDep,
    service: SelfServiceDep,
) -> SubscriptionSettingsPreviewRead:
    preview = service.preview_settings(
        grant,
        payload=payload.model_dump(exclude_unset=True),
    )
    return SubscriptionSettingsPreviewRead(**preview)


@router.patch(
    "/settings",
    response_model=SubscriptionSelfServiceSettingsRead | SubscriptionSettingsSaveResultRead,
)
def patch_subscription_self_service_settings(
    payload: SubscriptionSelfServiceSettingsPatchRequest,
    request: Request,
    grant: GrantDep,
    service: SelfServiceDep,
    audit_service: AuditServiceDep,
    include_preview: bool = Query(default=False),
) -> SubscriptionSelfServiceSettingsRead | SubscriptionSettingsSaveResultRead:
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
        include_preview=include_preview,
    )
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.settings_patch",
        resource_type="subscription_policy",
        resource_id=(
            None
            if (
                settings.get("subscription_policy_id") is None
                and settings.get("saved_settings", {}).get("subscription_policy_id") is None
            )
            else str(
                settings.get("subscription_policy_id")
                or settings["saved_settings"]["subscription_policy_id"]
            )
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
    if include_preview:
        return SubscriptionSettingsSaveResultRead(**settings)
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


@router.post(
    "/wechat-binding-reserve/oauth-start",
    response_model=SubscriptionSelfServiceOAuthStartResponse,
)
def start_subscription_self_service_wechat_binding_oauth(
    payload: SubscriptionSelfServiceOAuthStartRequest,
    request: Request,
    grant: GrantDep,
    service: OAuthDep,
    audit_service: AuditServiceDep,
) -> SubscriptionSelfServiceOAuthStartResponse:
    result = service.start_self_service_oauth(
        grant_id=grant.grant_id,
        user_id=grant.user_id,
        app_id=payload.app_id,
        display_label=payload.display_label,
        requested_scope=payload.requested_scope,
    )
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.binding_handshake_oauth_start",
        resource_type="official_account_binding_handshake_session",
        resource_id=str(result["session"]["id"]),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
            "requested_scope": result["requested_scope"].value,
        },
    )
    return SubscriptionSelfServiceOAuthStartResponse(**result)


@router.get(
    "/wechat-binding-reserve/oauth-status",
    response_model=SubscriptionSelfServiceOAuthStatusResponse,
)
def get_subscription_self_service_wechat_binding_oauth_status(
    grant: GrantDep,
    service: OAuthDep,
) -> SubscriptionSelfServiceOAuthStatusResponse:
    return SubscriptionSelfServiceOAuthStatusResponse(
        **service.self_service_oauth_status(
            grant_id=grant.grant_id,
            user_id=grant.user_id,
        )
    )


@router.get(
    "/workspace-invites/{invite_token}/claim-preview",
    response_model=GroupWorkspaceInviteClaimPreviewRead,
)
def preview_subscription_self_service_workspace_invite_claim(
    invite_token: str,
    request: Request,
    grant: GrantDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceInviteClaimPreviewRead:
    payload = service.preview_invite_claim(raw_token=invite_token, grant=grant)
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.workspace_invite_claim_preview",
        resource_type="group_workspace_invite_grant",
        resource_id=None if payload["invite"] is None else str(payload["invite"]["id"]),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "workspace_id": (
                None if payload["workspace"] is None else str(payload["workspace"]["id"])
            ),
            "reason_codes": payload["reason_codes"],
            "can_claim": payload["can_claim"],
        },
    )
    return GroupWorkspaceInviteClaimPreviewRead(**payload)


@router.post(
    "/workspace-invites/{invite_token}/claim",
    response_model=GroupWorkspaceInviteClaimResponse,
)
def claim_subscription_self_service_workspace_invite(
    invite_token: str,
    request: Request,
    grant: GrantDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceInviteClaimResponse:
    payload = service.claim_workspace_invite(raw_token=invite_token, grant=grant)
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.workspace_invite_claim",
        resource_type="group_workspace_invite_grant",
        resource_id=None if payload["invite"] is None else str(payload["invite"]["id"]),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "workspace_id": (
                None if payload["workspace"] is None else str(payload["workspace"]["id"])
            ),
            "action": payload["action"],
            "invite_claim_id": (
                None if payload["invite_claim"] is None else str(payload["invite_claim"]["id"])
            ),
        },
    )
    return GroupWorkspaceInviteClaimResponse(**payload)


@router.get(
    "/workspace-memberships",
    response_model=list[GroupWorkspaceMembershipSummaryRead],
)
def list_subscription_self_service_workspace_memberships(
    grant: GrantDep,
    service: WorkspaceServiceDep,
) -> list[GroupWorkspaceMembershipSummaryRead]:
    return [
        GroupWorkspaceMembershipSummaryRead(**membership)
        for membership in service.self_service_workspace_memberships(user_id=grant.user_id)
    ]


@router.get(
    "/result-shares/{share_token}/collect-preview",
    response_model=ResultShareCollectPreviewRead,
)
def preview_subscription_self_service_result_share_collect(
    share_token: str,
    request: Request,
    grant: GrantDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareCollectPreviewRead:
    payload = service.preview_result_share_collect(raw_token=share_token, grant=grant)
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.result_share_collect_preview",
        resource_type="result_share_grant",
        resource_id=None if payload["share"] is None else str(payload["share"]["id"]),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "reason_codes": payload["reason_codes"],
            "can_collect": payload["can_collect"],
        },
    )
    return ResultShareCollectPreviewRead(**payload)


@router.post(
    "/result-shares/{share_token}/collect",
    response_model=ResultShareCollectResponse,
)
def collect_subscription_self_service_result_share(
    share_token: str,
    payload: ResultShareCollectRequest,
    request: Request,
    grant: GrantDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareCollectResponse:
    response_payload = service.collect_result_share(
        raw_token=share_token,
        grant=grant,
        workspace_id=payload.workspace_id,
        paper_ids=payload.paper_ids,
    )
    audit_service.safe_record(
        actor=_self_service_actor(grant),
        action="subscription_self_service.result_share_collect",
        resource_type="result_share_grant",
        resource_id=(
            None
            if not response_payload["collected_results"]
            else str(
                response_payload["collected_results"][0]["collect_record"]["result_share_grant_id"]
            )
            if response_payload["collected_results"][0]["collect_record"] is not None
            else None
        ),
        request_id=getattr(request.state, "request_id", None),
        route=request.url.path,
        method=request.method,
        status_code=200,
        metadata={
            "grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "workspace_id": (
                None
                if response_payload["workspace"] is None
                else str(response_payload["workspace"]["id"])
            ),
            "action": response_payload["action"],
            "result_count": len(response_payload["collected_results"]),
        },
    )
    return ResultShareCollectResponse(**response_payload)


@router.get(
    "/workspace-result-collections",
    response_model=list[GroupWorkspaceResultCollectionRead],
)
def list_subscription_self_service_workspace_result_collections(
    grant: GrantDep,
    service: WorkspaceServiceDep,
    workspace_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[GroupWorkspaceResultCollectStatus | None, Query()] = None,
) -> list[GroupWorkspaceResultCollectionRead]:
    return [
        GroupWorkspaceResultCollectionRead(**item)
        for item in service.self_service_workspace_result_collections(
            user_id=grant.user_id,
            workspace_id=workspace_id,
            status=status,
        )
    ]
