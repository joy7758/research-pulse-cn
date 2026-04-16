"""Short-lived handoff-grant routes for subscription editor access."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from research_pulse_cn.api.dependencies import (
    get_audit_service,
    get_subscription_editor_handoff_service,
)
from research_pulse_cn.api.subscription_editor_security import (
    get_current_subscription_editor_handoff_grant,
)
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.domain.subscription_self_service import (
    SubscriptionEditorHandoffGrantContext,
)
from research_pulse_cn.schemas.subscription_self_service import (
    SubscriptionEditorBootstrapRead,
    SubscriptionSelfServiceEditorContractRead,
    SubscriptionSelfServiceSettingsPatchRequest,
    SubscriptionSelfServiceSettingsRead,
    SubscriptionSettingsPreviewRead,
    SubscriptionSettingsSaveResultRead,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.subscription_editor_handoff import (
    SubscriptionEditorHandoffService,
)

router = APIRouter(prefix="/subscription-editor", tags=["subscription-editor"])
EditorServiceDep = Annotated[
    SubscriptionEditorHandoffService,
    Depends(get_subscription_editor_handoff_service),
]
EditorGrantDep = Annotated[
    SubscriptionEditorHandoffGrantContext,
    Depends(get_current_subscription_editor_handoff_grant),
]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


def _editor_handoff_actor(grant: SubscriptionEditorHandoffGrantContext) -> ActorContext:
    return ActorContext(
        actor_type=AuditActorType.ANONYMOUS,
        actor_label=f"subscription_editor_handoff:{grant.grant_id}",
        is_active=True,
    )


@router.get("/bootstrap", response_model=SubscriptionEditorBootstrapRead)
def get_subscription_editor_bootstrap(
    grant: EditorGrantDep,
    service: EditorServiceDep,
) -> SubscriptionEditorBootstrapRead:
    return SubscriptionEditorBootstrapRead(**service.get_editor_bootstrap(grant))


@router.get("/contract", response_model=SubscriptionSelfServiceEditorContractRead)
def get_subscription_editor_contract(
    _grant: EditorGrantDep,
    service: EditorServiceDep,
) -> SubscriptionSelfServiceEditorContractRead:
    return SubscriptionSelfServiceEditorContractRead(**service.get_editor_contract())


@router.post("/settings/preview", response_model=SubscriptionSettingsPreviewRead)
def preview_subscription_editor_settings(
    payload: SubscriptionSelfServiceSettingsPatchRequest,
    grant: EditorGrantDep,
    service: EditorServiceDep,
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
def patch_subscription_editor_settings(
    payload: SubscriptionSelfServiceSettingsPatchRequest,
    request: Request,
    grant: EditorGrantDep,
    service: EditorServiceDep,
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
        actor=_editor_handoff_actor(grant),
        action="subscription_editor_handoff.settings_patch",
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
            "handoff_grant_id": str(grant.grant_id),
            "user_id": str(grant.user_id),
            "channel": grant.channel.value,
            "updated_fields": sorted(explicit_fields),
        },
    )
    if include_preview:
        return SubscriptionSettingsSaveResultRead(**settings)
    return SubscriptionSelfServiceSettingsRead(**settings)
