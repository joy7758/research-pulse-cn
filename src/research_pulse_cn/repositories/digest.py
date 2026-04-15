"""Repositories for WeChat bindings, digest issues, items, and publication jobs."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    DigestPublicationAttempt,
    DigestPublicationJob,
    OfficialAccountCallbackEvent,
    PulseDigestIssue,
    PulseDigestItem,
    WeChatIdentityBinding,
)
from research_pulse_cn.domain.enums import (
    DigestPublicationAttemptStatus,
    DigestPublicationStatus,
    DigestPublicationTarget,
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

    def add_callback_event(
        self,
        event: OfficialAccountCallbackEvent,
    ) -> OfficialAccountCallbackEvent:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

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
        linked_binding_id: UUID | None = None,
        processing_status: OfficialAccountCallbackProcessingStatus | None = None,
        signature_valid: bool | None = None,
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
        if linked_binding_id is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.linked_binding_id == linked_binding_id
            )
        if processing_status is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.processing_status == processing_status
            )
        if signature_valid is not None:
            statement = statement.where(
                OfficialAccountCallbackEvent.signature_valid.is_(signature_valid)
            )
        return list(self.session.scalars(statement))
