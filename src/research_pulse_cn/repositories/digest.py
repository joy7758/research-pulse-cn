"""Repositories for WeChat bindings, digest issues, items, and publication jobs."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    DigestPublicationJob,
    PulseDigestIssue,
    WeChatIdentityBinding,
)
from research_pulse_cn.domain.enums import (
    DigestPublicationStatus,
    DigestPublicationTarget,
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
                selectinload(PulseDigestIssue.items),
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
                selectinload(PulseDigestIssue.items),
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
                selectinload(PulseDigestIssue.items),
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
        status: DigestPublicationStatus | None = None,
    ) -> list[DigestPublicationJob]:
        statement = (
            select(DigestPublicationJob)
            .join(PulseDigestIssue, DigestPublicationJob.digest_issue_id == PulseDigestIssue.id)
            .options(
                selectinload(DigestPublicationJob.digest_issue),
                selectinload(DigestPublicationJob.binding),
            )
            .order_by(DigestPublicationJob.created_at.desc())
        )
        if digest_issue_id is not None:
            statement = statement.where(DigestPublicationJob.digest_issue_id == digest_issue_id)
        if user_id is not None:
            statement = statement.where(PulseDigestIssue.user_id == user_id)
        if status is not None:
            statement = statement.where(DigestPublicationJob.status == status)
        return list(self.session.scalars(statement))

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
