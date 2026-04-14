"""Digest issue building, WeChat binding management, and publication preparation."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    DigestPublicationJob,
    PulseCard,
    PulseDigestIssue,
    PulseDigestItem,
    PulseJob,
    UserProfile,
    WeChatIdentityBinding,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    DigestPublicationMode,
    DigestPublicationStatus,
    DigestPublicationTarget,
    PulseDigestIssueStatus,
    PulseJobStatus,
    SyncEventSource,
    SyncEventType,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.sync_events import SyncEventService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DigestBuildResult:
    issue: PulseDigestIssue
    action: str


class DigestPublicationProvider(Protocol):
    """Prepare a future provider payload without sending it externally."""

    def prepare(
        self,
        *,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
        highlights: list[dict[str, str | None]],
    ) -> dict:
        """Return a future-facing provider payload."""


class StubOfficialAccountPublicationProvider:
    """Generate preview payloads without calling any external WeChat API."""

    provider_name = "stub"

    def prepare(
        self,
        *,
        issue: PulseDigestIssue,
        binding: WeChatIdentityBinding,
        highlights: list[dict[str, str | None]],
    ) -> dict:
        return {
            "title": issue.title,
            "summary": issue.summary,
            "issue_date": issue.issue_date.isoformat(),
            "highlight_count": issue.highlight_count,
            "selected_card_count": issue.selected_card_count,
            "highlights": highlights,
            "landing": {
                "deep_link_path": issue.deep_link_path,
                "mini_program_path": issue.deep_link_path,
                "article_url": None,
            },
            "binding": {
                "binding_id": str(binding.id),
                "channel_type": binding.channel_type.value,
                "app_id": binding.app_id,
                "openid": binding.openid,
                "unionid": binding.unionid,
                "display_label": binding.display_label,
            },
            "provider_contract": {
                "mode": "preview_only",
                "external_send_enabled": False,
            },
        }


class DigestService:
    """Manage future official-account digest reserve objects."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider=None,
        publication_provider: DigestPublicationProvider | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = DigestRepository(session)
        self.user_repository = UserRepository(session)
        self.pulse_repository = PulseRepository(session)
        self.sync_events = SyncEventService(session)
        self.metrics = get_metrics()
        self.publication_provider = publication_provider or StubOfficialAccountPublicationProvider()

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
        highlights = [
            {
                "title": item.title,
                "summary": item.summary,
                "why_now": item.why_now,
                "card_type": item.card_type.value,
                "source_paper_id": (
                    None if item.source_paper_id is None else str(item.source_paper_id)
                ),
            }
            for item in issue.items[:3]
        ]

        with bind_log_context(digest_issue_id=issue.id, user_id=issue.user_id):
            for existing in issue.publication_jobs:
                if existing.binding_id is None or existing.binding_id in eligible_binding_ids:
                    continue
                existing.status = DigestPublicationStatus.SKIPPED
                existing.last_error = "binding no longer eligible for digest publication"

            prepared_jobs: list[DigestPublicationJob] = []
            for binding in eligible_bindings:
                try:
                    payload = self.publication_provider.prepare(
                        issue=issue,
                        binding=binding,
                        highlights=highlights,
                    )
                except Exception as exc:
                    self.metrics.increment("digest_publication_jobs_failed_total")
                    logger.exception("digest publication payload preparation failed")
                    raise RuntimeError("digest publication preparation failed") from exc

                job = self.repository.get_publication_job(
                    digest_issue_id=issue.id,
                    binding_id=binding.id,
                    publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
                )
                status_value = (
                    DigestPublicationStatus.PREVIEWED
                    if publish_mode == DigestPublicationMode.MANUAL_PREVIEW
                    else DigestPublicationStatus.PREPARED
                )
                if job is None:
                    job = DigestPublicationJob(
                        digest_issue_id=issue.id,
                        binding_id=binding.id,
                        publish_target=DigestPublicationTarget.OFFICIAL_ACCOUNT,
                    )
                    self.repository.add_publication_job(job)
                job.publish_mode = publish_mode
                job.provider_name = getattr(self.publication_provider, "provider_name", "stub")
                job.status = status_value
                job.payload = payload
                job.last_error = None
                job.prepared_at = self.now_provider()
                prepared_jobs.append(job)
                self.metrics.increment("digest_publication_jobs_prepared_total")

            if auto_commit:
                commit_session(self.session)
            logger.info(
                "digest publication prepared",
                extra={"prepared_jobs": len(prepared_jobs)},
            )
        return self.repository.list_publication_jobs(digest_issue_id=issue.id)

    def list_publication_jobs(
        self,
        *,
        digest_issue_id: UUID | None = None,
        user_id: UUID | None = None,
        status: DigestPublicationStatus | None = None,
    ) -> list[DigestPublicationJob]:
        return self.repository.list_publication_jobs(
            digest_issue_id=digest_issue_id,
            user_id=user_id,
            status=status,
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
            issue.highlight_count = min(3, len(ordered_cards))
            issue.items.clear()
            self.session.flush()

            if ordered_cards:
                issue.status = PulseDigestIssueStatus.READY
                issue.title = self._build_title(issue_date, len(ordered_cards))
                issue.summary = self._build_summary(ordered_cards)
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
                issue.title = self._build_empty_title(issue_date)
                issue.summary = "No selected pulse cards were available for this digest issue."

            issue.build_metadata = {
                "selection_source": "selected_pulse_cards_only",
                "source_pulse_job_id": None if source_job is None else str(source_job.id),
                "selected_card_ids": [str(card.id) for card in ordered_cards],
                "selection_order": "existing_issue_sort_order_or_generated_at_asc",
                "result": issue.status.value,
            }
            issue.content_payload = self._build_content_payload(issue, ordered_cards)
            sync_event_type = (
                SyncEventType.UPDATED if action == "updated" else SyncEventType.CREATED
            )
            self.sync_events.emit_pulse_digest_issue(
                issue,
                event_type=sync_event_type,
                event_source=event_source,
            )
            self.metrics.increment("digest_issues_built_total")
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

    def _build_title(self, issue_date: date, selected_card_count: int) -> str:
        return f"Pulse digest for {issue_date.isoformat()} ({selected_card_count} highlights)"

    def _build_empty_title(self, issue_date: date) -> str:
        return f"Pulse digest for {issue_date.isoformat()} (no highlights)"

    def _build_summary(self, cards: Sequence[PulseCard]) -> str:
        card_types = [card.card_type.value for card in cards[:3]]
        return (
            f"{len(cards)} selected pulse cards ready for digest publication. "
            f"Top highlights: {', '.join(card_types)}."
        )

    def _build_content_payload(
        self,
        issue: PulseDigestIssue,
        ordered_cards: Sequence[PulseCard],
    ) -> dict:
        return {
            "issue_date": issue.issue_date.isoformat(),
            "status": issue.status.value,
            "title": issue.title,
            "summary": issue.summary,
            "highlight_count": issue.highlight_count,
            "selected_card_count": issue.selected_card_count,
            "deep_link_path": issue.deep_link_path,
            "highlights": [
                {
                    "sort_order": index,
                    "pulse_card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "source_paper_id": (
                        None if card.source_paper_id is None else str(card.source_paper_id)
                    ),
                    "title": card.title,
                    "summary": card.summary,
                    "why_now": card.why_now,
                }
                for index, card in enumerate(ordered_cards[:3], start=1)
            ],
            "items": [
                {
                    "sort_order": index,
                    "pulse_card_id": str(card.id),
                    "card_type": card.card_type.value,
                    "source_paper_id": (
                        None if card.source_paper_id is None else str(card.source_paper_id)
                    ),
                    "title": card.title,
                    "summary": card.summary,
                    "why_now": card.why_now,
                }
                for index, card in enumerate(ordered_cards, start=1)
            ],
        }

    def _build_deep_link_path(self, user_id: UUID, issue_date: date) -> str:
        return f"/mini/pulse-digests/{user_id}/{issue_date.isoformat()}"
