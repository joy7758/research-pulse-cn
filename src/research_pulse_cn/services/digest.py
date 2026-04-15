"""Digest issue building, WeChat binding management, and publication preparation."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from xml.etree import ElementTree
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import ConflictError, NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    DigestDeliveryDecision,
    DigestDispatchRun,
    DigestPublicationAttempt,
    DigestPublicationJob,
    OfficialAccountCallbackEvent,
    PulseCard,
    PulseDigestIssue,
    PulseDigestItem,
    PulseJob,
    SubscriptionPolicy,
    UserProfile,
    WeChatIdentityBinding,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ChannelType,
    DigestDeliveryDecisionStatus,
    DigestDispatchMode,
    DigestDispatchRunStatus,
    DigestPublicationAttemptStatus,
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    OfficialAccountCallbackPayloadFormat,
    OfficialAccountCallbackProcessingStatus,
    OfficialAccountProviderMode,
    PulseCardType,
    PulseDigestIssueStatus,
    PulseJobStatus,
    SyncEventSource,
    SyncEventType,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.official_account import (
    OfficialAccountAccessTokenService,
    OfficialAccountPublisher,
    OfficialAccountPublishResult,
    build_official_account_payload,
    build_provider_status,
    get_official_account_publisher,
)
from research_pulse_cn.services.subscription_policy import (
    find_matching_delivery_policy,
    normalize_delivery_control_policy,
)
from research_pulse_cn.services.sync_events import SyncEventService

logger = logging.getLogger(__name__)

DAILY_DIGEST_SECTION_ORDER = (
    "today_focus",
    "yesterday_recap",
    "signal_updates",
    "related_papers",
    "other_updates",
)
DAILY_DIGEST_SECTION_TITLES = {
    "today_focus": "Today Focus",
    "yesterday_recap": "Yesterday Recap",
    "signal_updates": "Signal Updates",
    "related_papers": "Related Papers",
    "other_updates": "Other Updates",
}


@dataclass(slots=True)
class DigestBuildResult:
    issue: PulseDigestIssue
    action: str


@dataclass(slots=True)
class DispatchPublicationResult:
    action: str
    publication_job: DigestPublicationJob
    attempt: DigestPublicationAttempt | None


@dataclass(slots=True)
class DigestIssueDispatchPreview:
    issue: PulseDigestIssue
    provider_status: dict[str, Any]
    delivery_control_preview: DigestDeliveryControlPreview
    total_publication_jobs: int
    eligible_jobs: list[DigestPublicationJob]
    already_sent_jobs: list[DigestPublicationJob]
    failed_jobs: list[DigestPublicationJob]
    skipped_reasons: list[str]
    would_prepare: bool
    retry_failed: bool
    force_prepare: bool


@dataclass(slots=True)
class DigestDispatchRunResult:
    action: str
    issue: PulseDigestIssue
    dispatch_run: DigestDispatchRun | None
    delivery_decision: DigestDeliveryDecision | None
    publication_jobs: list[DigestPublicationJob]


@dataclass(slots=True)
class CallbackIngestResult:
    callback_event: OfficialAccountCallbackEvent
    action: str
    binding_updated: bool
    linked_binding: WeChatIdentityBinding | None


@dataclass(slots=True)
class DigestDeliveryControlPreview:
    issue: PulseDigestIssue
    matched_subscription_policy: SubscriptionPolicy | None
    normalized_control_policy: dict[str, Any]
    current_local_time: datetime
    local_weekday: int
    decision: DigestDeliveryDecisionStatus
    reason_codes: list[str]
    next_allowed_at: datetime | None
    quiet_hours: dict[str, Any] | None
    muted_until: datetime | None
    focus_card_type: str | None


class DigestService:
    """Manage future official-account digest reserve objects."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider=None,
        official_account_publisher: OfficialAccountPublisher | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = DigestRepository(session)
        self.user_repository = UserRepository(session)
        self.pulse_repository = PulseRepository(session)
        self.subscription_policy_repository = SubscriptionPolicyRepository(session)
        self.sync_events = SyncEventService(session)
        self.metrics = get_metrics()
        self.official_account_access_token_service = OfficialAccountAccessTokenService(
            self.settings,
            metrics=self.metrics,
            now_provider=self.now_provider,
        )
        self.official_account_publisher = (
            official_account_publisher
            or get_official_account_publisher(
                self.settings,
                access_token_service=self.official_account_access_token_service,
            )
        )

    def list_bindings(
        self,
        *,
        user_id: UUID | None = None,
        channel_type: WeChatBindingChannelType | None = None,
        subscribed: bool | None = None,
        digest_enabled: bool | None = None,
    ) -> list[WeChatIdentityBinding]:
        return self.repository.list_bindings(
            user_id=user_id,
            channel_type=channel_type,
            subscribed=subscribed,
            digest_enabled=digest_enabled,
        )

    def get_binding(self, binding_id: UUID) -> WeChatIdentityBinding:
        binding = self.repository.get_binding(binding_id)
        if binding is None:
            raise NotFoundError(f"wechat binding {binding_id} was not found")
        return binding

    def create_binding(
        self,
        *,
        user_id: UUID,
        channel_type: WeChatBindingChannelType,
        app_id: str,
        openid: str,
        unionid: str | None = None,
        bind_state: WeChatBindingState = WeChatBindingState.PENDING,
        subscribed: bool = False,
        digest_enabled: bool = True,
        display_label: str | None = None,
        subscribed_at: datetime | None = None,
        unsubscribed_at: datetime | None = None,
        last_seen_at: datetime | None = None,
        metadata: dict | None = None,
        auto_commit: bool = True,
    ) -> WeChatIdentityBinding:
        self._require_user(user_id)
        binding = WeChatIdentityBinding(
            user_id=user_id,
            channel_type=channel_type,
            app_id=app_id,
            openid=openid,
            unionid=unionid,
            bind_state=bind_state,
            subscribed=subscribed,
            digest_enabled=digest_enabled,
            display_label=display_label,
            subscribed_at=subscribed_at,
            unsubscribed_at=unsubscribed_at,
            last_seen_at=last_seen_at,
            metadata_json=dict(metadata or {}) or None,
        )
        self.repository.add_binding(binding)
        if auto_commit:
            commit_session(self.session)
            return self.get_binding(binding.id)
        return binding

    def update_binding(
        self,
        binding_id: UUID,
        *,
        unionid: str | None = None,
        bind_state: WeChatBindingState | None = None,
        subscribed: bool | None = None,
        digest_enabled: bool | None = None,
        display_label: str | None = None,
        subscribed_at: datetime | None = None,
        unsubscribed_at: datetime | None = None,
        last_seen_at: datetime | None = None,
        metadata: dict | None = None,
        auto_commit: bool = True,
    ) -> WeChatIdentityBinding:
        binding = self.get_binding(binding_id)
        if unionid is not None:
            binding.unionid = unionid
        if bind_state is not None:
            binding.bind_state = bind_state
        if subscribed is not None:
            binding.subscribed = subscribed
        if digest_enabled is not None:
            binding.digest_enabled = digest_enabled
        if display_label is not None:
            binding.display_label = display_label
        if subscribed_at is not None:
            binding.subscribed_at = subscribed_at
        if unsubscribed_at is not None:
            binding.unsubscribed_at = unsubscribed_at
        if last_seen_at is not None:
            binding.last_seen_at = last_seen_at
        if metadata is not None:
            binding.metadata_json = dict(metadata)
        if auto_commit:
            commit_session(self.session)
            return self.get_binding(binding.id)
        return binding

    def list_digest_issues(
        self,
        *,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        status: PulseDigestIssueStatus | None = None,
    ) -> list[PulseDigestIssue]:
        return self.repository.list_digest_issues(
            user_id=user_id,
            issue_date=issue_date,
            status=status,
        )

    def get_digest_issue(self, digest_issue_id: UUID) -> PulseDigestIssue:
        issue = self.repository.get_digest_issue(digest_issue_id)
        if issue is None:
            raise NotFoundError(f"digest issue {digest_issue_id} was not found")
        return issue

    def build_issue(
        self,
        *,
        user_id: UUID,
        issue_date: date | None = None,
        source_pulse_job_id: UUID | None = None,
        event_source: SyncEventSource,
        auto_commit: bool = True,
    ) -> DigestBuildResult:
        user = self._require_user(user_id)
        source_job = self._resolve_source_job(
            user=user,
            issue_date=issue_date,
            source_pulse_job_id=source_pulse_job_id,
        )
        effective_issue_date = issue_date or self._resolve_issue_date(user, source_job)
        ordered_cards = self._resolve_cards_for_build(
            user_id=user.id,
            issue_date=effective_issue_date,
            source_job=source_job,
        )
        result = self._upsert_issue(
            user=user,
            issue_date=effective_issue_date,
            source_job=source_job,
            ordered_cards=ordered_cards,
            event_source=event_source,
            auto_commit=auto_commit,
        )
        return result

    def build_issue_from_cards(
        self,
        *,
        user_id: UUID,
        source_job: PulseJob | None,
        ordered_cards: Sequence[PulseCard],
        event_source: SyncEventSource,
        auto_commit: bool = True,
    ) -> DigestBuildResult:
        user = self._require_user(user_id)
        effective_issue_date = self._resolve_issue_date(user, source_job)
        return self._upsert_issue(
            user=user,
            issue_date=effective_issue_date,
            source_job=source_job,
            ordered_cards=list(ordered_cards),
            event_source=event_source,
            auto_commit=auto_commit,
        )

    def prepare_publication(
        self,
        digest_issue_id: UUID,
        *,
        publish_mode: DigestPublicationMode = DigestPublicationMode.MANUAL_PREVIEW,
        auto_commit: bool = True,
    ) -> list[DigestPublicationJob]:
        issue = self.get_digest_issue(digest_issue_id)
        eligible_bindings = self.repository.list_active_official_account_bindings(
            user_id=issue.user_id
        )
        eligible_binding_ids = {binding.id for binding in eligible_bindings}

        with bind_log_context(digest_issue_id=issue.id, user_id=issue.user_id):
            for existing in issue.publication_jobs:
                if existing.binding_id is None or existing.binding_id in eligible_binding_ids:
                    continue
                existing.status = DigestPublicationStatus.SKIPPED
                existing.last_error = "binding no longer eligible for digest publication"

            prepared_jobs: list[DigestPublicationJob] = []
            for binding in eligible_bindings:
                job = self.repository.get_publication_job(
                    digest_issue_id=issue.id,
                    binding_id=binding.id,
                    publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
                )
                if job is None:
                    job = DigestPublicationJob(
                        digest_issue_id=issue.id,
                        binding_id=binding.id,
                        publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
                    )
                    self.repository.add_publication_job(job)
                job.publish_mode = publish_mode
                job.provider_name = "official_account_boundary"
                job.status = DigestPublicationStatus.PREPARED
                job.payload = build_official_account_payload(
                    publication_job=job,
                    issue=issue,
                    binding=binding,
                    settings=self.settings,
                )
                job.last_error = None
                job.prepared_at = self.now_provider()
                prepared_jobs.append(job)
                self.metrics.increment("digest_publication_jobs_prepared_total")

            if prepared_jobs:
                self.metrics.increment("daily_digest_publication_prepared_total")

            if auto_commit:
                commit_session(self.session)
            logger.info(
                "digest publication prepared",
                extra={"prepared_jobs": len(prepared_jobs)},
            )
        return self.repository.list_publication_jobs(digest_issue_id=issue.id)

    def get_daily_preview(self, digest_issue_id: UUID) -> dict[str, Any]:
        issue = self.get_digest_issue(digest_issue_id)
        content_payload = dict(issue.content_payload or {})
        publication_preview = content_payload.get("publication_preview")
        return {
            "issue": issue,
            "content_payload": content_payload,
            "publication_preview": (
                None if not isinstance(publication_preview, dict) else publication_preview
            ),
        }

    def get_dispatch_preview(
        self,
        digest_issue_id: UUID,
        *,
        retry_failed: bool = False,
        force_prepare: bool = False,
    ) -> DigestIssueDispatchPreview:
        issue = self.get_digest_issue(digest_issue_id)
        provider_status = self.provider_status()
        delivery_control_preview = self.get_delivery_control_preview(digest_issue_id)
        publication_jobs = [
            job
            for job in issue.publication_jobs
            if job.publish_target == DigestPublicationTarget.OFFICIAL_ACCOUNT
        ]
        effective_retry_failed = retry_failed or self.settings.digest_dispatch_retry_failed_jobs
        would_prepare = bool(
            not publication_jobs
            and (force_prepare or self.settings.digest_dispatch_prepare_if_missing)
        )
        eligible_jobs = self._select_dispatch_eligible_jobs(
            publication_jobs,
            retry_failed=effective_retry_failed,
        )
        already_sent_jobs = [
            job for job in publication_jobs if job.status == DigestPublicationStatus.SENT
        ]
        failed_jobs = [
            job for job in publication_jobs if job.status == DigestPublicationStatus.FAILED
        ]
        skipped_reasons: list[str] = []
        running_run = self.repository.get_running_dispatch_run(
            digest_issue_id=issue.id,
            publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
        )
        if running_run is not None:
            skipped_reasons.append("an official-account dispatch run is already in progress")
        if provider_status["mode"] == OfficialAccountProviderMode.DISABLED:
            skipped_reasons.append("official-account provider mode is disabled")
        elif (
            provider_status["mode"] == OfficialAccountProviderMode.REAL
            and not provider_status["readiness"]
        ):
            skipped_reasons.append(
                "official-account provider is not ready: "
                + "; ".join(provider_status["readiness_failures"])
            )
        if not publication_jobs and not would_prepare:
            skipped_reasons.append(
                "no prepared official-account publication jobs exist for this issue"
            )
        if publication_jobs and not eligible_jobs:
            skipped_reasons.append(
                "no eligible official-account publication jobs remain for dispatch"
            )
        if len(eligible_jobs) > self.settings.digest_dispatch_max_publication_jobs_per_run:
            skipped_reasons.append(
                "eligible jobs exceed the per-run cap and will be truncated during dispatch"
            )
        return DigestIssueDispatchPreview(
            issue=issue,
            provider_status=provider_status,
            delivery_control_preview=delivery_control_preview,
            total_publication_jobs=len(publication_jobs),
            eligible_jobs=eligible_jobs[
                : self.settings.digest_dispatch_max_publication_jobs_per_run
            ],
            already_sent_jobs=already_sent_jobs,
            failed_jobs=failed_jobs,
            skipped_reasons=skipped_reasons,
            would_prepare=would_prepare,
            retry_failed=effective_retry_failed,
            force_prepare=force_prepare,
        )

    def get_delivery_control_preview(
        self,
        digest_issue_id: UUID,
        *,
        channel: ChannelType = ChannelType.OFFICIAL_ACCOUNT,
        now: datetime | None = None,
    ) -> DigestDeliveryControlPreview:
        issue = self.get_digest_issue(digest_issue_id)
        current_time = self.now_provider() if now is None else now
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        policy = self._matching_subscription_policy(
            user_id=issue.user_id,
            channel=channel,
        )
        return self._evaluate_delivery_control(
            issue=issue,
            channel=channel,
            policy=policy,
            current_time=current_time,
        )

    def evaluate_delivery_control_for_issue(
        self,
        issue: PulseDigestIssue,
        *,
        channel: ChannelType = ChannelType.OFFICIAL_ACCOUNT,
        policy: SubscriptionPolicy | None = None,
        now: datetime | None = None,
    ) -> DigestDeliveryControlPreview:
        current_time = self.now_provider() if now is None else now
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        effective_policy = policy
        if effective_policy is None:
            effective_policy = self._matching_subscription_policy(
                user_id=issue.user_id,
                channel=channel,
            )
        return self._evaluate_delivery_control(
            issue=issue,
            channel=channel,
            policy=effective_policy,
            current_time=current_time,
        )

    def list_delivery_decisions(
        self,
        *,
        user_id: UUID | None = None,
        digest_issue_id: UUID | None = None,
        channel: ChannelType | None = None,
        decision: DigestDeliveryDecisionStatus | None = None,
    ) -> list[DigestDeliveryDecision]:
        return self.repository.list_delivery_decisions(
            user_id=user_id,
            digest_issue_id=digest_issue_id,
            channel=channel,
            decision=decision,
        )

    def list_dispatch_runs(
        self,
        *,
        user_id: UUID | None = None,
        digest_issue_id: UUID | None = None,
        status: DigestDispatchRunStatus | None = None,
        dispatch_mode: DigestDispatchMode | None = None,
        publish_target: DigestPublicationTarget | None = None,
    ) -> list[DigestDispatchRun]:
        return self.repository.list_dispatch_runs(
            user_id=user_id,
            digest_issue_id=digest_issue_id,
            status=status,
            dispatch_mode=dispatch_mode,
            publish_target=publish_target,
        )

    def get_dispatch_run(self, dispatch_run_id: UUID) -> DigestDispatchRun:
        dispatch_run = self.repository.get_dispatch_run(dispatch_run_id)
        if dispatch_run is None:
            raise NotFoundError(f"digest dispatch run {dispatch_run_id} was not found")
        return dispatch_run

    def serialize_dispatch_run(self, dispatch_run: DigestDispatchRun) -> dict[str, Any]:
        return {
            "id": dispatch_run.id,
            "digest_issue_id": dispatch_run.digest_issue_id,
            "user_id": dispatch_run.user_id,
            "publish_target": dispatch_run.publish_target,
            "dispatch_mode": dispatch_run.dispatch_mode,
            "provider_mode": dispatch_run.provider_mode,
            "status": dispatch_run.status,
            "total_jobs": dispatch_run.total_jobs,
            "eligible_jobs": dispatch_run.eligible_jobs,
            "previewed_jobs": dispatch_run.previewed_jobs,
            "sent_jobs": dispatch_run.sent_jobs,
            "failed_jobs": dispatch_run.failed_jobs,
            "skipped_jobs": dispatch_run.skipped_jobs,
            "started_at": dispatch_run.started_at,
            "finished_at": dispatch_run.finished_at,
            "last_error": dispatch_run.last_error,
            "created_at": dispatch_run.created_at,
            "updated_at": dispatch_run.updated_at,
        }

    def serialize_delivery_decision(
        self,
        delivery_decision: DigestDeliveryDecision,
    ) -> dict[str, Any]:
        return {
            "id": delivery_decision.id,
            "digest_issue_id": delivery_decision.digest_issue_id,
            "user_id": delivery_decision.user_id,
            "channel": delivery_decision.channel,
            "subscription_policy_id": delivery_decision.subscription_policy_id,
            "dispatch_run_id": delivery_decision.dispatch_run_id,
            "decision": delivery_decision.decision,
            "reason_codes": list(delivery_decision.reason_codes or []),
            "effective_timezone": delivery_decision.effective_timezone,
            "local_issue_weekday": delivery_decision.local_issue_weekday,
            "selected_card_count": delivery_decision.selected_card_count,
            "focus_card_type": delivery_decision.focus_card_type,
            "quiet_hours": delivery_decision.quiet_hours,
            "muted_until": delivery_decision.muted_until,
            "next_allowed_at": delivery_decision.next_allowed_at,
            "created_at": delivery_decision.created_at,
        }

    def serialize_delivery_control_preview(
        self,
        preview: DigestDeliveryControlPreview,
    ) -> dict[str, Any]:
        return {
            "issue": {
                "id": preview.issue.id,
                "user_id": preview.issue.user_id,
                "issue_date": preview.issue.issue_date,
                "source_pulse_job_id": preview.issue.source_pulse_job_id,
                "status": preview.issue.status,
                "title": preview.issue.title,
                "summary": preview.issue.summary,
                "highlight_count": preview.issue.highlight_count,
                "selected_card_count": preview.issue.selected_card_count,
                "deep_link_path": preview.issue.deep_link_path,
                "content_payload": preview.issue.content_payload,
                "build_metadata": preview.issue.build_metadata,
                "published_at": preview.issue.published_at,
                "created_at": preview.issue.created_at,
                "updated_at": preview.issue.updated_at,
            },
            "matched_subscription_policy": self._serialize_matched_subscription_policy(
                preview.matched_subscription_policy
            ),
            "normalized_control_policy": dict(preview.normalized_control_policy),
            "current_local_time": preview.current_local_time,
            "local_weekday": preview.local_weekday,
            "decision": preview.decision,
            "reason_codes": list(preview.reason_codes),
            "next_allowed_at": preview.next_allowed_at,
        }

    def dispatch_digest_issue(
        self,
        digest_issue_id: UUID,
        *,
        dispatch_mode: DigestDispatchMode = DigestDispatchMode.MANUAL,
        retry_failed: bool = False,
        force_prepare: bool = False,
        auto_commit: bool = True,
        create_skipped_run_if_no_eligible: bool = True,
    ) -> DigestDispatchRunResult | None:
        issue = self.get_digest_issue(digest_issue_id)
        delivery_preview = self.get_delivery_control_preview(
            digest_issue_id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
        )
        delivery_decision = self._persist_delivery_decision(
            preview=delivery_preview,
            dispatch_run_id=None,
        )
        if delivery_preview.decision == DigestDeliveryDecisionStatus.SKIPPED:
            self.metrics.increment("digest_dispatch_policy_skips_total")
            if auto_commit:
                commit_session(self.session)
                issue = self.get_digest_issue(issue.id)
                delivery_decision = self.repository.list_delivery_decisions(
                    digest_issue_id=issue.id,
                    channel=ChannelType.OFFICIAL_ACCOUNT,
                )[0]
            return DigestDispatchRunResult(
                action="skipped",
                issue=issue,
                dispatch_run=None,
                delivery_decision=delivery_decision,
                publication_jobs=self.list_publication_jobs(digest_issue_id=issue.id),
            )
        result = self._dispatch_digest_issue_allowed(
            digest_issue_id,
            dispatch_mode=dispatch_mode,
            retry_failed=retry_failed,
            force_prepare=force_prepare,
            auto_commit=False,
            create_skipped_run_if_no_eligible=create_skipped_run_if_no_eligible,
        )
        if result is not None and result.dispatch_run is not None:
            delivery_decision.dispatch_run_id = result.dispatch_run.id
        if auto_commit:
            commit_session(self.session)
            issue = self.get_digest_issue(issue.id)
            delivery_decision = self.repository.list_delivery_decisions(
                digest_issue_id=issue.id,
                channel=ChannelType.OFFICIAL_ACCOUNT,
            )[0]
            dispatch_run = None
            if result is not None and result.dispatch_run is not None:
                dispatch_run = self.get_dispatch_run(result.dispatch_run.id)
            return DigestDispatchRunResult(
                action="skipped" if result is None else result.action,
                issue=issue,
                dispatch_run=dispatch_run,
                delivery_decision=delivery_decision,
                publication_jobs=self.list_publication_jobs(digest_issue_id=issue.id),
            )
        if result is not None:
            result.delivery_decision = delivery_decision
        return result

    def _dispatch_digest_issue_allowed(
        self,
        digest_issue_id: UUID,
        *,
        dispatch_mode: DigestDispatchMode = DigestDispatchMode.MANUAL,
        retry_failed: bool = False,
        force_prepare: bool = False,
        auto_commit: bool = True,
        create_skipped_run_if_no_eligible: bool = True,
    ) -> DigestDispatchRunResult | None:
        issue = self.get_digest_issue(digest_issue_id)
        effective_retry_failed = retry_failed or self.settings.digest_dispatch_retry_failed_jobs
        preview = self.get_dispatch_preview(
            digest_issue_id,
            retry_failed=effective_retry_failed,
            force_prepare=force_prepare,
        )
        provider_status = preview.provider_status
        running_run = self.repository.get_running_dispatch_run(
            digest_issue_id=issue.id,
            publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
        )
        if running_run is not None:
            raise ConflictError("an official-account dispatch run is already in progress")
        self._validate_dispatch_provider_mode(
            provider_status=provider_status,
            dispatch_mode=dispatch_mode,
        )

        publication_jobs = [
            job
            for job in issue.publication_jobs
            if job.publish_target == DigestPublicationTarget.OFFICIAL_ACCOUNT
        ]
        if not publication_jobs and preview.would_prepare:
            self.prepare_publication(
                issue.id,
                publish_mode=DigestPublicationMode.MANUAL_PREVIEW,
                auto_commit=False,
            )
            self.session.flush()
            self.session.expire(issue, ["publication_jobs"])
            issue = self.get_digest_issue(issue.id)
            publication_jobs = [
                job
                for job in issue.publication_jobs
                if job.publish_target == DigestPublicationTarget.OFFICIAL_ACCOUNT
            ]

        eligible_jobs = self._select_dispatch_eligible_jobs(
            publication_jobs,
            retry_failed=effective_retry_failed,
        )[: self.settings.digest_dispatch_max_publication_jobs_per_run]
        skipped_count = max(0, len(publication_jobs) - len(eligible_jobs))

        if not eligible_jobs:
            if not create_skipped_run_if_no_eligible:
                return None
            dispatch_run = DigestDispatchRun(
                digest_issue_id=issue.id,
                user_id=issue.user_id,
                publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
                dispatch_mode=dispatch_mode,
                provider_mode=self.settings.official_account_provider_mode,
                status=DigestDispatchRunStatus.SKIPPED,
                total_jobs=len(publication_jobs),
                eligible_jobs=0,
                previewed_jobs=0,
                sent_jobs=0,
                failed_jobs=0,
                skipped_jobs=len(publication_jobs),
                started_at=self.now_provider(),
                finished_at=self.now_provider(),
                last_error=(
                    None if not preview.skipped_reasons else "; ".join(preview.skipped_reasons[:3])
                ),
            )
            self.repository.add_dispatch_run(dispatch_run)
            if auto_commit:
                commit_session(self.session)
                issue = self.get_digest_issue(issue.id)
                dispatch_run = self.get_dispatch_run(dispatch_run.id)
            return DigestDispatchRunResult(
                action="skipped",
                issue=issue,
                dispatch_run=dispatch_run,
                delivery_decision=None,
                publication_jobs=publication_jobs,
            )

        dispatch_run = DigestDispatchRun(
            digest_issue_id=issue.id,
            user_id=issue.user_id,
            publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
            dispatch_mode=dispatch_mode,
            provider_mode=self.settings.official_account_provider_mode,
            status=DigestDispatchRunStatus.RUNNING,
            total_jobs=len(publication_jobs),
            eligible_jobs=len(eligible_jobs),
            previewed_jobs=0,
            sent_jobs=0,
            failed_jobs=0,
            skipped_jobs=skipped_count,
            started_at=self.now_provider(),
        )
        self.repository.add_dispatch_run(dispatch_run)
        self.metrics.increment("digest_dispatch_runs_started_total")

        previewed_jobs = 0
        sent_jobs = 0
        failed_jobs = 0
        last_error: str | None = None

        with bind_log_context(
            digest_issue_id=issue.id,
            dispatch_run_id=dispatch_run.id,
            user_id=issue.user_id,
        ):
            for job in eligible_jobs:
                try:
                    result = self.dispatch_publication_job(
                        job.id,
                        force=True,
                        dispatch_run_id=dispatch_run.id,
                    )
                except (ConflictError, RuntimeError) as exc:
                    failed_jobs += 1
                    last_error = str(exc)
                    logger.warning(
                        "digest publication job failed during issue dispatch",
                        extra={"publication_job_id": str(job.id)},
                    )
                    continue
                if result.action == "sent":
                    sent_jobs += 1
                elif result.action == "previewed":
                    previewed_jobs += 1
                else:
                    failed_jobs += 1
                    last_error = f"unexpected dispatch action: {result.action}"

        dispatch_run.previewed_jobs = previewed_jobs
        dispatch_run.sent_jobs = sent_jobs
        dispatch_run.failed_jobs = failed_jobs
        dispatch_run.last_error = last_error
        dispatch_run.finished_at = self.now_provider()
        dispatch_run.status = self._resolve_dispatch_run_status(
            eligible_jobs=len(eligible_jobs),
            previewed_jobs=previewed_jobs,
            sent_jobs=sent_jobs,
            failed_jobs=failed_jobs,
        )
        if sent_jobs:
            self.metrics.increment("digest_dispatch_jobs_sent_total", sent_jobs)
        if dispatch_run.status == DigestDispatchRunStatus.COMPLETED:
            self.metrics.increment("digest_dispatch_runs_completed_total")
        elif dispatch_run.status in (
            DigestDispatchRunStatus.FAILED,
            DigestDispatchRunStatus.PARTIAL_FAILED,
        ):
            self.metrics.increment("digest_dispatch_runs_failed_total")

        if auto_commit:
            commit_session(self.session)
            issue = self.get_digest_issue(issue.id)
            dispatch_run = self.get_dispatch_run(dispatch_run.id)
        return DigestDispatchRunResult(
            action=dispatch_run.status.value,
            issue=issue,
            dispatch_run=dispatch_run,
            delivery_decision=None,
            publication_jobs=self.list_publication_jobs(digest_issue_id=issue.id),
        )

    def list_publication_jobs(
        self,
        *,
        digest_issue_id: UUID | None = None,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        status: DigestPublicationStatus | None = None,
    ) -> list[DigestPublicationJob]:
        return self.repository.list_publication_jobs(
            digest_issue_id=digest_issue_id,
            user_id=user_id,
            issue_date=issue_date,
            status=status,
        )

    def get_publication_job(self, publication_job_id: UUID) -> DigestPublicationJob:
        job = self.repository.get_publication_job_by_id(publication_job_id)
        if job is None:
            raise NotFoundError(f"digest publication job {publication_job_id} was not found")
        return job

    def list_publication_attempts(
        self,
        *,
        user_id: UUID | None = None,
        issue_date: date | None = None,
        publication_job_id: UUID | None = None,
        status: DigestPublicationAttemptStatus | None = None,
        provider_mode: OfficialAccountProviderMode | None = None,
    ) -> list[DigestPublicationAttempt]:
        return self.repository.list_publication_attempts(
            user_id=user_id,
            issue_date=issue_date,
            publication_job_id=publication_job_id,
            status=status,
            provider_mode=provider_mode,
        )

    def list_callback_events(
        self,
        *,
        user_id: UUID | None = None,
        linked_binding_id: UUID | None = None,
        processing_status: OfficialAccountCallbackProcessingStatus | None = None,
        signature_valid: bool | None = None,
    ) -> list[OfficialAccountCallbackEvent]:
        return self.repository.list_callback_events(
            user_id=user_id,
            linked_binding_id=linked_binding_id,
            processing_status=processing_status,
            signature_valid=signature_valid,
        )

    def provider_status(self) -> dict[str, Any]:
        return build_provider_status(
            self.settings,
            access_token_service=self.official_account_access_token_service,
        )

    def refresh_provider_token(self) -> dict[str, Any]:
        if self.settings.official_account_provider_mode == OfficialAccountProviderMode.DISABLED:
            raise ConflictError("official-account provider mode is disabled")
        if self.settings.official_account_provider_mode == OfficialAccountProviderMode.DRY_RUN:
            snapshot = self.official_account_access_token_service.cache_snapshot()
            return {
                "action": "noop",
                "mode": self.settings.official_account_provider_mode,
                "transport_kind": self.settings.official_account_transport_kind,
                "token_cached": snapshot.token_cached,
                "token_expires_at": snapshot.token_expires_at,
                "last_refresh_at": snapshot.last_refresh_at,
                "cache_backend": snapshot.backend,
            }
        return self.official_account_access_token_service.refresh_summary()

    def serialize_publication_attempt(self, attempt: DigestPublicationAttempt) -> dict[str, Any]:
        job = attempt.digest_publication_job
        return {
            "id": attempt.id,
            "digest_publication_job_id": attempt.digest_publication_job_id,
            "dispatch_run_id": attempt.dispatch_run_id,
            "digest_issue_id": job.digest_issue_id,
            "user_id": job.digest_issue.user_id,
            "binding_id": job.binding_id,
            "attempt_number": attempt.attempt_number,
            "provider_name": attempt.provider_name,
            "provider_mode": attempt.provider_mode,
            "status": attempt.status,
            "request_payload": attempt.request_payload,
            "response_payload": attempt.response_payload,
            "error_summary": attempt.error_summary,
            "external_message_id": attempt.external_message_id,
            "provider_response_code": attempt.provider_response_code,
            "provider_response_message": attempt.provider_response_message,
            "started_at": attempt.started_at,
            "finished_at": attempt.finished_at,
        }

    def serialize_callback_event(self, event: OfficialAccountCallbackEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "app_id": event.app_id,
            "to_user_name": event.to_user_name,
            "from_openid": event.from_openid,
            "msg_type": event.msg_type,
            "event_type": event.event_type,
            "event_key": event.event_key,
            "event_time": event.event_time,
            "dedupe_key": event.dedupe_key,
            "signature_valid": event.signature_valid,
            "payload_format": event.payload_format,
            "raw_payload": event.raw_payload,
            "parsed_payload": event.parsed_payload_json,
            "processing_status": event.processing_status,
            "processing_note": event.processing_note,
            "linked_binding_id": event.linked_binding_id,
            "created_at": event.created_at,
            "processed_at": event.processed_at,
        }

    def dispatch_publication_job(
        self,
        publication_job_id: UUID,
        *,
        force: bool = False,
        dispatch_run_id: UUID | None = None,
    ) -> DispatchPublicationResult:
        job = self.get_publication_job(publication_job_id)
        if job.publish_target != DigestPublicationTarget.OFFICIAL_ACCOUNT:
            raise ConflictError("publication job target is not supported by this dispatcher")
        if job.binding is None:
            raise ConflictError("publication job has no official-account binding")
        if (
            self.settings.official_account_provider_mode == OfficialAccountProviderMode.REAL
            and not force
            and job.status == DigestPublicationStatus.SENT
        ):
            return DispatchPublicationResult(
                action="already_sent",
                publication_job=job,
                attempt=self.repository.get_latest_publication_attempt(publication_job_id=job.id),
            )
        if self.settings.official_account_provider_mode == OfficialAccountProviderMode.REAL:
            self._validate_real_dispatch_binding(job.binding)

        publisher = self.official_account_publisher
        latest_attempt = self.repository.get_latest_publication_attempt(publication_job_id=job.id)
        if (
            self.settings.official_account_provider_mode == OfficialAccountProviderMode.DRY_RUN
            and not force
            and job.status == DigestPublicationStatus.PREVIEWED
            and latest_attempt is not None
            and latest_attempt.status == DigestPublicationAttemptStatus.PREVIEWED
            and latest_attempt.provider_mode == OfficialAccountProviderMode.DRY_RUN
        ):
            return DispatchPublicationResult(
                action="already_previewed",
                publication_job=job,
                attempt=latest_attempt,
            )

        attempt_number = 1 if latest_attempt is None else latest_attempt.attempt_number + 1
        attempt = DigestPublicationAttempt(
            digest_publication_job_id=job.id,
            dispatch_run_id=dispatch_run_id,
            attempt_number=attempt_number,
            provider_name=publisher.provider_name,
            provider_mode=publisher.provider_mode,
            status=DigestPublicationAttemptStatus.STARTED,
            started_at=self.now_provider(),
        )
        self.repository.add_publication_attempt(attempt)
        self.metrics.increment("digest_publication_attempts_created_total")

        with bind_log_context(
            digest_issue_id=job.digest_issue_id,
            publication_job_id=job.id,
            publication_attempt_id=attempt.id,
            user_id=job.digest_issue.user_id,
        ):
            try:
                result = publisher.dispatch(
                    publication_job=job,
                    issue=job.digest_issue,
                    binding=job.binding,
                )
            except ConflictError as exc:
                attempt.status = DigestPublicationAttemptStatus.FAILED
                attempt.error_summary = str(exc)
                attempt.finished_at = self.now_provider()
                job.provider_name = publisher.provider_name
                job.last_error = str(exc)
                job.status = DigestPublicationStatus.FAILED
                self.metrics.increment("digest_publication_attempts_failed_total")
                if self.settings.official_account_provider_mode == OfficialAccountProviderMode.REAL:
                    self.metrics.increment("official_account_real_dispatch_failure_total")
                commit_session(self.session)
                raise
            except Exception as exc:
                attempt.status = DigestPublicationAttemptStatus.FAILED
                attempt.error_summary = str(exc)
                attempt.finished_at = self.now_provider()
                job.provider_name = publisher.provider_name
                job.last_error = "official-account dispatch failed"
                job.status = DigestPublicationStatus.FAILED
                self.metrics.increment("digest_publication_attempts_failed_total")
                if self.settings.official_account_provider_mode == OfficialAccountProviderMode.REAL:
                    self.metrics.increment("official_account_real_dispatch_failure_total")
                logger.exception("official-account dispatch failed")
                commit_session(self.session)
                raise RuntimeError("official-account dispatch failed") from exc

            self._apply_dispatch_result(job=job, attempt=attempt, result=result)
            commit_session(self.session)
            refreshed_job = self.get_publication_job(job.id)
            refreshed_attempt = self.repository.get_latest_publication_attempt(
                publication_job_id=job.id
            )
            action = "failed"
            if result.attempt_status == DigestPublicationAttemptStatus.PREVIEWED:
                action = "previewed"
            elif result.attempt_status == DigestPublicationAttemptStatus.SENT:
                action = "sent"
            return DispatchPublicationResult(
                action=action,
                publication_job=refreshed_job,
                attempt=refreshed_attempt,
            )

    def verify_callback_handshake(
        self,
        *,
        signature: str | None,
        timestamp: str | None,
        nonce: str | None,
        echostr: str,
    ) -> str:
        if not self.settings.official_account_callback_enabled:
            raise ConflictError("official-account callback handling is disabled")
        if not self._verify_callback_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
        ):
            raise ConflictError("official-account callback signature is invalid")
        return echostr

    def ingest_callback(
        self,
        *,
        raw_payload: str,
        signature: str | None,
        timestamp: str | None,
        nonce: str | None,
    ) -> CallbackIngestResult:
        if not self.settings.official_account_callback_enabled:
            raise ConflictError("official-account callback handling is disabled")

        self.metrics.increment("official_account_callback_events_received_total")
        parsed_payload, payload_format = self._parse_callback_payload(raw_payload)
        parsed_app_id = self._resolve_callback_app_id(parsed_payload)
        dedupe_key = self._build_callback_dedupe_key(
            raw_payload=raw_payload,
            parsed_payload=parsed_payload,
            app_id=parsed_app_id,
        )
        existing = self.repository.get_callback_event_by_dedupe_key(dedupe_key)
        if existing is not None:
            existing.processing_status = OfficialAccountCallbackProcessingStatus.DUPLICATE
            existing.processing_note = "duplicate callback ignored"
            existing.processed_at = self.now_provider()
            commit_session(self.session)
            self.metrics.increment("official_account_callback_events_processed_total")
            return CallbackIngestResult(
                callback_event=existing,
                action="duplicate",
                binding_updated=False,
                linked_binding=existing.linked_binding,
            )

        event = OfficialAccountCallbackEvent(
            app_id=parsed_app_id,
            to_user_name=_string_or_none(parsed_payload.get("ToUserName")),
            from_openid=_string_or_none(
                parsed_payload.get("FromUserName") or parsed_payload.get("openid")
            ),
            msg_type=_string_or_none(
                parsed_payload.get("MsgType") or parsed_payload.get("msg_type")
            ),
            event_type=_string_or_none(parsed_payload.get("Event") or parsed_payload.get("event")),
            event_key=_string_or_none(
                parsed_payload.get("EventKey") or parsed_payload.get("event_key")
            ),
            event_time=self._parse_callback_event_time(
                parsed_payload.get("CreateTime")
                or parsed_payload.get("EventTime")
                or parsed_payload.get("event_time")
            ),
            dedupe_key=dedupe_key,
            signature_valid=self._verify_callback_signature(
                signature=signature,
                timestamp=timestamp,
                nonce=nonce,
            ),
            payload_format=payload_format,
            raw_payload=raw_payload,
            parsed_payload_json=parsed_payload or None,
            processing_status=OfficialAccountCallbackProcessingStatus.ACCEPTED,
        )
        self.repository.add_callback_event(event)

        if not event.signature_valid:
            event.processing_status = OfficialAccountCallbackProcessingStatus.FAILED
            event.processing_note = "callback signature verification failed"
            event.processed_at = self.now_provider()
            commit_session(self.session)
            return CallbackIngestResult(
                callback_event=event,
                action="signature_invalid",
                binding_updated=False,
                linked_binding=None,
            )

        linked_binding = self._resolve_callback_binding(
            app_id=event.app_id,
            openid=event.from_openid,
        )
        event.linked_binding_id = None if linked_binding is None else linked_binding.id

        action = "ignored"
        binding_updated = False
        if event.msg_type != "event":
            event.processing_status = OfficialAccountCallbackProcessingStatus.IGNORED
            event.processing_note = "non-event official-account callback ignored in v1"
        elif event.event_type == "subscribe":
            action, binding_updated = self._handle_subscribe_callback(
                event=event,
                binding=linked_binding,
            )
        elif event.event_type == "unsubscribe":
            action, binding_updated = self._handle_unsubscribe_callback(
                event=event,
                binding=linked_binding,
            )
        else:
            event.processing_status = OfficialAccountCallbackProcessingStatus.IGNORED
            event.processing_note = (
                f"official-account callback event {event.event_type or 'unknown'} ignored in v1"
            )
            event.processed_at = self.now_provider()

        commit_session(self.session)
        if event.processing_status in {
            OfficialAccountCallbackProcessingStatus.PROCESSED,
            OfficialAccountCallbackProcessingStatus.IGNORED,
            OfficialAccountCallbackProcessingStatus.DUPLICATE,
        }:
            self.metrics.increment("official_account_callback_events_processed_total")
        return CallbackIngestResult(
            callback_event=event,
            action=action,
            binding_updated=binding_updated,
            linked_binding=linked_binding,
        )

    def _upsert_issue(
        self,
        *,
        user: UserProfile,
        issue_date: date,
        source_job: PulseJob | None,
        ordered_cards: Sequence[PulseCard],
        event_source: SyncEventSource,
        auto_commit: bool,
    ) -> DigestBuildResult:
        existing = self.repository.get_digest_issue_for_user_date(
            user_id=user.id,
            issue_date=issue_date,
        )
        action = "updated" if existing is not None else "created"
        if existing is None:
            issue = PulseDigestIssue(
                user_id=user.id,
                issue_date=issue_date,
                title="",
                summary="",
                content_payload={},
            )
            self.repository.add_digest_issue(issue)
        else:
            issue = existing

        with bind_log_context(digest_issue_id=issue.id, user_id=user.id):
            issue.source_pulse_job_id = None if source_job is None else source_job.id
            issue.deep_link_path = self._build_deep_link_path(user.id, issue_date)
            issue.selected_card_count = len(ordered_cards)
            issue.items.clear()
            self.session.flush()

            if ordered_cards:
                issue.status = PulseDigestIssueStatus.READY
                for index, card in enumerate(ordered_cards, start=1):
                    issue.items.append(
                        PulseDigestItem(
                            pulse_card_id=card.id,
                            sort_order=index,
                            card_type=card.card_type,
                            source_paper_id=card.source_paper_id,
                            title=card.title,
                            summary=card.summary,
                            why_now=card.why_now,
                        )
                    )
            else:
                issue.status = PulseDigestIssueStatus.SKIPPED
            content_payload = self._build_content_payload(issue, ordered_cards)
            issue.title = str(content_payload["title"])
            issue.summary = str(content_payload["summary"])
            issue.highlight_count = int(content_payload["highlight_count"])
            orchestration_metadata: dict[str, Any] = {
                "section_order": list(content_payload.get("section_order") or []),
                "section_item_counts": {
                    str(section.get("kind")): int(section.get("item_count") or 0)
                    for section in list(content_payload.get("sections") or [])
                },
                "auto_prepare_official_account": (
                    self.settings.digest_auto_prepare_official_account
                ),
                "auto_dispatch_official_account": (
                    self.settings.digest_auto_dispatch_official_account
                ),
            }
            if ordered_cards and self.settings.digest_auto_prepare_official_account:
                self.prepare_publication(
                    issue.id,
                    publish_mode=DigestPublicationMode.MANUAL_PREVIEW,
                    auto_commit=False,
                )
                self.session.flush()
                self.session.expire(issue, ["publication_jobs"])
                if self.settings.digest_auto_dispatch_official_account:
                    auto_dispatch_note: dict[str, Any] = {
                        "attempted": True,
                        "required_real_mode": self.settings.digest_auto_dispatch_require_real_mode,
                    }
                    try:
                        auto_dispatch_result = self.dispatch_digest_issue(
                            issue.id,
                            dispatch_mode=DigestDispatchMode.AUTO_AFTER_ORCHESTRATION,
                            retry_failed=self.settings.digest_dispatch_retry_failed_jobs,
                            force_prepare=False,
                            auto_commit=False,
                            create_skipped_run_if_no_eligible=False,
                        )
                    except ConflictError as exc:
                        auto_dispatch_note["result"] = "skipped"
                        auto_dispatch_note["reason"] = str(exc)
                        logger.info("digest issue auto-dispatch skipped", extra=auto_dispatch_note)
                    else:
                        if auto_dispatch_result is None:
                            auto_dispatch_note["result"] = "skipped"
                            auto_dispatch_note["reason"] = (
                                "no eligible official-account publication jobs remained "
                                "for dispatch"
                            )
                        else:
                            auto_dispatch_note["result"] = auto_dispatch_result.action
                            if auto_dispatch_result.delivery_decision is not None:
                                auto_dispatch_note["delivery_decision"] = (
                                    auto_dispatch_result.delivery_decision.decision.value
                                )
                                auto_dispatch_note["delivery_reason_codes"] = list(
                                    auto_dispatch_result.delivery_decision.reason_codes or []
                                )
                            if auto_dispatch_result.dispatch_run is not None:
                                auto_dispatch_note["dispatch_run_id"] = str(
                                    auto_dispatch_result.dispatch_run.id
                                )
                                auto_dispatch_note["dispatch_status"] = (
                                    auto_dispatch_result.dispatch_run.status.value
                                )
                            elif auto_dispatch_result.action == "skipped":
                                auto_dispatch_note["reason"] = (
                                    "official-account delivery policy blocked auto dispatch"
                                )
                    orchestration_metadata["auto_dispatch"] = auto_dispatch_note

            issue.build_metadata = {
                "selection_source": "selected_pulse_cards_only",
                "source_pulse_job_id": None if source_job is None else str(source_job.id),
                "selected_card_ids": [str(card.id) for card in ordered_cards],
                "selection_order": "existing_issue_sort_order_or_generated_at_asc",
                "result": issue.status.value,
                "orchestration": orchestration_metadata,
            }
            issue.content_payload = content_payload
            sync_event_type = (
                SyncEventType.UPDATED if action == "updated" else SyncEventType.CREATED
            )
            self.sync_events.emit_pulse_digest_issue(
                issue,
                event_type=sync_event_type,
                event_source=event_source,
            )
            self.metrics.increment("digest_issues_built_total")
            self.metrics.increment("daily_digest_issues_orchestrated_total")
            logger.info(
                "digest issue upserted",
                extra={
                    "digest_status": issue.status.value,
                    "selected_cards": len(ordered_cards),
                    "source_pulse_job_id": None if source_job is None else str(source_job.id),
                },
            )

        if auto_commit:
            commit_session(self.session)
            issue = self.get_digest_issue(issue.id)
        return DigestBuildResult(issue=issue, action=action)

    def _select_dispatch_eligible_jobs(
        self,
        publication_jobs: Sequence[DigestPublicationJob],
        *,
        retry_failed: bool,
    ) -> list[DigestPublicationJob]:
        eligible: list[DigestPublicationJob] = []
        for job in publication_jobs:
            if job.publish_target != DigestPublicationTarget.OFFICIAL_ACCOUNT:
                continue
            if job.status in (DigestPublicationStatus.PREPARED, DigestPublicationStatus.PREVIEWED):
                eligible.append(job)
                continue
            if job.status == DigestPublicationStatus.FAILED and retry_failed:
                eligible.append(job)
        eligible.sort(
            key=lambda job: (
                0 if job.status == DigestPublicationStatus.PREPARED else 1,
                0 if job.prepared_at is None else 1,
                job.prepared_at or job.created_at,
                str(job.id),
            )
        )
        return eligible

    def _matching_subscription_policy(
        self,
        *,
        user_id: UUID,
        channel: ChannelType,
    ) -> SubscriptionPolicy | None:
        policies = self.subscription_policy_repository.list(user_id=user_id)
        return find_matching_delivery_policy(policies, channel=channel)

    def _evaluate_delivery_control(
        self,
        *,
        issue: PulseDigestIssue,
        channel: ChannelType,
        policy: SubscriptionPolicy | None,
        current_time: datetime,
    ) -> DigestDeliveryControlPreview:
        self.metrics.increment("digest_delivery_decisions_evaluated_total")
        normalized_policy = normalize_delivery_control_policy(
            policy,
            default_timezone=self.settings.default_timezone,
        )
        zone = self._safe_zone(normalized_policy.effective_timezone)
        local_now = current_time.astimezone(zone)
        local_weekday = local_now.weekday()
        focus_card_type = self._resolve_focus_card_type(issue)
        selected_card_count = int(issue.selected_card_count or 0)
        reason_codes: list[str] = []
        next_allowed_at: datetime | None = None

        if policy is None:
            reason_codes.append("no_subscription_policy")
        elif not policy.enabled:
            reason_codes.append("policy_disabled")
        else:
            if selected_card_count <= 0:
                reason_codes.append("no_digest_content")
            if (
                normalized_policy.minimum_selected_cards is not None
                and selected_card_count < normalized_policy.minimum_selected_cards
            ):
                reason_codes.append("insufficient_selected_cards")
            if normalized_policy.skip_if_no_today_focus and focus_card_type is None:
                reason_codes.append("missing_today_focus")
            if (
                normalized_policy.allowed_weekdays
                and local_weekday not in normalized_policy.allowed_weekdays
            ):
                reason_codes.append("weekday_blocked")
                next_allowed_at = self._max_allowed_at(
                    next_allowed_at,
                    self._next_allowed_weekday(
                        local_now=local_now,
                        allowed_weekdays=normalized_policy.allowed_weekdays,
                    ),
                )
            active_quiet_window = self._active_quiet_window(
                quiet_hours=normalized_policy.quiet_hours,
                current_time=current_time,
            )
            if active_quiet_window is not None:
                reason_codes.append("quiet_hours_active")
                next_allowed_at = self._max_allowed_at(
                    next_allowed_at,
                    self._next_allowed_after_quiet_window(
                        window=active_quiet_window,
                        current_time=current_time,
                    ),
                )
            if (
                normalized_policy.muted_until is not None
                and current_time < normalized_policy.muted_until
            ):
                reason_codes.append("muted_until_active")
                next_allowed_at = self._max_allowed_at(
                    next_allowed_at,
                    normalized_policy.muted_until,
                )

        decision = (
            DigestDeliveryDecisionStatus.ELIGIBLE
            if not reason_codes
            else DigestDeliveryDecisionStatus.SKIPPED
        )
        return DigestDeliveryControlPreview(
            issue=issue,
            matched_subscription_policy=policy,
            normalized_control_policy=normalized_policy.as_dict(),
            current_local_time=local_now,
            local_weekday=local_weekday,
            decision=decision,
            reason_codes=reason_codes,
            next_allowed_at=next_allowed_at,
            quiet_hours=normalized_policy.quiet_hours,
            muted_until=normalized_policy.muted_until,
            focus_card_type=focus_card_type,
        )

    def _persist_delivery_decision(
        self,
        *,
        preview: DigestDeliveryControlPreview,
        dispatch_run_id: UUID | None,
    ) -> DigestDeliveryDecision:
        decision = DigestDeliveryDecision(
            digest_issue_id=preview.issue.id,
            user_id=preview.issue.user_id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
            subscription_policy_id=(
                None
                if preview.matched_subscription_policy is None
                else preview.matched_subscription_policy.id
            ),
            dispatch_run_id=dispatch_run_id,
            decision=preview.decision,
            reason_codes=list(preview.reason_codes),
            effective_timezone=str(preview.normalized_control_policy["effective_timezone"]),
            local_issue_weekday=preview.local_weekday,
            selected_card_count=int(preview.issue.selected_card_count or 0),
            focus_card_type=preview.focus_card_type,
            quiet_hours=preview.quiet_hours,
            muted_until=preview.muted_until,
            next_allowed_at=preview.next_allowed_at,
            created_at=self.now_provider(),
        )
        self.repository.add_delivery_decision(decision)
        if decision.decision == DigestDeliveryDecisionStatus.SKIPPED:
            self.metrics.increment("digest_delivery_decisions_skipped_total")
        return decision

    def _serialize_matched_subscription_policy(
        self,
        policy: SubscriptionPolicy | None,
    ) -> dict[str, Any] | None:
        if policy is None:
            return None
        return {
            "id": str(policy.id),
            "user_id": str(policy.user_id),
            "channel": policy.channel.value,
            "enabled": policy.enabled,
            "frequency": policy.frequency.value,
            "quiet_hours": policy.quiet_hours,
            "frequency_cap": policy.frequency_cap,
            "endpoint": policy.endpoint,
            "policy": dict(policy.policy or {}),
            "created_at": policy.created_at,
            "updated_at": policy.updated_at,
        }

    def _resolve_focus_card_type(self, issue: PulseDigestIssue) -> str | None:
        content_payload = issue.content_payload or {}
        focus_card = content_payload.get("focus_card")
        if isinstance(focus_card, dict):
            card_type = focus_card.get("card_type")
            if isinstance(card_type, str):
                return card_type
        sections = content_payload.get("sections")
        if isinstance(sections, list):
            for section in sections:
                if not isinstance(section, dict) or section.get("kind") != "today_focus":
                    continue
                items = section.get("items")
                if isinstance(items, list) and items:
                    first = items[0]
                    if isinstance(first, dict) and isinstance(first.get("card_type"), str):
                        return str(first["card_type"])
        return None

    def _active_quiet_window(
        self,
        *,
        quiet_hours: dict[str, Any] | None,
        current_time: datetime,
    ) -> dict[str, Any] | None:
        windows = []
        if isinstance(quiet_hours, dict):
            candidate_windows = quiet_hours.get("windows")
            if isinstance(candidate_windows, list):
                windows = [window for window in candidate_windows if isinstance(window, dict)]
        for window in windows:
            if self._quiet_window_active(window=window, current_time=current_time):
                return window
        return None

    def _quiet_window_active(
        self,
        *,
        window: dict[str, Any],
        current_time: datetime,
    ) -> bool:
        start = window.get("start")
        end = window.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            return False
        zone = self._safe_zone(str(window.get("timezone") or self.settings.default_timezone))
        localized = current_time.astimezone(zone)
        start_time = time.fromisoformat(start)
        end_time = time.fromisoformat(end)
        current_local_time = localized.time().replace(tzinfo=None)
        if start_time <= end_time:
            return start_time <= current_local_time < end_time
        return current_local_time >= start_time or current_local_time < end_time

    def _next_allowed_after_quiet_window(
        self,
        *,
        window: dict[str, Any],
        current_time: datetime,
    ) -> datetime | None:
        end = window.get("end")
        if not isinstance(end, str):
            return None
        zone = self._safe_zone(str(window.get("timezone") or self.settings.default_timezone))
        localized = current_time.astimezone(zone)
        end_time = time.fromisoformat(end)
        candidate_date = localized.date()
        current_local_time = localized.time().replace(tzinfo=None)
        if current_local_time >= end_time:
            candidate_date = candidate_date + timedelta(days=1)
        next_local = datetime.combine(candidate_date, end_time, tzinfo=zone)
        if next_local <= localized:
            next_local = next_local + timedelta(days=1)
        return next_local.astimezone(UTC)

    def _next_allowed_weekday(
        self,
        *,
        local_now: datetime,
        allowed_weekdays: Sequence[int],
    ) -> datetime | None:
        if not allowed_weekdays:
            return None
        zone = local_now.tzinfo
        assert zone is not None
        for offset in range(0, 8):
            candidate = local_now + timedelta(days=offset)
            if candidate.weekday() in allowed_weekdays:
                candidate_local = datetime.combine(candidate.date(), time.min, tzinfo=zone)
                if candidate_local > local_now:
                    return candidate_local.astimezone(UTC)
        return None

    def _max_allowed_at(
        self,
        current: datetime | None,
        candidate: datetime | None,
    ) -> datetime | None:
        if candidate is None:
            return current
        if current is None:
            return candidate
        return max(current, candidate)

    def _safe_zone(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    def _validate_dispatch_provider_mode(
        self,
        *,
        provider_status: dict[str, Any],
        dispatch_mode: DigestDispatchMode,
    ) -> None:
        provider_mode = provider_status["mode"]
        if provider_mode == OfficialAccountProviderMode.DISABLED:
            raise ConflictError("official-account provider mode is disabled")
        if dispatch_mode == DigestDispatchMode.AUTO_AFTER_ORCHESTRATION:
            if self.settings.digest_auto_dispatch_require_real_mode and (
                provider_mode != OfficialAccountProviderMode.REAL
                or not provider_status["real_send_enabled"]
            ):
                raise ConflictError(
                    "auto dispatch requires official-account real mode with real send enabled"
                )
        if provider_mode == OfficialAccountProviderMode.REAL and not provider_status["readiness"]:
            raise ConflictError(
                "official-account provider is not ready: "
                + "; ".join(provider_status["readiness_failures"])
            )

    def _resolve_dispatch_run_status(
        self,
        *,
        eligible_jobs: int,
        previewed_jobs: int,
        sent_jobs: int,
        failed_jobs: int,
    ) -> DigestDispatchRunStatus:
        if eligible_jobs <= 0:
            return DigestDispatchRunStatus.SKIPPED
        if failed_jobs <= 0:
            return DigestDispatchRunStatus.COMPLETED
        if previewed_jobs > 0 or sent_jobs > 0:
            return DigestDispatchRunStatus.PARTIAL_FAILED
        return DigestDispatchRunStatus.FAILED

    def _resolve_source_job(
        self,
        *,
        user: UserProfile,
        issue_date: date | None,
        source_pulse_job_id: UUID | None,
    ) -> PulseJob | None:
        if source_pulse_job_id is not None:
            source_job = self.pulse_repository.get_job(source_pulse_job_id)
            if source_job is None or source_job.user_id != user.id:
                raise NotFoundError(f"pulse job {source_pulse_job_id} was not found")
            return source_job

        candidate_jobs = self.pulse_repository.list_jobs(
            user_id=user.id,
            status=PulseJobStatus.COMPLETED,
            limit=200,
        )
        if issue_date is None and candidate_jobs:
            return candidate_jobs[0]

        for job in candidate_jobs:
            if self._resolve_issue_date(user, job) == issue_date:
                return job
        return None

    def _resolve_cards_for_build(
        self,
        *,
        user_id: UUID,
        issue_date: date,
        source_job: PulseJob | None,
    ) -> list[PulseCard]:
        existing = self.repository.get_digest_issue_for_user_date(
            user_id=user_id,
            issue_date=issue_date,
        )
        existing_order = {
            item.pulse_card_id: item.sort_order
            for item in ([] if existing is None else existing.items)
        }
        if source_job is None:
            return []
        cards = list(source_job.cards)
        if existing_order:
            return sorted(
                cards,
                key=lambda card: (
                    existing_order.get(card.id, 10_000),
                    card.generated_at,
                    str(card.id),
                ),
            )
        return sorted(cards, key=lambda card: (card.generated_at, str(card.id)))

    def _resolve_issue_date(self, user: UserProfile, source_job: PulseJob | None) -> date:
        timezone_name = str(
            user.reminder_preferences.get("timezone") or self.settings.default_timezone
        )
        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo("UTC")
        anchor = self.now_provider() if source_job is None else source_job.scheduled_for
        if anchor.tzinfo is None:
            anchor = anchor.replace(tzinfo=UTC)
        return anchor.astimezone(zone).date()

    def _require_user(self, user_id: UUID) -> UserProfile:
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def _build_content_payload(
        self,
        issue: PulseDigestIssue,
        ordered_cards: Sequence[PulseCard],
    ) -> dict:
        serialized_items = [
            self._serialize_digest_card(card, sort_order=index)
            for index, card in enumerate(ordered_cards, start=1)
        ]
        card_order = {card.id: index for index, card in enumerate(ordered_cards, start=1)}
        consumed_ids: set[UUID] = set()

        today_focus_cards = self._take_first_matching_cards(
            ordered_cards,
            consumed_ids=consumed_ids,
            preferred_types=(
                PulseCardType.TODAY_SUGGESTION,
                PulseCardType.NEXT_ACTION,
                PulseCardType.STALLED_PROGRESS,
                PulseCardType.DEADLINE_RISK,
            ),
        )
        yesterday_recap_cards = self._take_first_matching_cards(
            ordered_cards,
            consumed_ids=consumed_ids,
            preferred_types=(PulseCardType.YESTERDAY_SUMMARY,),
        )
        signal_update_cards = self._take_matching_cards(
            ordered_cards,
            consumed_ids=consumed_ids,
            predicate=lambda card: card.card_type == PulseCardType.SIGNAL_CHANGE,
            limit=self.settings.digest_signal_updates_max_items,
        )
        related_paper_cards = self._take_matching_cards(
            ordered_cards,
            consumed_ids=consumed_ids,
            predicate=lambda card: card.card_type == PulseCardType.RELATED_PAPER,
            limit=self.settings.digest_related_papers_max_items,
        )
        other_update_cards = self._take_matching_cards(
            ordered_cards,
            consumed_ids=consumed_ids,
            predicate=lambda _card: True,
            limit=self.settings.digest_other_updates_max_items,
        )

        section_cards = {
            "today_focus": today_focus_cards,
            "yesterday_recap": yesterday_recap_cards,
            "signal_updates": signal_update_cards,
            "related_papers": related_paper_cards,
            "other_updates": other_update_cards,
        }
        sections = [
            {
                "kind": section_kind,
                "title": DAILY_DIGEST_SECTION_TITLES[section_kind],
                "item_count": len(section_cards[section_kind]),
                "items": [
                    self._serialize_digest_card(card, sort_order=card_order[card.id])
                    for card in section_cards[section_kind]
                ],
            }
            for section_kind in DAILY_DIGEST_SECTION_ORDER
        ]
        highlights = self._build_digest_highlights(sections)
        quick_stats = self._build_quick_stats(ordered_cards)
        title = self._build_daily_digest_title(issue.issue_date, ordered_cards)
        summary = self._build_daily_digest_summary(sections, len(ordered_cards))
        focus_card = (
            None
            if not today_focus_cards
            else self._serialize_digest_card(
                today_focus_cards[0],
                sort_order=card_order[today_focus_cards[0].id],
            )
        )
        publication_preview = self._build_publication_preview(
            issue=issue,
            title=title,
            summary=summary,
            highlights=highlights,
            focus_card=focus_card,
        )
        return {
            "issue_date": issue.issue_date.isoformat(),
            "status": issue.status.value,
            "title": title,
            "summary": summary,
            "highlight_count": len(highlights),
            "selected_card_count": len(serialized_items),
            "deep_link_path": issue.deep_link_path,
            "section_order": list(DAILY_DIGEST_SECTION_ORDER),
            "sections": sections,
            "quick_stats": quick_stats,
            "highlights": highlights,
            "focus_card": focus_card,
            "publication_preview": publication_preview,
            "items": serialized_items,
            "mini_program_path": publication_preview.get("mini_program_path"),
        }

    def _serialize_digest_card(self, card: PulseCard, *, sort_order: int) -> dict[str, Any]:
        return {
            "sort_order": sort_order,
            "pulse_card_id": str(card.id),
            "card_type": card.card_type.value,
            "source_paper_id": None if card.source_paper_id is None else str(card.source_paper_id),
            "title": card.title,
            "summary": card.summary,
            "why_now": card.why_now,
            "action_text": card.action_text,
            "deep_link": card.deep_link,
        }

    def _take_first_matching_cards(
        self,
        ordered_cards: Sequence[PulseCard],
        *,
        consumed_ids: set[UUID],
        preferred_types: Sequence[PulseCardType],
    ) -> list[PulseCard]:
        for preferred_type in preferred_types:
            for card in ordered_cards:
                if card.id in consumed_ids or card.card_type != preferred_type:
                    continue
                consumed_ids.add(card.id)
                return [card]
        return []

    def _take_matching_cards(
        self,
        ordered_cards: Sequence[PulseCard],
        *,
        consumed_ids: set[UUID],
        predicate,
        limit: int,
    ) -> list[PulseCard]:
        selected: list[PulseCard] = []
        effective_limit = max(0, limit)
        if effective_limit == 0:
            return selected
        for card in ordered_cards:
            if card.id in consumed_ids or not predicate(card):
                continue
            selected.append(card)
            consumed_ids.add(card.id)
            if len(selected) >= effective_limit:
                break
        return selected

    def _build_digest_highlights(self, sections: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        highlights: list[dict[str, Any]] = []
        for section in sections:
            items = list(section.get("items") or [])
            if not items:
                continue
            highlights.append(items[0])
            if len(highlights) >= 3:
                break
        return highlights

    def _build_quick_stats(self, ordered_cards: Sequence[PulseCard]) -> dict[str, int]:
        touched_paper_ids = {card.source_paper_id for card in ordered_cards if card.source_paper_id}
        return {
            "selected_card_count": len(ordered_cards),
            "related_paper_count": sum(
                1 for card in ordered_cards if card.card_type == PulseCardType.RELATED_PAPER
            ),
            "signal_update_count": sum(
                1 for card in ordered_cards if card.card_type == PulseCardType.SIGNAL_CHANGE
            ),
            "touched_paper_count": len(touched_paper_ids),
        }

    def _build_daily_digest_title(
        self,
        issue_date: date,
        ordered_cards: Sequence[PulseCard],
    ) -> str:
        if not ordered_cards:
            return f"Daily digest for {issue_date.isoformat()} (no selected cards)"
        return f"Daily digest for {issue_date.isoformat()}"

    def _build_daily_digest_summary(
        self,
        sections: Sequence[dict[str, Any]],
        total_cards: int,
    ) -> str:
        if total_cards == 0:
            return "No selected pulse cards were available for this digest issue."

        counts = {str(section["kind"]): int(section["item_count"]) for section in sections}
        parts: list[str] = []
        if counts.get("today_focus"):
            parts.append("1 today focus")
        if counts.get("yesterday_recap"):
            parts.append("1 yesterday recap")
        if counts.get("signal_updates"):
            count = counts["signal_updates"]
            parts.append(f"{count} signal update" if count == 1 else f"{count} signal updates")
        if counts.get("related_papers"):
            count = counts["related_papers"]
            parts.append(f"{count} related paper" if count == 1 else f"{count} related papers")
        if counts.get("other_updates"):
            count = counts["other_updates"]
            parts.append(f"{count} other update" if count == 1 else f"{count} other updates")
        return f"{', '.join(parts)} from {total_cards} selected pulse cards."

    def _build_publication_preview(
        self,
        *,
        issue: PulseDigestIssue,
        title: str,
        summary: str,
        highlights: Sequence[dict[str, Any]],
        focus_card: dict[str, Any] | None,
    ) -> dict[str, Any]:
        deep_link_path = issue.deep_link_path
        mini_program_path = None if deep_link_path is None else deep_link_path.lstrip("/")
        article_url = None
        if deep_link_path and self.settings.official_account_default_article_base_url:
            article_url = (
                self.settings.official_account_default_article_base_url.rstrip("/") + deep_link_path
            )
        return {
            "digest_title": title,
            "digest_subtitle": summary,
            "digest_highlights": list(highlights),
            "primary_cta_text": (
                "查看今日重点"
                if focus_card is None or not focus_card.get("action_text")
                else str(focus_card["action_text"])
            ),
            "primary_cta_path": deep_link_path,
            "mini_program_path": mini_program_path,
            "article_url": article_url,
        }

    def _build_deep_link_path(self, user_id: UUID, issue_date: date) -> str:
        return f"/mini/pulse-digests/{user_id}/{issue_date.isoformat()}"

    def _apply_dispatch_result(
        self,
        *,
        job: DigestPublicationJob,
        attempt: DigestPublicationAttempt,
        result: OfficialAccountPublishResult,
    ) -> None:
        attempt.provider_name = result.provider_name
        attempt.provider_mode = result.provider_mode
        attempt.status = result.attempt_status
        attempt.request_payload = result.request_payload
        attempt.response_payload = result.response_payload
        attempt.error_summary = result.error_summary
        attempt.external_message_id = result.external_message_id
        attempt.provider_response_code = result.provider_response_code
        attempt.provider_response_message = result.provider_response_message
        attempt.finished_at = self.now_provider()
        job.provider_name = result.provider_name
        job.payload = result.request_payload
        job.last_error = result.error_summary
        if result.attempt_status == DigestPublicationAttemptStatus.PREVIEWED:
            job.status = DigestPublicationStatus.PREVIEWED
        elif result.attempt_status == DigestPublicationAttemptStatus.SENT:
            job.status = DigestPublicationStatus.SENT
            job.published_at = self.now_provider()
        else:
            job.status = DigestPublicationStatus.FAILED
        job.external_message_id = result.external_message_id
        if result.attempt_status == DigestPublicationAttemptStatus.FAILED:
            self.metrics.increment("digest_publication_attempts_failed_total")
            if result.provider_mode == OfficialAccountProviderMode.REAL:
                self.metrics.increment("official_account_real_dispatch_failure_total")
        elif result.attempt_status == DigestPublicationAttemptStatus.SENT:
            self.metrics.increment("official_account_real_dispatch_success_total")

    def _validate_real_dispatch_binding(self, binding: WeChatIdentityBinding) -> None:
        if binding.channel_type != WeChatBindingChannelType.OFFICIAL_ACCOUNT:
            raise ConflictError("publication binding is not an official-account binding")
        if binding.bind_state != WeChatBindingState.ACTIVE:
            raise ConflictError("official-account binding is not active")
        if not binding.subscribed:
            raise ConflictError("official-account binding is not subscribed")
        if not binding.digest_enabled:
            raise ConflictError("official-account binding has digest disabled")

    def _resolve_callback_binding(
        self,
        *,
        app_id: str | None,
        openid: str | None,
    ) -> WeChatIdentityBinding | None:
        if not app_id or not openid:
            return None
        return self.repository.get_binding_by_channel_app_openid(
            channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
            app_id=app_id,
            openid=openid,
        )

    def _handle_subscribe_callback(
        self,
        *,
        event: OfficialAccountCallbackEvent,
        binding: WeChatIdentityBinding | None,
    ) -> tuple[str, bool]:
        if binding is None:
            event.processing_status = OfficialAccountCallbackProcessingStatus.ACCEPTED
            event.processing_note = (
                "no matching official-account binding exists yet; "
                "callback reserved for explicit claim"
            )
            return "binding_not_found", False

        callback_time = event.event_time or self.now_provider()
        binding.subscribed = True
        binding.subscribed_at = callback_time
        binding.unsubscribed_at = None
        binding.last_seen_at = callback_time
        binding.bind_state = WeChatBindingState.ACTIVE
        event.processing_status = OfficialAccountCallbackProcessingStatus.PROCESSED
        event.processing_note = "official-account subscribe event applied to binding"
        event.processed_at = self.now_provider()
        self.sync_events.emit_wechat_identity_binding(
            binding,
            event_type=SyncEventType.UPDATED,
            event_source=SyncEventSource.SYSTEM,
        )
        self.metrics.increment("official_account_binding_updates_total")
        return "binding_updated", True

    def _handle_unsubscribe_callback(
        self,
        *,
        event: OfficialAccountCallbackEvent,
        binding: WeChatIdentityBinding | None,
    ) -> tuple[str, bool]:
        if binding is None:
            event.processing_status = OfficialAccountCallbackProcessingStatus.IGNORED
            event.processing_note = (
                "no matching official-account binding exists for this unsubscribe event"
            )
            event.processed_at = self.now_provider()
            return "binding_not_found", False

        callback_time = event.event_time or self.now_provider()
        binding.subscribed = False
        binding.unsubscribed_at = callback_time
        binding.last_seen_at = callback_time
        event.processing_status = OfficialAccountCallbackProcessingStatus.PROCESSED
        event.processing_note = "official-account unsubscribe event applied to binding"
        event.processed_at = self.now_provider()
        self.sync_events.emit_wechat_identity_binding(
            binding,
            event_type=SyncEventType.UPDATED,
            event_source=SyncEventSource.SYSTEM,
        )
        self.metrics.increment("official_account_binding_updates_total")
        return "binding_updated", True

    def _build_callback_dedupe_key(
        self,
        *,
        raw_payload: str,
        parsed_payload: dict[str, Any],
        app_id: str | None,
    ) -> str:
        parts = [
            app_id or "",
            _string_or_none(parsed_payload.get("FromUserName")) or "",
            _string_or_none(parsed_payload.get("MsgType") or parsed_payload.get("msg_type")) or "",
            _string_or_none(parsed_payload.get("Event") or parsed_payload.get("event")) or "",
            _string_or_none(parsed_payload.get("EventKey") or parsed_payload.get("event_key"))
            or "",
            _string_or_none(
                parsed_payload.get("CreateTime")
                or parsed_payload.get("EventTime")
                or parsed_payload.get("event_time")
            )
            or "",
            raw_payload.strip(),
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _resolve_callback_app_id(self, parsed_payload: dict[str, Any]) -> str | None:
        return (
            self.settings.wechat_official_app_id
            or _string_or_none(parsed_payload.get("AppId"))
            or _string_or_none(parsed_payload.get("app_id"))
        )

    def _parse_callback_payload(
        self,
        raw_payload: str,
    ) -> tuple[dict[str, Any], OfficialAccountCallbackPayloadFormat]:
        stripped = raw_payload.strip()
        if not stripped:
            return {}, OfficialAccountCallbackPayloadFormat.UNKNOWN
        if stripped.startswith("<"):
            try:
                root = ElementTree.fromstring(stripped)
            except ElementTree.ParseError:
                return {}, OfficialAccountCallbackPayloadFormat.XML
            payload = {
                child.tag: (child.text or "").strip() if child.text is not None else None
                for child in root
            }
            return payload, OfficialAccountCallbackPayloadFormat.XML
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                return {}, OfficialAccountCallbackPayloadFormat.JSON
            return (
                payload if isinstance(payload, dict) else {},
                OfficialAccountCallbackPayloadFormat.JSON,
            )
        return {}, OfficialAccountCallbackPayloadFormat.UNKNOWN

    def _parse_callback_event_time(self, raw_value: Any) -> datetime | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, datetime):
            return raw_value if raw_value.tzinfo is not None else raw_value.replace(tzinfo=UTC)
        if isinstance(raw_value, (int, float)):
            return datetime.fromtimestamp(raw_value, tz=UTC)
        value = str(raw_value).strip()
        if not value:
            return None
        if value.isdigit():
            return datetime.fromtimestamp(int(value), tz=UTC)
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    def _verify_callback_signature(
        self,
        *,
        signature: str | None,
        timestamp: str | None,
        nonce: str | None,
    ) -> bool:
        token = self.settings.wechat_official_callback_token
        if not token or not signature or not timestamp or not nonce:
            return False
        expected = hashlib.sha1(
            "".join(sorted([token, str(timestamp), str(nonce)])).encode("utf-8")
        ).hexdigest()
        return expected == signature


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
