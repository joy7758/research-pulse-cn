"""Repositories for WeChat bindings, digest issues, items, and publication jobs."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    DigestDeliveryDecision,
    DigestDispatchRun,
    DigestPublicationAttempt,
    DigestPublicationJob,
    OfficialAccountBindingHandshakeSession,
    OfficialAccountCallbackEvent,
    PulseDigestIssue,
    PulseDigestItem,
    WeChatIdentityBinding,
)
from research_pulse_cn.domain.enums import (
    ChannelType,
    DigestDeliveryDecisionStatus,
    DigestDispatchMode,
    DigestDispatchRunStatus,
    DigestPublicationAttemptStatus,
    DigestPublicationStatus,
    DigestPublicationTarget,
    OfficialAccountBindingHandshakeSessionStatus,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
    PulseDigestIssueStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
)


class DigestRepository:
    """Persistence operations for digest reserve objects."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_bindings(
        self,
        *,
        user_id: UUID | None = None,
        channel_type: WeChatBindingChannelType | None = None,
        subscribed: bool | None = None,
        digest_enabled: bool | None = None,
    ) -> list[WeChatIdentityBinding]:
        statement = (
            select(WeChatIdentityBinding)
            .options(selectinload(WeChatIdentityBinding.user))
            .order_by(WeChatIdentityBinding.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(WeChatIdentityBinding.user_id == user_id)
        if channel_type is not None:
            statement = statement.where(WeChatIdentityBinding.channel_type == channel_type)
        if subscribed is not None:
            statement = statement.where(WeChatIdentityBinding.subscribed.is_(subscribed))
        if digest_enabled is not None:
            statement = statement.where(WeChatIdentityBinding.digest_enabled.is_(digest_enabled))
        return list(self.session.scalars(statement))

    def get_binding(self, binding_id: UUID) -> WeChatIdentityBinding | None:
        statement = (
            select(WeChatIdentityBinding)
            .options(selectinload(WeChatIdentityBinding.user))
            .where(WeChatIdentityBinding.id == binding_id)
        )
        return self.session.scalar(statement)

    def add_binding(self, binding: WeChatIdentityBinding) -> WeChatIdentityBinding:
        self.session.add(binding)
        self.session.flush()
        self.session.refresh(binding)
        return binding

    def get_binding_by_channel_app_openid(
        self,
        *,
        channel_type: WeChatBindingChannelType,
        app_id: str,
        openid: str,
    ) -> WeChatIdentityBinding | None:
        statement = (
            select(WeChatIdentityBinding)
            .options(selectinload(WeChatIdentityBinding.user))
            .where(
                WeChatIdentityBinding.channel_type == channel_type,
                WeChatIdentityBinding.app_id == app_id,
                WeChatIdentityBinding.openid == openid,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_active_official_account_bindings(
        self,
        *,
        user_id: UUID,
    ) -> list[WeChatIdentityBinding]:
        statement = (
            select(WeChatIdentityBinding)
            .where(
                WeChatIdentityBinding.user_id == user_id,
                WeChatIdentityBinding.channel_type == WeChatBindingChannelType.OFFICIAL_ACCOUNT,
                WeChatIdentityBinding.bind_state == WeChatBindingState.ACTIVE,
                WeChatIdentityBinding.subscribed.is_(True),
                WeChatIdentityBinding.digest_enabled.is_(True),
            )
            .order_by(WeChatIdentityBinding.created_at.asc(), WeChatIdentityBinding.id.asc())
        )
        return list(self.session.scalars(statement))

    def list_digest_issues(
        self,
        *,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        status: PulseDigestIssueStatus | None = None,
    ) -> list[PulseDigestIssue]:
        statement = (
            select(PulseDigestIssue)
            .options(
                selectinload(PulseDigestIssue.items).selectinload(PulseDigestItem.source_paper),
                selectinload(PulseDigestIssue.publication_jobs),
                selectinload(PulseDigestIssue.user),
                selectinload(PulseDigestIssue.source_pulse_job),
            )
            .order_by(PulseDigestIssue.issue_date.desc(), PulseDigestIssue.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(PulseDigestIssue.user_id == user_id)
        if issue_date is not None:
            statement = statement.where(PulseDigestIssue.issue_date == issue_date)
        if status is not None:
            statement = statement.where(PulseDigestIssue.status == status)
        return list(self.session.scalars(statement))

    def get_digest_issue(self, digest_issue_id: UUID) -> PulseDigestIssue | None:
        statement = (
            select(PulseDigestIssue)
            .options(
                selectinload(PulseDigestIssue.items).selectinload(PulseDigestItem.source_paper),
                selectinload(PulseDigestIssue.publication_jobs).selectinload(
                    DigestPublicationJob.binding
                ),
                selectinload(PulseDigestIssue.dispatch_runs).selectinload(
                    DigestDispatchRun.attempts
                ),
                selectinload(PulseDigestIssue.user),
                selectinload(PulseDigestIssue.source_pulse_job),
            )
            .where(PulseDigestIssue.id == digest_issue_id)
        )
        return self.session.scalar(statement)

    def get_digest_issue_for_user_date(
        self,
        *,
        user_id: UUID,
        issue_date: date,
    ) -> PulseDigestIssue | None:
        statement = (
            select(PulseDigestIssue)
            .options(
                selectinload(PulseDigestIssue.items).selectinload(PulseDigestItem.source_paper),
                selectinload(PulseDigestIssue.publication_jobs).selectinload(
                    DigestPublicationJob.binding
                ),
                selectinload(PulseDigestIssue.dispatch_runs),
                selectinload(PulseDigestIssue.source_pulse_job),
            )
            .where(
                PulseDigestIssue.user_id == user_id,
                PulseDigestIssue.issue_date == issue_date,
            )
        )
        return self.session.scalar(statement)

    def add_digest_issue(self, digest_issue: PulseDigestIssue) -> PulseDigestIssue:
        self.session.add(digest_issue)
        self.session.flush()
        self.session.refresh(digest_issue)
        return digest_issue

    def list_publication_jobs(
        self,
        *,
        digest_issue_id: UUID | None = None,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        status: DigestPublicationStatus | None = None,
    ) -> list[DigestPublicationJob]:
        statement = (
            select(DigestPublicationJob)
            .join(PulseDigestIssue, DigestPublicationJob.digest_issue_id == PulseDigestIssue.id)
            .options(
                selectinload(DigestPublicationJob.digest_issue),
                selectinload(DigestPublicationJob.binding),
                selectinload(DigestPublicationJob.attempts),
            )
            .order_by(DigestPublicationJob.created_at.desc())
        )
        if digest_issue_id is not None:
            statement = statement.where(DigestPublicationJob.digest_issue_id == digest_issue_id)
        if user_id is not None:
            statement = statement.where(PulseDigestIssue.user_id == user_id)
        if issue_date is not None:
            statement = statement.where(PulseDigestIssue.issue_date == issue_date)
        if status is not None:
            statement = statement.where(DigestPublicationJob.status == status)
        return list(self.session.scalars(statement))

    def get_publication_job_by_id(self, publication_job_id: UUID) -> DigestPublicationJob | None:
        statement = (
            select(DigestPublicationJob)
            .options(
                selectinload(DigestPublicationJob.digest_issue).selectinload(
                    PulseDigestIssue.items
                ),
                selectinload(DigestPublicationJob.binding),
                selectinload(DigestPublicationJob.attempts),
            )
            .where(DigestPublicationJob.id == publication_job_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_publication_job(
        self,
        *,
        digest_issue_id: UUID,
        binding_id: UUID | None,
        publish_target: DigestPublicationTarget,
    ) -> DigestPublicationJob | None:
        statement = (
            select(DigestPublicationJob)
            .where(
                DigestPublicationJob.digest_issue_id == digest_issue_id,
                DigestPublicationJob.binding_id == binding_id,
                DigestPublicationJob.publish_target == publish_target,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_publication_job(self, job: DigestPublicationJob) -> DigestPublicationJob:
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job

    def add_publication_attempt(
        self,
        attempt: DigestPublicationAttempt,
    ) -> DigestPublicationAttempt:
        self.session.add(attempt)
        self.session.flush()
        self.session.refresh(attempt)
        return attempt

    def add_delivery_decision(
        self,
        decision: DigestDeliveryDecision,
    ) -> DigestDeliveryDecision:
        self.session.add(decision)
        self.session.flush()
        self.session.refresh(decision)
        return decision

    def list_publication_attempts(
        self,
        *,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        publication_job_id: UUID | None = None,
        status: DigestPublicationAttemptStatus | None = None,
        provider_mode: OfficialAccountProviderMode | None = None,
    ) -> list[DigestPublicationAttempt]:
        statement = (
            select(DigestPublicationAttempt)
            .join(
                DigestPublicationJob,
                DigestPublicationAttempt.digest_publication_job_id == DigestPublicationJob.id,
            )
            .join(PulseDigestIssue, DigestPublicationJob.digest_issue_id == PulseDigestIssue.id)
            .options(
                selectinload(DigestPublicationAttempt.digest_publication_job).selectinload(
                    DigestPublicationJob.digest_issue
                ),
                selectinload(DigestPublicationAttempt.digest_publication_job).selectinload(
                    DigestPublicationJob.binding
                ),
                selectinload(DigestPublicationAttempt.dispatch_run),
            )
            .order_by(
                DigestPublicationAttempt.started_at.desc(),
                DigestPublicationAttempt.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(PulseDigestIssue.user_id == user_id)
        if issue_date is not None:
            statement = statement.where(PulseDigestIssue.issue_date == issue_date)
        if publication_job_id is not None:
            statement = statement.where(
                DigestPublicationAttempt.digest_publication_job_id == publication_job_id
            )
        if status is not None:
            statement = statement.where(DigestPublicationAttempt.status == status)
        if provider_mode is not None:
            statement = statement.where(DigestPublicationAttempt.provider_mode == provider_mode)
        return list(self.session.scalars(statement))

    def get_latest_publication_attempt(
        self,
        *,
        publication_job_id: UUID,
    ) -> DigestPublicationAttempt | None:
        statement = (
            select(DigestPublicationAttempt)
            .where(DigestPublicationAttempt.digest_publication_job_id == publication_job_id)
            .order_by(
                DigestPublicationAttempt.attempt_number.desc(),
                DigestPublicationAttempt.started_at.desc(),
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_dispatch_run(
        self,
        dispatch_run: DigestDispatchRun,
    ) -> DigestDispatchRun:
        self.session.add(dispatch_run)
        self.session.flush()
        self.session.refresh(dispatch_run)
        return dispatch_run

    def list_delivery_decisions(
        self,
        *,
        user_id: UUID | None = None,
        digest_issue_id: UUID | None = None,
        channel: ChannelType | None = None,
        decision: DigestDeliveryDecisionStatus | None = None,
    ) -> list[DigestDeliveryDecision]:
        statement = (
            select(DigestDeliveryDecision)
            .options(
                selectinload(DigestDeliveryDecision.digest_issue),
                selectinload(DigestDeliveryDecision.subscription_policy),
                selectinload(DigestDeliveryDecision.dispatch_run),
                selectinload(DigestDeliveryDecision.user),
            )
            .order_by(
                DigestDeliveryDecision.created_at.desc(),
                DigestDeliveryDecision.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(DigestDeliveryDecision.user_id == user_id)
        if digest_issue_id is not None:
            statement = statement.where(DigestDeliveryDecision.digest_issue_id == digest_issue_id)
        if channel is not None:
            statement = statement.where(DigestDeliveryDecision.channel == channel)
        if decision is not None:
            statement = statement.where(DigestDeliveryDecision.decision == decision)
        return list(self.session.scalars(statement))

    def list_dispatch_runs(
        self,
        *,
        user_id: UUID | None = None,
        digest_issue_id: UUID | None = None,
        status: DigestDispatchRunStatus | None = None,
        dispatch_mode: DigestDispatchMode | None = None,
        publish_target: DigestPublicationTarget | None = None,
    ) -> list[DigestDispatchRun]:
        statement = (
            select(DigestDispatchRun)
            .options(
                selectinload(DigestDispatchRun.digest_issue),
                selectinload(DigestDispatchRun.user),
                selectinload(DigestDispatchRun.attempts).selectinload(
                    DigestPublicationAttempt.digest_publication_job
                ),
            )
            .order_by(DigestDispatchRun.created_at.desc(), DigestDispatchRun.id.desc())
        )
        if user_id is not None:
            statement = statement.where(DigestDispatchRun.user_id == user_id)
        if digest_issue_id is not None:
            statement = statement.where(DigestDispatchRun.digest_issue_id == digest_issue_id)
        if status is not None:
            statement = statement.where(DigestDispatchRun.status == status)
        if dispatch_mode is not None:
            statement = statement.where(DigestDispatchRun.dispatch_mode == dispatch_mode)
        if publish_target is not None:
            statement = statement.where(DigestDispatchRun.publish_target == publish_target)
        return list(self.session.scalars(statement))

    def get_dispatch_run(self, dispatch_run_id: UUID) -> DigestDispatchRun | None:
        statement = (
            select(DigestDispatchRun)
            .options(
                selectinload(DigestDispatchRun.digest_issue),
                selectinload(DigestDispatchRun.user),
                selectinload(DigestDispatchRun.attempts).selectinload(
                    DigestPublicationAttempt.digest_publication_job
                ),
            )
            .where(DigestDispatchRun.id == dispatch_run_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_running_dispatch_run(
        self,
        *,
        digest_issue_id: UUID,
        publish_target: DigestPublicationTarget,
    ) -> DigestDispatchRun | None:
        statement = (
            select(DigestDispatchRun)
            .where(
                DigestDispatchRun.digest_issue_id == digest_issue_id,
                DigestDispatchRun.publish_target == publish_target,
                DigestDispatchRun.status == DigestDispatchRunStatus.RUNNING,
            )
            .order_by(DigestDispatchRun.started_at.desc(), DigestDispatchRun.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_callback_event(
        self,
        event: OfficialAccountCallbackEvent,
    ) -> OfficialAccountCallbackEvent:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def get_callback_event(self, callback_event_id: UUID) -> OfficialAccountCallbackEvent | None:
        statement = (
            select(OfficialAccountCallbackEvent)
            .options(selectinload(OfficialAccountCallbackEvent.linked_binding))
            .where(OfficialAccountCallbackEvent.id == callback_event_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_callback_event_by_dedupe_key(
        self,
        dedupe_key: str,
    ) -> OfficialAccountCallbackEvent | None:
        statement = (
            select(OfficialAccountCallbackEvent)
            .options(selectinload(OfficialAccountCallbackEvent.linked_binding))
            .where(OfficialAccountCallbackEvent.dedupe_key == dedupe_key)
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_callback_events(
        self,
        *,
        user_id: UUID | None = None,
        app_id: str | None = None,
        linked_binding_id: UUID | None = None,
        processing_status: OfficialAccountCallbackProcessingStatus | None = None,
        event_type: str | None = None,
        signature_valid: bool | None = None,
        unmatched_only: bool = False,
        created_after: datetime | None = None,
    ) -> list[OfficialAccountCallbackEvent]:
        statement = (
            select(OfficialAccountCallbackEvent)
            .options(selectinload(OfficialAccountCallbackEvent.linked_binding))
            .order_by(
                OfficialAccountCallbackEvent.created_at.desc(),
                OfficialAccountCallbackEvent.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.join(
                WeChatIdentityBinding,
                OfficialAccountCallbackEvent.linked_binding_id == WeChatIdentityBinding.id,
            ).where(WeChatIdentityBinding.user_id == user_id)
        if app_id is not None:
            statement = statement.where(OfficialAccountCallbackEvent.app_id == app_id)
        if linked_binding_id is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.linked_binding_id == linked_binding_id
            )
        if unmatched_only:
            statement = statement.where(OfficialAccountCallbackEvent.linked_binding_id.is_(None))
        if processing_status is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.processing_status == processing_status
            )
        if event_type is not None:
            statement = statement.where(OfficialAccountCallbackEvent.event_type == event_type)
        if signature_valid is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.signature_valid.is_(signature_valid)
            )
        if created_after is not None:
            statement = statement.where(OfficialAccountCallbackEvent.created_at >= created_after)
        return list(self.session.scalars(statement))

    def add_handshake_session(
        self,
        handshake_session: OfficialAccountBindingHandshakeSession,
    ) -> OfficialAccountBindingHandshakeSession:
        self.session.add(handshake_session)
        self.session.flush()
        self.session.refresh(handshake_session)
        return handshake_session

    def get_handshake_session(
        self,
        session_id: UUID,
    ) -> OfficialAccountBindingHandshakeSession | None:
        statement = (
            select(OfficialAccountBindingHandshakeSession)
            .options(
                selectinload(OfficialAccountBindingHandshakeSession.user),
                selectinload(OfficialAccountBindingHandshakeSession.self_service_grant),
                selectinload(OfficialAccountBindingHandshakeSession.issued_by_admin),
                selectinload(OfficialAccountBindingHandshakeSession.matched_callback_event),
                selectinload(OfficialAccountBindingHandshakeSession.claimed_binding),
            )
            .where(OfficialAccountBindingHandshakeSession.id == session_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_handshake_sessions(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: OfficialAccountBindingHandshakeSessionStatus | None = None,
        self_service_grant_id: UUID | None = None,
        app_id: str | None = None,
    ) -> list[OfficialAccountBindingHandshakeSession]:
        statement = (
            select(OfficialAccountBindingHandshakeSession)
            .options(
                selectinload(OfficialAccountBindingHandshakeSession.user),
                selectinload(OfficialAccountBindingHandshakeSession.self_service_grant),
                selectinload(OfficialAccountBindingHandshakeSession.issued_by_admin),
                selectinload(OfficialAccountBindingHandshakeSession.matched_callback_event),
                selectinload(OfficialAccountBindingHandshakeSession.claimed_binding),
            )
            .order_by(
                OfficialAccountBindingHandshakeSession.created_at.desc(),
                OfficialAccountBindingHandshakeSession.id.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(OfficialAccountBindingHandshakeSession.user_id == user_id)
        if channel is not None:
            statement = statement.where(OfficialAccountBindingHandshakeSession.channel == channel)
        if status is not None:
            statement = statement.where(OfficialAccountBindingHandshakeSession.status == status)
        if self_service_grant_id is not None:
            statement = statement.where(
                OfficialAccountBindingHandshakeSession.self_service_grant_id
                == self_service_grant_id
            )
        if app_id is not None:
            statement = statement.where(OfficialAccountBindingHandshakeSession.app_id == app_id)
        return list(self.session.scalars(statement))
