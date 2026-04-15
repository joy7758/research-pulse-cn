"""Admin routes for WeChat bindings and digest reserve workflows."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_digest_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.core.errors import ConflictError
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    DigestPublicationAttemptStatus,
    DigestPublicationMode,
    DigestPublicationStatus,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
    PulseDigestIssueStatus,
    SyncEventSource,
    WeChatBindingChannelType,
)
from research_pulse_cn.schemas.digest import (
    DigestIssueBuildRequest,
    DigestIssueBuildResponse,
    DigestPublicationAttemptRead,
    DigestPublicationDispatchResponse,
    DigestPublicationJobRead,
    DigestPublicationPrepareResponse,
    OfficialAccountCallbackEventRead,
    OfficialAccountProviderStatusRead,
    OfficialAccountProviderTokenRefreshResponse,
    PulseDigestIssueDetailRead,
    PulseDigestIssueRead,
    WeChatIdentityBindingCreate,
    WeChatIdentityBindingRead,
    WeChatIdentityBindingUpdate,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.digest import DigestService

router = APIRouter(prefix="/admin", tags=["admin"])
DigestServiceDep = Annotated[DigestService, Depends(get_digest_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]
ChannelTypeQuery = Annotated[WeChatBindingChannelType | None, Query()]
DigestEnabledQuery = Annotated[bool | None, Query()]
SubscribedQuery = Annotated[bool | None, Query()]
IssueDateQuery = Annotated[date | None, Query()]


@router.get("/wechat-bindings", response_model=list[WeChatIdentityBindingRead])
def list_wechat_bindings(
    _actor: OperatorDep,
    service: DigestServiceDep,
    user_id: UserIdQuery = None,
    channel_type: ChannelTypeQuery = None,
    subscribed: SubscribedQuery = None,
    digest_enabled: DigestEnabledQuery = None,
) -> list[WeChatIdentityBindingRead]:
    return [
        WeChatIdentityBindingRead.model_validate(binding)
        for binding in service.list_bindings(
            user_id=user_id,
            channel_type=channel_type,
            subscribed=subscribed,
            digest_enabled=digest_enabled,
        )
    ]


@router.post(
    "/wechat-bindings",
    response_model=WeChatIdentityBindingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_wechat_binding(
    payload: WeChatIdentityBindingCreate,
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
) -> WeChatIdentityBindingRead:
    binding = service.create_binding(
        user_id=payload.user_id,
        channel_type=payload.channel_type,
        app_id=payload.app_id,
        openid=payload.openid,
        unionid=payload.unionid,
        bind_state=payload.bind_state,
        subscribed=payload.subscribed,
        digest_enabled=payload.digest_enabled,
        display_label=payload.display_label,
        subscribed_at=payload.subscribed_at,
        unsubscribed_at=payload.unsubscribed_at,
        last_seen_at=payload.last_seen_at,
        metadata=payload.metadata,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="wechat_binding.create",
        resource_type="wechat_binding",
        resource_id=str(binding.id),
        status_code=201,
        metadata={
            "user_id": str(binding.user_id),
            "channel_type": binding.channel_type.value,
            "subscribed": binding.subscribed,
            "digest_enabled": binding.digest_enabled,
        },
    )
    return WeChatIdentityBindingRead.model_validate(binding)


@router.patch("/wechat-bindings/{binding_id}", response_model=WeChatIdentityBindingRead)
def update_wechat_binding(
    binding_id: UUID,
    payload: WeChatIdentityBindingUpdate,
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
) -> WeChatIdentityBindingRead:
    binding = service.update_binding(
        binding_id,
        unionid=payload.unionid,
        bind_state=payload.bind_state,
        subscribed=payload.subscribed,
        digest_enabled=payload.digest_enabled,
        display_label=payload.display_label,
        subscribed_at=payload.subscribed_at,
        unsubscribed_at=payload.unsubscribed_at,
        last_seen_at=payload.last_seen_at,
        metadata=payload.metadata,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="wechat_binding.update",
        resource_type="wechat_binding",
        resource_id=str(binding.id),
        status_code=200,
        metadata={
            "bind_state": binding.bind_state.value,
            "subscribed": binding.subscribed,
            "digest_enabled": binding.digest_enabled,
        },
    )
    return WeChatIdentityBindingRead.model_validate(binding)


@router.get("/digest-issues", response_model=list[PulseDigestIssueRead])
def list_digest_issues(
    _actor: OperatorDep,
    service: DigestServiceDep,
    user_id: UserIdQuery = None,
    issue_date: IssueDateQuery = None,
    status: Annotated[PulseDigestIssueStatus | None, Query()] = None,
) -> list[PulseDigestIssueRead]:
    return [
        PulseDigestIssueRead.model_validate(issue)
        for issue in service.list_digest_issues(
            user_id=user_id,
            issue_date=issue_date,
            status=status,
        )
    ]


@router.get("/digest-issues/{digest_issue_id}", response_model=PulseDigestIssueDetailRead)
def get_digest_issue(
    digest_issue_id: UUID,
    _actor: OperatorDep,
    service: DigestServiceDep,
) -> PulseDigestIssueDetailRead:
    return PulseDigestIssueDetailRead.model_validate(service.get_digest_issue(digest_issue_id))


@router.post("/digest-issues/build/{user_id}", response_model=DigestIssueBuildResponse)
def build_digest_issue(
    user_id: UUID,
    payload: DigestIssueBuildRequest,
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
) -> DigestIssueBuildResponse:
    result = service.build_issue(
        user_id=user_id,
        issue_date=payload.issue_date,
        source_pulse_job_id=payload.source_pulse_job_id,
        event_source=SyncEventSource.API,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="digest_issue.build",
        resource_type="pulse_digest_issue",
        resource_id=str(result.issue.id),
        status_code=200,
        metadata={
            "user_id": str(user_id),
            "issue_date": result.issue.issue_date.isoformat(),
            "action_result": result.action,
            "status": result.issue.status.value,
            "source_pulse_job_id": (
                None
                if result.issue.source_pulse_job_id is None
                else str(result.issue.source_pulse_job_id)
            ),
        },
    )
    return DigestIssueBuildResponse(
        action=result.action,
        issue=PulseDigestIssueDetailRead.model_validate(result.issue),
    )


@router.post(
    "/digest-issues/{digest_issue_id}/prepare-publication",
    response_model=DigestPublicationPrepareResponse,
)
def prepare_digest_publication(
    digest_issue_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
) -> DigestPublicationPrepareResponse:
    jobs = service.prepare_publication(
        digest_issue_id,
        publish_mode=DigestPublicationMode.MANUAL_PREVIEW,
    )
    issue = service.get_digest_issue(digest_issue_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="digest_publication.prepare",
        resource_type="pulse_digest_issue",
        resource_id=str(issue.id),
        status_code=200,
        metadata={
            "prepared_jobs": len(jobs),
            "publish_mode": DigestPublicationMode.MANUAL_PREVIEW.value,
        },
    )
    return DigestPublicationPrepareResponse(
        issue=PulseDigestIssueDetailRead.model_validate(issue),
        publication_jobs=[DigestPublicationJobRead.model_validate(job) for job in jobs],
    )


@router.get("/digest-publication-jobs", response_model=list[DigestPublicationJobRead])
def list_digest_publication_jobs(
    _actor: OperatorDep,
    service: DigestServiceDep,
    digest_issue_id: Annotated[UUID | None, Query()] = None,
    user_id: UserIdQuery = None,
    issue_date: IssueDateQuery = None,
    status: Annotated[DigestPublicationStatus | None, Query()] = None,
) -> list[DigestPublicationJobRead]:
    return [
        DigestPublicationJobRead.model_validate(job)
        for job in service.list_publication_jobs(
            digest_issue_id=digest_issue_id,
            user_id=user_id,
            issue_date=issue_date,
            status=status,
        )
    ]


@router.post(
    "/digest-publication-jobs/{publication_job_id}/dispatch",
    response_model=DigestPublicationDispatchResponse,
)
def dispatch_digest_publication_job(
    publication_job_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
    force: Annotated[bool, Query()] = False,
) -> DigestPublicationDispatchResponse:
    try:
        result = service.dispatch_publication_job(publication_job_id, force=force)
    except ConflictError:
        audit_request_action(
            audit_service=audit_service,
            request=request,
            actor=actor,
            action="digest_publication.dispatch",
            resource_type="digest_publication_job",
            resource_id=str(publication_job_id),
            status_code=409,
            metadata={"action_result": "conflict"},
        )
        raise
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="digest_publication.dispatch",
        resource_type="digest_publication_job",
        resource_id=str(result.publication_job.id),
        status_code=200,
        metadata={
            "action_result": result.action,
            "publication_job_status": result.publication_job.status.value,
            "attempt_id": None if result.attempt is None else str(result.attempt.id),
            "force": force,
        },
    )
    return DigestPublicationDispatchResponse(
        action=result.action,
        publication_job=DigestPublicationJobRead.model_validate(result.publication_job),
        attempt=(
            None
            if result.attempt is None
            else DigestPublicationAttemptRead(
                **service.serialize_publication_attempt(result.attempt)
            )
        ),
    )


@router.get("/digest-publication-attempts", response_model=list[DigestPublicationAttemptRead])
def list_digest_publication_attempts(
    _actor: OperatorDep,
    service: DigestServiceDep,
    publication_job_id: Annotated[UUID | None, Query()] = None,
    user_id: UserIdQuery = None,
    issue_date: IssueDateQuery = None,
    status: Annotated[DigestPublicationAttemptStatus | None, Query()] = None,
    provider_mode: Annotated[OfficialAccountProviderMode | None, Query()] = None,
) -> list[DigestPublicationAttemptRead]:
    return [
        DigestPublicationAttemptRead(**service.serialize_publication_attempt(attempt))
        for attempt in service.list_publication_attempts(
            publication_job_id=publication_job_id,
            user_id=user_id,
            issue_date=issue_date,
            status=status,
            provider_mode=provider_mode,
        )
    ]


@router.get(
    "/official-account/provider-status",
    response_model=OfficialAccountProviderStatusRead,
)
def official_account_provider_status(
    _actor: OperatorDep,
    service: DigestServiceDep,
) -> OfficialAccountProviderStatusRead:
    return OfficialAccountProviderStatusRead(**service.provider_status())


@router.post(
    "/official-account/provider-token/refresh",
    response_model=OfficialAccountProviderTokenRefreshResponse,
)
def refresh_official_account_provider_token(
    request: Request,
    actor: OperatorDep,
    service: DigestServiceDep,
    audit_service: AuditServiceDep,
) -> OfficialAccountProviderTokenRefreshResponse:
    try:
        result = service.refresh_provider_token()
    except ConflictError:
        audit_request_action(
            audit_service=audit_service,
            request=request,
            actor=actor,
            action="official_account.provider_token_refresh",
            resource_type="official_account_provider",
            status_code=409,
            metadata={"action_result": "conflict"},
        )
        raise
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="official_account.provider_token_refresh",
        resource_type="official_account_provider",
        status_code=200,
        metadata={
            "action_result": result["action"],
            "cache_backend": result["cache_backend"],
            "token_cached": result["token_cached"],
        },
    )
    return OfficialAccountProviderTokenRefreshResponse(**result)


@router.get(
    "/official-account/callback-events",
    response_model=list[OfficialAccountCallbackEventRead],
)
def list_official_account_callback_events(
    _actor: OperatorDep,
    service: DigestServiceDep,
    user_id: UserIdQuery = None,
    linked_binding_id: Annotated[UUID | None, Query()] = None,
    processing_status: Annotated[OfficialAccountCallbackProcessingStatus | None, Query()] = None,
    signature_valid: Annotated[bool | None, Query()] = None,
) -> list[OfficialAccountCallbackEventRead]:
    return [
        OfficialAccountCallbackEventRead(**service.serialize_callback_event(event))
        for event in service.list_callback_events(
            user_id=user_id,
            linked_binding_id=linked_binding_id,
            processing_status=processing_status,
            signature_valid=signature_valid,
        )
    ]
