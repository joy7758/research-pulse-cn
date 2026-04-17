"""Explainable pulse pipeline, scoring, and orchestration."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.adapters.channels.registry import ChannelAdapterRegistry
from research_pulse_cn.adapters.models.dummy import DummyModelProvider
from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import DeliveryJob, PaperProfile, PulseCard, PulseJob
from research_pulse_cn.db.models import utcnow as db_utcnow
from research_pulse_cn.domain.contracts import (
    CardValidator,
    FactCollector,
    ModelProvider,
    RuleEngine,
)
from research_pulse_cn.domain.enums import (
    DeliveryJobStatus,
    PaperType,
    PulseCardType,
    PulseJobScheduledReason,
    PulseJobStatus,
    SyncEventSource,
)
from research_pulse_cn.domain.pulse import (
    PulseCandidate,
    PulseFact,
    PulsePipelineResult,
    PulseScoringConfig,
    ScoreBreakdown,
    SuppressionCode,
    SuppressionReason,
)
from research_pulse_cn.repositories.delivery import DeliveryRepository
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.pulse import PulseCardPreview
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.related_paper import RelatedPaperCandidateBuilder
from research_pulse_cn.services.sync_events import SyncEventService
from research_pulse_cn.services.today_suggestion import TodaySuggestionBuilder
from research_pulse_cn.services.yesterday_summary import YesterdaySummaryBuilder

logger = logging.getLogger(__name__)

CARD_TYPE_TIE_BREAK_ORDER: dict[PulseCardType, int] = {
    PulseCardType.SIGNAL_CHANGE: 0,
    PulseCardType.DEADLINE_RISK: 1,
    PulseCardType.STALLED_PROGRESS: 2,
    PulseCardType.TODAY_SUGGESTION: 3,
    PulseCardType.NEXT_ACTION: 4,
    PulseCardType.YESTERDAY_SUMMARY: 5,
    PulseCardType.RELATED_PAPER: 6,
}

TITLE_HINTS: dict[PulseCardType, str] = {
    PulseCardType.SIGNAL_CHANGE: "Signal update detected",
    PulseCardType.DEADLINE_RISK: "Deadline risk identified",
    PulseCardType.STALLED_PROGRESS: "Progress appears stalled",
    PulseCardType.TODAY_SUGGESTION: "Today's best next step",
    PulseCardType.NEXT_ACTION: "Next action ready",
    PulseCardType.YESTERDAY_SUMMARY: "Yesterday summary ready",
    PulseCardType.RELATED_PAPER: "Related paper worth reviewing",
}


@dataclass(slots=True)
class ResolvedPulsePolicy:
    """Resolved scoring and suppression knobs for a user."""

    config: PulseScoringConfig
    policy_ids: list[UUID]


class SimpleCardValidator(CardValidator):
    """Reject incomplete deterministic cards before delivery."""

    def validate(self, payload: dict[str, Any]) -> bool:
        required_fields = ("title", "summary", "why_now", "card_type")
        return all(payload.get(field) for field in required_fields)


class DeterministicFactCollector(FactCollector):
    """Build typed deterministic facts from current paper state."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider: Callable[[], datetime],
        settings: Settings,
    ) -> None:
        self.paper_repository = PaperRepository(session)
        self.now_provider = now_provider
        self.settings = settings

    def collect(self, subject_id: str) -> list[PulseFact]:
        user_id = UUID(subject_id)
        now = self.now_provider()
        papers = [
            paper
            for paper in self.paper_repository.list(user_id=user_id)
            if paper.type != PaperType.PAUSED
        ]
        facts: list[PulseFact] = []

        for paper in papers:
            facts.extend(self._collect_fact_set(paper, now))

        return sorted(
            facts,
            key=lambda fact: (
                CARD_TYPE_TIE_BREAK_ORDER[fact.card_type],
                fact.paper_title,
                fact.id,
            ),
        )

    def _collect_fact_set(
        self,
        paper: PaperProfile,
        now: datetime,
    ) -> list[PulseFact]:
        facts: list[PulseFact] = []
        latest_touch = _coerce_utc(paper.last_touch_at or paper.created_at)
        stagnation_days = max(0, (now - latest_touch).days)

        if paper.next_action:
            facts.append(
                PulseFact(
                    id=f"next_action:{paper.id}",
                    user_id=paper.user_id,
                    card_type=PulseCardType.NEXT_ACTION,
                    source_paper_id=paper.id,
                    source_timestamp=latest_touch,
                    paper_title=paper.title,
                    summary=paper.next_action,
                    why_now=f"{paper.title} already has a defined next action.",
                    action_text=paper.next_action,
                    deep_link=f"/papers/{paper.id}",
                    evidence_refs=paper.source_links[:3],
                    metadata={
                        "paper_priority": paper.priority,
                        "explicit_next_action": True,
                        "stagnation_days": stagnation_days,
                        "paper_type": paper.type.value,
                    },
                )
            )

        if stagnation_days > 0:
            facts.append(
                PulseFact(
                    id=f"stalled_progress:{paper.id}",
                    user_id=paper.user_id,
                    card_type=PulseCardType.STALLED_PROGRESS,
                    source_paper_id=paper.id,
                    source_timestamp=latest_touch,
                    paper_title=paper.title,
                    summary=(
                        "No material update has been recorded since "
                        f"{latest_touch.date().isoformat()}."
                    ),
                    why_now="The paper may be stuck and requires owner attention.",
                    action_text="Review blockers and schedule the next move.",
                    deep_link=f"/papers/{paper.id}",
                    evidence_refs=paper.source_links[:3],
                    metadata={
                        "paper_priority": paper.priority,
                        "stagnation_days": stagnation_days,
                        "explicit_next_action": bool(paper.next_action),
                        "paper_type": paper.type.value,
                    },
                )
            )

        signal_fact = self._build_signal_change_fact(paper, now, stagnation_days)
        if signal_fact is not None:
            facts.append(signal_fact)

        deadline_fact = self._build_deadline_risk_fact(paper, now, stagnation_days)
        if deadline_fact is not None:
            facts.append(deadline_fact)

        return facts

    def _build_signal_change_fact(
        self,
        paper: PaperProfile,
        now: datetime,
        stagnation_days: int,
    ) -> PulseFact | None:
        snapshots = sorted(paper.signal_snapshots, key=lambda item: item.fetched_at)
        if len(snapshots) < 2:
            return None

        previous = snapshots[-2]
        latest = snapshots[-1]
        signal_deltas: list[str] = []
        delta_total = 0
        for field_name, label in (
            ("citation_count", "citations"),
            ("download_count", "downloads"),
            ("read_count", "reads"),
        ):
            previous_value = getattr(previous, field_name)
            latest_value = getattr(latest, field_name)
            if (
                previous_value is not None
                and latest_value is not None
                and previous_value != latest_value
            ):
                delta = latest_value - previous_value
                delta_total += abs(delta)
                signal_deltas.append(f"{label}: {previous_value} -> {latest_value}")
        if previous.inclusion_status != latest.inclusion_status and latest.inclusion_status:
            signal_deltas.append(
                "inclusion status: "
                f"{previous.inclusion_status or 'unknown'}"
                f" -> {latest.inclusion_status}"
            )

        if not signal_deltas:
            return None

        latest_signal_time = _coerce_utc(latest.fetched_at)
        return PulseFact(
            id=f"signal_change:{paper.id}:{latest.id}",
            user_id=paper.user_id,
            card_type=PulseCardType.SIGNAL_CHANGE,
            source_paper_id=paper.id,
            source_timestamp=latest_signal_time,
            paper_title=paper.title,
            summary="; ".join(signal_deltas),
            why_now="External paper signals changed since the previous snapshot.",
            action_text="Review the new signal trend.",
            deep_link=f"/papers/{paper.id}",
            evidence_refs=paper.source_links[:3],
            metadata={
                "paper_priority": paper.priority,
                "hours_since_signal": max(
                    0, int((now - latest_signal_time).total_seconds() // 3600)
                ),
                "delta_total": delta_total,
                "explicit_next_action": bool(paper.next_action),
                "stagnation_days": stagnation_days,
                "paper_type": paper.type.value,
            },
        )

    def _build_deadline_risk_fact(
        self,
        paper: PaperProfile,
        now: datetime,
        stagnation_days: int,
    ) -> PulseFact | None:
        deadline_at = _parse_datetime(
            paper.identifiers.get("deadline_at")
            or paper.identifiers.get("submission_deadline_at")
            or paper.identifiers.get("next_deadline_at")
        )
        if deadline_at is None:
            return None

        days_until_deadline = int((deadline_at - now).total_seconds() // 86400)
        return PulseFact(
            id=f"deadline_risk:{paper.id}:{deadline_at.date().isoformat()}",
            user_id=paper.user_id,
            card_type=PulseCardType.DEADLINE_RISK,
            source_paper_id=paper.id,
            source_timestamp=deadline_at,
            paper_title=paper.title,
            summary=f"Paper deadline is {deadline_at.date().isoformat()}.",
            why_now="A tracked deadline is approaching or needs proactive monitoring.",
            action_text=paper.next_action or "Review the deadline plan and confirm ownership.",
            deep_link=f"/papers/{paper.id}",
            evidence_refs=paper.source_links[:3],
            metadata={
                "paper_priority": paper.priority,
                "days_until_deadline": days_until_deadline,
                "deadline_at": deadline_at.isoformat(),
                "explicit_next_action": bool(paper.next_action),
                "stagnation_days": stagnation_days,
                "paper_type": paper.type.value,
            },
        )


class DeterministicRuleEngine(RuleEngine):
    """Convert facts into stable pulse candidates."""

    def generate_candidates(self, facts: list[PulseFact]) -> list[PulseCandidate]:
        deduped: dict[tuple[Any, ...], PulseCandidate] = {}
        for fact in facts:
            title_hint = TITLE_HINTS[fact.card_type]
            title = f"{title_hint}: {fact.paper_title}"
            if fact.card_type == PulseCardType.TODAY_SUGGESTION:
                title = str(fact.metadata.get("title", title))
            elif fact.card_type == PulseCardType.YESTERDAY_SUMMARY:
                title = f"Yesterday summary for {fact.metadata['summary_date']}"
            elif fact.card_type == PulseCardType.RELATED_PAPER:
                title = f"Related paper: {fact.metadata.get('title', fact.paper_title)}"
            candidate = PulseCandidate(
                id=f"{fact.card_type.value}:{fact.source_paper_id or 'global'}:{fact.id}",
                fact_id=fact.id,
                user_id=fact.user_id,
                card_type=fact.card_type,
                source_paper_id=fact.source_paper_id,
                source_timestamp=fact.source_timestamp,
                paper_title=fact.paper_title,
                title_hint=title_hint,
                title=title,
                summary=fact.summary,
                why_now=fact.why_now,
                action_text=fact.action_text,
                deep_link=fact.deep_link,
                evidence_refs=list(fact.evidence_refs),
                candidate_metadata=dict(fact.metadata),
            )
            if fact.card_type == PulseCardType.RELATED_PAPER:
                key = (
                    fact.source_paper_id,
                    fact.card_type,
                    str(fact.metadata.get("external_reference_key", fact.id)),
                )
            else:
                key = (fact.source_paper_id, fact.card_type)
            current = deduped.get(key)
            if current is None or fact.source_timestamp > current.source_timestamp:
                deduped[key] = candidate
        return list(deduped.values())


class PulseService:
    """Orchestrate pulse preview, scoring, suppression, and dispatch."""

    def __init__(
        self,
        session: Session,
        *,
        fact_collector: FactCollector | None = None,
        rule_engine: RuleEngine | None = None,
        model_provider: ModelProvider | None = None,
        card_validator: CardValidator | None = None,
        adapter_registry: ChannelAdapterRegistry | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or db_utcnow
        self.user_repository = UserRepository(session)
        self.paper_repository = PaperRepository(session)
        self.pulse_repository = PulseRepository(session)
        self.policy_repository = SubscriptionPolicyRepository(session)
        self.delivery_repository = DeliveryRepository(session)
        self.fact_collector = fact_collector or DeterministicFactCollector(
            session,
            now_provider=self.now_provider,
            settings=self.settings,
        )
        self.rule_engine = rule_engine or DeterministicRuleEngine()
        self.model_provider = model_provider or DummyModelProvider()
        self.card_validator = card_validator or SimpleCardValidator()
        self.delivery_service = DeliveryService(session, adapter_registry=adapter_registry)
        self.digest_service = DigestService(session, now_provider=self.now_provider)
        self.sync_events = SyncEventService(session)
        self.yesterday_summary_builder = YesterdaySummaryBuilder(
            session,
            settings=self.settings,
            now_provider=self.now_provider,
        )
        self.today_suggestion_builder = TodaySuggestionBuilder(
            session,
            settings=self.settings,
            now_provider=self.now_provider,
        )
        self.related_paper_builder = RelatedPaperCandidateBuilder(
            session,
            settings=self.settings,
            now_provider=self.now_provider,
        )
        self.metrics = get_metrics()

    def preview(
        self,
        user_id: UUID,
        *,
        timezone_name: str | None = None,
    ) -> PulsePipelineResult:
        return self._build_pipeline(user_id, timezone_name=timezone_name)

    def enqueue_run(
        self,
        user_id: UUID,
        *,
        scheduled_for: datetime | None = None,
        subscription_policy_id: UUID | None = None,
        scheduled_reason: PulseJobScheduledReason = PulseJobScheduledReason.MANUAL_RUN,
        schedule_key: str | None = None,
        source_pulse_job_id: UUID | None = None,
    ) -> PulseJob:
        self._ensure_user_exists(user_id)
        job = PulseJob(
            user_id=user_id,
            subscription_policy_id=subscription_policy_id,
            source_pulse_job_id=source_pulse_job_id,
            scheduled_for=scheduled_for or self.now_provider(),
            scheduled_reason=scheduled_reason,
            schedule_key=schedule_key,
            status=PulseJobStatus.PENDING,
        )
        self.pulse_repository.add_job(job)
        commit_session(self.session)
        return self.pulse_repository.get_job(job.id) or job

    def run_with_pipeline(
        self,
        user_id: UUID,
        *,
        timezone_name: str | None = None,
    ) -> tuple[PulseJob, PulsePipelineResult]:
        job = self.enqueue_run(user_id)
        return self.process_job_with_pipeline(job.id, timezone_name=timezone_name)

    def run_now(self, user_id: UUID, *, timezone_name: str | None = None) -> PulseJob:
        job, _pipeline = self.run_with_pipeline(user_id, timezone_name=timezone_name)
        return job

    def process_pending_jobs(
        self,
        *,
        limit: int = 20,
        lease_owner: str = "pulse-worker",
    ) -> list[PulseJob]:
        now = self.now_provider()
        lease_expires_at = now + timedelta(seconds=self.settings.worker_lease_seconds)
        jobs = self.pulse_repository.list_pending_jobs(as_of=now, limit=limit)
        processed_jobs: list[PulseJob] = []
        for job in jobs:
            acquired = self.pulse_repository.acquire_lease(
                job_id=job.id,
                owner=lease_owner,
                lease_expires_at=lease_expires_at,
                as_of=now,
            )
            if not acquired:
                continue
            commit_session(self.session)
            processed_jobs.append(self.process_job(job.id, lease_owner=lease_owner))
        return processed_jobs

    def process_job_with_pipeline(
        self,
        job_id: UUID,
        *,
        lease_owner: str | None = None,
        timezone_name: str | None = None,
    ) -> tuple[PulseJob, PulsePipelineResult]:
        job = self.get_job(job_id)
        with bind_log_context(pulse_job_id=job.id, user_id=job.user_id):
            now = self.now_provider()
            job.status = PulseJobStatus.RUNNING
            job.error = None
            job.started_at = job.started_at or now
            job.completed_at = None
            job.failed_at = None
            if lease_owner is not None:
                job.lease_owner = lease_owner
                job.lease_expires_at = now + timedelta(seconds=self.settings.worker_lease_seconds)
            commit_session(self.session)
            logger.info("pulse job started")

            try:
                pipeline = self._build_pipeline(
                    job.user_id,
                    subscription_policy_id=job.subscription_policy_id,
                    timezone_name=timezone_name,
                )
                cards = [
                    self._persist_card(job, candidate) for candidate in pipeline.selected_candidates
                ]
                self._enqueue_delivery_jobs(job, cards)
                self.digest_service.build_issue_from_cards(
                    user_id=job.user_id,
                    source_job=job,
                    ordered_cards=cards,
                    event_source=SyncEventSource.WORKER,
                    auto_commit=False,
                )
                job.status = PulseJobStatus.COMPLETED
                job.completed_at = self.now_provider()
                job.lease_owner = None
                job.lease_expires_at = None
                commit_session(self.session)
                self.metrics.increment("pulse_jobs_completed_total")
                self.metrics.increment("pulse_cards_selected_total", len(cards))
                yesterday_summary_count = sum(
                    1 for card in cards if card.card_type == PulseCardType.YESTERDAY_SUMMARY
                )
                if yesterday_summary_count:
                    self.metrics.increment(
                        "pulse_yesterday_summary_cards_selected_total",
                        yesterday_summary_count,
                    )
                today_suggestion_count = sum(
                    1 for card in cards if card.card_type == PulseCardType.TODAY_SUGGESTION
                )
                if today_suggestion_count:
                    self.metrics.increment(
                        "pulse_today_suggestion_cards_selected_total",
                        today_suggestion_count,
                    )
                related_paper_count = sum(
                    1 for card in cards if card.card_type == PulseCardType.RELATED_PAPER
                )
                if related_paper_count:
                    self.metrics.increment(
                        "pulse_related_paper_cards_selected_total",
                        related_paper_count,
                    )
                logger.info("pulse job completed", extra={"selected_cards": len(cards)})
            except Exception as exc:
                self.session.rollback()
                failed_job = self.get_job(job_id)
                failed_job.status = PulseJobStatus.FAILED
                failed_job.error = str(exc)
                failed_job.failed_at = self.now_provider()
                failed_job.lease_owner = None
                failed_job.lease_expires_at = None
                commit_session(self.session)
                self.metrics.increment("pulse_jobs_failed_total")
                logger.exception("pulse job failed")
                raise

        self.delivery_service.dispatch_due_jobs()
        return self.get_job(job_id), pipeline

    def process_job(self, job_id: UUID, *, lease_owner: str | None = None) -> PulseJob:
        job, _pipeline = self.process_job_with_pipeline(job_id, lease_owner=lease_owner)
        return job

    def get_job(self, job_id: UUID) -> PulseJob:
        job = self.pulse_repository.get_job(job_id)
        if job is None:
            raise NotFoundError(f"pulse job {job_id} was not found")
        return job

    def build_preview_cards(self, candidates: list[PulseCandidate]) -> list[PulseCardPreview]:
        return [self._candidate_to_preview(candidate) for candidate in candidates]

    def _build_pipeline(
        self,
        user_id: UUID,
        *,
        subscription_policy_id: UUID | None = None,
        timezone_name: str | None = None,
    ) -> PulsePipelineResult:
        self._ensure_user_exists(user_id)
        policies = self._policies_for_pipeline(
            user_id=user_id,
            subscription_policy_id=subscription_policy_id,
        )
        resolved_policy = self._resolve_policy(policies)
        effective_timezone_name = self._resolve_effective_timezone_name(
            user_id=user_id,
            timezone_name=timezone_name,
        )
        facts = list(self.fact_collector.collect(str(user_id)))
        today_suggestion_fact = self._build_today_suggestion_fact(
            user_id=user_id,
            config=resolved_policy.config,
            timezone_name=effective_timezone_name,
        )
        if today_suggestion_fact is not None:
            facts.append(today_suggestion_fact)
            self.metrics.increment("pulse_today_suggestion_candidates_total")
        yesterday_summary_fact = self._build_yesterday_summary_fact(
            user_id=user_id,
            config=resolved_policy.config,
            timezone_name=effective_timezone_name,
        )
        if yesterday_summary_fact is not None:
            facts.append(yesterday_summary_fact)
            self.metrics.increment("pulse_yesterday_summary_candidates_total")
        related_paper_facts = self._build_related_paper_facts(
            user_id=user_id,
            config=resolved_policy.config,
        )
        if related_paper_facts:
            facts.extend(related_paper_facts)
            self.metrics.increment(
                "pulse_related_paper_candidates_total",
                len(related_paper_facts),
            )
        facts = self._filter_facts_for_config(
            sorted(
                facts,
                key=lambda fact: (
                    CARD_TYPE_TIE_BREAK_ORDER[fact.card_type],
                    fact.paper_title.lower(),
                    fact.id,
                ),
            ),
            resolved_policy.config,
        )
        candidates = list(self.rule_engine.generate_candidates(facts))

        recent_signatures = self.pulse_repository.list_recent_card_signatures(
            user_id=user_id,
            since=self.now_provider() - timedelta(hours=resolved_policy.config.dedupe_window_hours),
        )
        recent_yesterday_summary_dates = self.pulse_repository.list_recent_yesterday_summary_dates(
            user_id=user_id,
            since=self.now_provider() - timedelta(hours=resolved_policy.config.dedupe_window_hours),
        )
        recent_today_suggestion_contexts = (
            self.pulse_repository.list_recent_today_suggestion_contexts(
                user_id=user_id,
                since=(
                    self.now_provider()
                    - timedelta(hours=resolved_policy.config.dedupe_window_hours)
                ),
            )
        )
        recent_related_paper_reference_keys = (
            self.pulse_repository.list_recent_related_paper_reference_keys(
                user_id=user_id,
                since=(
                    self.now_provider()
                    - timedelta(days=resolved_policy.config.related_paper_dedupe_days)
                ),
            )
        )
        quiet_hour_window = self._matching_quiet_hours(
            self.now_provider(),
            resolved_policy.config.quiet_hours,
        )

        for candidate in candidates:
            self._score_candidate(candidate, resolved_policy.config)
            self._apply_suppression(
                candidate,
                resolved_policy.config,
                recent_signatures,
                recent_yesterday_summary_dates,
                recent_today_suggestion_contexts,
                recent_related_paper_reference_keys,
                quiet_hour_window,
            )

        selected_candidates, ordering_explanation = self._select_candidates(
            candidates,
            resolved_policy.config,
        )
        return PulsePipelineResult(
            user_id=user_id,
            config=resolved_policy.config,
            facts=facts,
            candidates=candidates,
            selected_candidates=selected_candidates,
            ordering_explanation=ordering_explanation,
        )

    def _policies_for_pipeline(
        self,
        *,
        user_id: UUID,
        subscription_policy_id: UUID | None,
    ) -> list[Any]:
        if subscription_policy_id is None:
            return self.policy_repository.list(user_id=user_id, enabled_only=True)
        policy = self.policy_repository.get(subscription_policy_id)
        if policy is None:
            return []
        return [policy]

    def _filter_facts_for_config(
        self,
        facts: list[PulseFact],
        config: PulseScoringConfig,
    ) -> list[PulseFact]:
        filtered: list[PulseFact] = []
        for fact in facts:
            if fact.card_type == PulseCardType.STALLED_PROGRESS:
                stagnation_days = int(fact.metadata.get("stagnation_days", 0))
                if stagnation_days < config.stale_days:
                    continue
            if fact.card_type == PulseCardType.YESTERDAY_SUMMARY:
                total_events = int(fact.metadata.get("total_events", 0))
                if total_events < config.yesterday_summary_min_events:
                    continue
            filtered.append(fact)
        return filtered

    def _resolve_policy(self, policies: list[Any]) -> ResolvedPulsePolicy:
        stale_days = self.settings.pulse_stale_days
        deadline_horizon_days = self.settings.pulse_deadline_horizon_days
        dedupe_window_hours = self.settings.pulse_dedupe_window_hours
        min_score = self.settings.pulse_min_score
        score_weights = {
            PulseCardType.SIGNAL_CHANGE: self.settings.pulse_weight_signal_change,
            PulseCardType.STALLED_PROGRESS: self.settings.pulse_weight_stalled_progress,
            PulseCardType.DEADLINE_RISK: self.settings.pulse_weight_deadline_risk,
            PulseCardType.TODAY_SUGGESTION: self.settings.pulse_weight_today_suggestion,
            PulseCardType.NEXT_ACTION: self.settings.pulse_weight_next_action,
            PulseCardType.YESTERDAY_SUMMARY: self.settings.pulse_weight_yesterday_summary,
            PulseCardType.RELATED_PAPER: self.settings.pulse_weight_related_paper,
        }
        today_suggestion_stale_days_threshold = (
            self.settings.pulse_today_suggestion_stale_days_threshold
        )
        today_suggestion_priority_bonus = self.settings.pulse_modifier_today_suggestion_priority
        today_suggestion_has_next_action_bonus = (
            self.settings.pulse_modifier_today_suggestion_has_next_action
        )
        today_suggestion_revision_stage_bonus = (
            self.settings.pulse_modifier_today_suggestion_revision_stage
        )
        today_suggestion_stale_progress_bonus = (
            self.settings.pulse_modifier_today_suggestion_stale_progress
        )
        today_suggestion_blocker_present_bonus = (
            self.settings.pulse_modifier_today_suggestion_blocker_present
        )
        yesterday_summary_min_events = self.settings.pulse_yesterday_summary_min_events
        yesterday_summary_activity_diversity_bonus = (
            self.settings.pulse_modifier_yesterday_summary_activity_diversity
        )
        yesterday_summary_multi_paper_bonus = (
            self.settings.pulse_modifier_yesterday_summary_multi_paper
        )
        related_paper_lookback_days = self.settings.pulse_related_paper_lookback_days
        related_paper_max_candidates_per_run = (
            self.settings.pulse_related_paper_max_candidates_per_run
        )
        related_paper_dedupe_days = self.settings.pulse_related_paper_dedupe_days
        related_paper_has_doi_bonus = self.settings.pulse_modifier_related_paper_has_doi
        related_paper_match_reason_count_bonus = (
            self.settings.pulse_modifier_related_paper_match_reason_count
        )
        related_paper_linked_paper_bonus = self.settings.pulse_modifier_related_paper_linked_paper
        related_paper_recent_retrieval_bonus = (
            self.settings.pulse_modifier_related_paper_recent_retrieval
        )
        urgency_modifiers = {
            "recent_signal_delta": self.settings.pulse_modifier_recent_signal_delta,
            "approaching_deadline": self.settings.pulse_modifier_approaching_deadline,
            "long_stagnation": self.settings.pulse_modifier_long_stagnation,
            "explicit_next_action": self.settings.pulse_modifier_explicit_next_action,
        }
        quiet_hours: list[dict[str, Any]] = []
        max_cards_per_run = self.settings.pulse_default_max_cards_per_run
        policy_ids: list[UUID] = []

        if policies:
            policy_ids = [policy.id for policy in policies]
            max_cards_per_run = min(
                policy.frequency_cap for policy in policies if policy.frequency_cap
            )

        for policy in sorted(policies, key=lambda item: (item.created_at, str(item.id))):
            quiet_hours.extend(_normalize_quiet_hours(policy.quiet_hours))
            raw_policy = dict(policy.policy or {})
            overrides = raw_policy.get("pulse", raw_policy)
            if not isinstance(overrides, dict):
                continue
            if "stale_days" in overrides:
                stale_days = int(overrides["stale_days"])
            if "deadline_horizon_days" in overrides:
                deadline_horizon_days = int(overrides["deadline_horizon_days"])
            if "dedupe_window_hours" in overrides:
                dedupe_window_hours = int(overrides["dedupe_window_hours"])
            if "min_score" in overrides:
                min_score = int(overrides["min_score"])
            if "max_cards_per_run" in overrides:
                max_cards_per_run = int(overrides["max_cards_per_run"])
            if "today_suggestion_stale_days_threshold" in overrides:
                today_suggestion_stale_days_threshold = int(
                    overrides["today_suggestion_stale_days_threshold"]
                )
            if "today_suggestion_priority_bonus" in overrides:
                today_suggestion_priority_bonus = int(overrides["today_suggestion_priority_bonus"])
            if "today_suggestion_has_next_action_bonus" in overrides:
                today_suggestion_has_next_action_bonus = int(
                    overrides["today_suggestion_has_next_action_bonus"]
                )
            if "today_suggestion_revision_stage_bonus" in overrides:
                today_suggestion_revision_stage_bonus = int(
                    overrides["today_suggestion_revision_stage_bonus"]
                )
            if "today_suggestion_stale_progress_bonus" in overrides:
                today_suggestion_stale_progress_bonus = int(
                    overrides["today_suggestion_stale_progress_bonus"]
                )
            if "today_suggestion_blocker_present_bonus" in overrides:
                today_suggestion_blocker_present_bonus = int(
                    overrides["today_suggestion_blocker_present_bonus"]
                )
            if "yesterday_summary_min_events" in overrides:
                yesterday_summary_min_events = int(overrides["yesterday_summary_min_events"])
            if "yesterday_summary_activity_diversity_bonus" in overrides:
                yesterday_summary_activity_diversity_bonus = int(
                    overrides["yesterday_summary_activity_diversity_bonus"]
                )
            if "yesterday_summary_multi_paper_bonus" in overrides:
                yesterday_summary_multi_paper_bonus = int(
                    overrides["yesterday_summary_multi_paper_bonus"]
                )
            if "related_paper_lookback_days" in overrides:
                related_paper_lookback_days = int(overrides["related_paper_lookback_days"])
            if "related_paper_max_candidates_per_run" in overrides:
                related_paper_max_candidates_per_run = int(
                    overrides["related_paper_max_candidates_per_run"]
                )
            if "related_paper_dedupe_days" in overrides:
                related_paper_dedupe_days = int(overrides["related_paper_dedupe_days"])
            if "related_paper_has_doi_bonus" in overrides:
                related_paper_has_doi_bonus = int(overrides["related_paper_has_doi_bonus"])
            if "related_paper_match_reason_count_bonus" in overrides:
                related_paper_match_reason_count_bonus = int(
                    overrides["related_paper_match_reason_count_bonus"]
                )
            if "related_paper_linked_paper_bonus" in overrides:
                related_paper_linked_paper_bonus = int(
                    overrides["related_paper_linked_paper_bonus"]
                )
            if "related_paper_recent_retrieval_bonus" in overrides:
                related_paper_recent_retrieval_bonus = int(
                    overrides["related_paper_recent_retrieval_bonus"]
                )
            weight_overrides = overrides.get("score_weights")
            if isinstance(weight_overrides, dict):
                for key, value in weight_overrides.items():
                    card_type = _coerce_card_type(key)
                    if card_type is not None:
                        score_weights[card_type] = int(value)
            modifier_overrides = overrides.get("urgency_modifiers")
            if isinstance(modifier_overrides, dict):
                for key, value in modifier_overrides.items():
                    urgency_modifiers[key] = int(value)

        config = PulseScoringConfig(
            stale_days=stale_days,
            deadline_horizon_days=deadline_horizon_days,
            dedupe_window_hours=dedupe_window_hours,
            min_score=min_score,
            max_cards_per_run=max(1, max_cards_per_run),
            today_suggestion_stale_days_threshold=max(1, today_suggestion_stale_days_threshold),
            today_suggestion_priority_bonus=today_suggestion_priority_bonus,
            today_suggestion_has_next_action_bonus=today_suggestion_has_next_action_bonus,
            today_suggestion_revision_stage_bonus=today_suggestion_revision_stage_bonus,
            today_suggestion_stale_progress_bonus=today_suggestion_stale_progress_bonus,
            today_suggestion_blocker_present_bonus=today_suggestion_blocker_present_bonus,
            yesterday_summary_min_events=max(1, yesterday_summary_min_events),
            yesterday_summary_activity_diversity_bonus=yesterday_summary_activity_diversity_bonus,
            yesterday_summary_multi_paper_bonus=yesterday_summary_multi_paper_bonus,
            related_paper_lookback_days=max(1, related_paper_lookback_days),
            related_paper_max_candidates_per_run=max(1, related_paper_max_candidates_per_run),
            related_paper_dedupe_days=max(1, related_paper_dedupe_days),
            related_paper_has_doi_bonus=related_paper_has_doi_bonus,
            related_paper_match_reason_count_bonus=related_paper_match_reason_count_bonus,
            related_paper_linked_paper_bonus=related_paper_linked_paper_bonus,
            related_paper_recent_retrieval_bonus=related_paper_recent_retrieval_bonus,
            score_weights=score_weights,
            urgency_modifiers=urgency_modifiers,
            quiet_hours=quiet_hours,
        )
        return ResolvedPulsePolicy(config=config, policy_ids=policy_ids)

    def _score_candidate(self, candidate: PulseCandidate, config: PulseScoringConfig) -> None:
        breakdown = ScoreBreakdown(base_weight=config.score_weights[candidate.card_type])

        if candidate.card_type == PulseCardType.TODAY_SUGGESTION:
            priority = int(candidate.candidate_metadata.get("priority", 0))
            suggestion_kind = str(candidate.candidate_metadata.get("suggestion_kind", ""))
            paper_type = str(candidate.candidate_metadata.get("paper_type", ""))
            days_since_last_touch = int(
                candidate.candidate_metadata.get("days_since_last_touch", 0) or 0
            )
            priority_bonus = max(0, priority) * config.today_suggestion_priority_bonus
            if priority_bonus:
                breakdown.modifiers["today_suggestion_priority"] = priority_bonus
            if suggestion_kind == "execute_next_action":
                breakdown.modifiers["today_suggestion_has_next_action"] = (
                    config.today_suggestion_has_next_action_bonus
                )
            if paper_type == PaperType.REVISION.value:
                breakdown.modifiers["today_suggestion_revision_stage"] = (
                    config.today_suggestion_revision_stage_bonus
                )
            if days_since_last_touch >= config.today_suggestion_stale_days_threshold:
                breakdown.modifiers["today_suggestion_stale_progress"] = (
                    config.today_suggestion_stale_progress_bonus
                )
            if suggestion_kind == "resolve_blocker":
                breakdown.modifiers["today_suggestion_blocker_present"] = (
                    config.today_suggestion_blocker_present_bonus
                )

        if candidate.card_type == PulseCardType.YESTERDAY_SUMMARY:
            total_events = int(candidate.candidate_metadata.get("total_events", 0))
            distinct_activity_types = int(
                candidate.candidate_metadata.get("distinct_activity_type_count", 0)
            )
            touched_paper_count = int(candidate.candidate_metadata.get("touched_paper_count", 0))
            event_volume_bonus = min(
                6,
                max(0, total_events - config.yesterday_summary_min_events),
            )
            if event_volume_bonus:
                breakdown.modifiers["yesterday_summary_event_volume"] = event_volume_bonus
            if distinct_activity_types > 1:
                breakdown.modifiers["yesterday_summary_activity_diversity"] = (
                    config.yesterday_summary_activity_diversity_bonus
                )
            if touched_paper_count > 1:
                breakdown.modifiers["yesterday_summary_multi_paper"] = (
                    config.yesterday_summary_multi_paper_bonus
                )

        if candidate.card_type == PulseCardType.RELATED_PAPER:
            if candidate.candidate_metadata.get("doi"):
                breakdown.modifiers["related_paper_has_doi"] = config.related_paper_has_doi_bonus
            match_reason_count = len(
                list(candidate.candidate_metadata.get("matched_reason_codes") or [])
            )
            if match_reason_count:
                breakdown.modifiers["related_paper_match_reason_count"] = (
                    min(3, match_reason_count) * config.related_paper_match_reason_count_bonus
                )
            if candidate.candidate_metadata.get("linked_paper_id"):
                breakdown.modifiers["related_paper_linked_paper"] = (
                    config.related_paper_linked_paper_bonus
                )
            run_finished_at = _parse_datetime(candidate.candidate_metadata.get("run_finished_at"))
            if run_finished_at is not None and (self.now_provider() - run_finished_at).days <= min(
                3, config.related_paper_lookback_days
            ):
                breakdown.modifiers["related_paper_recent_retrieval"] = (
                    config.related_paper_recent_retrieval_bonus
                )

        if candidate.card_type == PulseCardType.SIGNAL_CHANGE:
            signal_age_hours = int(candidate.candidate_metadata.get("hours_since_signal", 999999))
            if signal_age_hours <= config.dedupe_window_hours:
                breakdown.modifiers["recent_signal_delta"] = config.urgency_modifiers[
                    "recent_signal_delta"
                ]

        if candidate.card_type == PulseCardType.DEADLINE_RISK:
            days_until_deadline = int(
                candidate.candidate_metadata.get("days_until_deadline", 999999)
            )
            if days_until_deadline <= config.deadline_horizon_days:
                breakdown.modifiers["approaching_deadline"] = config.urgency_modifiers[
                    "approaching_deadline"
                ]

        stagnation_days = int(candidate.candidate_metadata.get("stagnation_days", 0))
        if stagnation_days >= config.stale_days * 2:
            breakdown.modifiers["long_stagnation"] = config.urgency_modifiers["long_stagnation"]

        if candidate.candidate_metadata.get("explicit_next_action"):
            breakdown.modifiers["explicit_next_action"] = config.urgency_modifiers[
                "explicit_next_action"
            ]

        breakdown.finalize()
        candidate.score_breakdown = breakdown
        candidate.score_total = breakdown.total

    def _apply_suppression(
        self,
        candidate: PulseCandidate,
        config: PulseScoringConfig,
        recent_signatures: set[tuple[str, str]],
        recent_yesterday_summary_dates: set[str],
        recent_today_suggestion_contexts: set[tuple[str, str, str]],
        recent_related_paper_reference_keys: set[str],
        quiet_hour_window: dict[str, Any] | None,
    ) -> None:
        if candidate.candidate_metadata.get("paper_type") == PaperType.PAUSED.value:
            candidate.add_suppression(
                SuppressionReason(
                    code=SuppressionCode.PAUSED_PAPER,
                    message="Paused papers are suppressed before selection.",
                )
            )

        if candidate.score_total < config.min_score:
            candidate.add_suppression(
                SuppressionReason(
                    code=SuppressionCode.LOW_SCORE,
                    message=(
                        f"Candidate score {candidate.score_total} is below the "
                        f"minimum score {config.min_score}."
                    ),
                    details={
                        "score_total": candidate.score_total,
                        "min_score": config.min_score,
                    },
                )
            )

        if quiet_hour_window is not None:
            candidate.add_suppression(
                SuppressionReason(
                    code=SuppressionCode.QUIET_HOURS,
                    message="Candidate falls within active quiet hours.",
                    details=quiet_hour_window,
                )
            )

        if candidate.card_type == PulseCardType.TODAY_SUGGESTION:
            if candidate.source_paper_id is not None:
                context = (
                    str(candidate.source_paper_id),
                    str(candidate.candidate_metadata.get("suggestion_kind", "")),
                    str(candidate.candidate_metadata.get("action_context", "")),
                )
                if context in recent_today_suggestion_contexts:
                    candidate.add_suppression(
                        SuppressionReason(
                            code=SuppressionCode.DEDUPE_WINDOW,
                            message=(
                                "A matching user/paper/suggestion-kind/action-context card "
                                "already exists in the dedupe window."
                            ),
                            details={
                                "card_type": candidate.card_type.value,
                                "source_paper_id": str(candidate.source_paper_id),
                                "suggestion_kind": candidate.candidate_metadata.get(
                                    "suggestion_kind"
                                ),
                                "action_context": candidate.candidate_metadata.get(
                                    "action_context"
                                ),
                                "dedupe_window_hours": config.dedupe_window_hours,
                            },
                        )
                    )
        elif candidate.card_type == PulseCardType.YESTERDAY_SUMMARY:
            summary_date = str(candidate.candidate_metadata.get("summary_date", ""))
            if summary_date and summary_date in recent_yesterday_summary_dates:
                candidate.add_suppression(
                    SuppressionReason(
                        code=SuppressionCode.DEDUPE_WINDOW,
                        message=(
                            "A matching user/card_type/summary_date card already exists "
                            "in the dedupe window."
                        ),
                        details={
                            "card_type": candidate.card_type.value,
                            "summary_date": summary_date,
                            "dedupe_window_hours": config.dedupe_window_hours,
                        },
                    )
                )
        elif candidate.card_type == PulseCardType.RELATED_PAPER:
            external_reference_key = str(
                candidate.candidate_metadata.get("external_reference_key", "")
            )
            if (
                external_reference_key
                and external_reference_key in recent_related_paper_reference_keys
            ):
                candidate.add_suppression(
                    SuppressionReason(
                        code=SuppressionCode.DEDUPE_WINDOW,
                        message=(
                            "A matching user/external-reference related-paper card already "
                            "exists in the dedupe window."
                        ),
                        details={
                            "card_type": candidate.card_type.value,
                            "external_reference_key": external_reference_key,
                            "dedupe_days": config.related_paper_dedupe_days,
                        },
                    )
                )
        elif candidate.source_paper_id is not None:
            signature = (candidate.card_type.value, str(candidate.source_paper_id))
            if signature in recent_signatures:
                candidate.add_suppression(
                    SuppressionReason(
                        code=SuppressionCode.DEDUPE_WINDOW,
                        message=(
                            "A matching user/card_type/paper card already exists "
                            "in the dedupe window."
                        ),
                        details={
                            "card_type": candidate.card_type.value,
                            "source_paper_id": str(candidate.source_paper_id),
                            "dedupe_window_hours": config.dedupe_window_hours,
                        },
                    )
                )

    def _build_yesterday_summary_fact(
        self,
        *,
        user_id: UUID,
        config: PulseScoringConfig,
        timezone_name: str,
    ) -> PulseFact | None:
        snapshot = self.yesterday_summary_builder.build(
            user_id=user_id,
            timezone_name=timezone_name,
            reference=self.now_provider(),
        )
        if snapshot.total_events < config.yesterday_summary_min_events:
            return None
        summary_date = snapshot.summary_date.isoformat()
        touched_paper_ids = [str(item.paper_id) for item in snapshot.touched_papers]
        touched_paper_titles = [item.title for item in snapshot.touched_papers]
        return PulseFact(
            id=f"yesterday_summary:{user_id}:{summary_date}",
            user_id=user_id,
            card_type=PulseCardType.YESTERDAY_SUMMARY,
            source_paper_id=None,
            source_timestamp=snapshot.window_ended_at,
            paper_title="Yesterday summary",
            summary=snapshot.text_summary,
            why_now=f"{summary_date} provides a concise recap before today's work starts.",
            action_text="Review yesterday's momentum before planning today.",
            deep_link=f"/pulse/input-preview/{user_id}",
            evidence_refs=[],
            metadata={
                "summary_date": summary_date,
                "timezone": snapshot.timezone_name,
                "window_started_at": snapshot.window_started_at.isoformat(),
                "window_ended_at": snapshot.window_ended_at.isoformat(),
                "total_events": snapshot.total_events,
                "activity_type_counts": snapshot.activity_type_counts,
                "distinct_activity_type_count": snapshot.distinct_activity_type_count,
                "top_activity_types": snapshot.top_activity_types,
                "touched_paper_ids": touched_paper_ids,
                "touched_paper_titles": touched_paper_titles,
                "touched_paper_count": len(touched_paper_ids),
            },
        )

    def _build_today_suggestion_fact(
        self,
        *,
        user_id: UUID,
        config: PulseScoringConfig,
        timezone_name: str,
    ) -> PulseFact | None:
        decision = self.today_suggestion_builder.build(
            user_id=user_id,
            timezone_name=timezone_name,
            stale_days_threshold=config.today_suggestion_stale_days_threshold,
            reference=self.now_provider(),
        )
        if decision is None:
            return None
        context_signature = hashlib.sha1(
            decision.action_context.encode("utf-8"),
            usedforsecurity=False,
        ).hexdigest()[:12]
        return PulseFact(
            id=(
                f"today_suggestion:{user_id}:{decision.paper_id}:"
                f"{decision.suggestion_kind}:{context_signature}"
            ),
            user_id=user_id,
            card_type=PulseCardType.TODAY_SUGGESTION,
            source_paper_id=decision.paper_id,
            source_timestamp=(
                decision.latest_progress_event_at or decision.last_touch_at or self.now_provider()
            ),
            paper_title=decision.paper_title,
            summary=decision.summary,
            why_now=decision.why_now,
            action_text=decision.action_text,
            deep_link=f"/papers/{decision.paper_id}",
            evidence_refs=[],
            metadata={
                "title": decision.title,
                "suggestion_kind": decision.suggestion_kind,
                "paper_id": str(decision.paper_id),
                "paper_title": decision.paper_title,
                "paper_type": decision.paper_type,
                "stage": decision.stage,
                "priority": decision.priority,
                "next_action": decision.next_action,
                "blocker": decision.blocker,
                "last_touch_at": (
                    decision.last_touch_at.isoformat() if decision.last_touch_at else None
                ),
                "days_since_last_touch": decision.days_since_last_touch,
                "latest_progress_event_at": (
                    decision.latest_progress_event_at.isoformat()
                    if decision.latest_progress_event_at
                    else None
                ),
                "latest_signal_snapshot_at": (
                    decision.latest_signal_snapshot_at.isoformat()
                    if decision.latest_signal_snapshot_at
                    else None
                ),
                "effective_timezone": decision.effective_timezone,
                "considered_paper_count": decision.considered_paper_count,
                "top_reason_codes": decision.top_reason_codes,
                "action_context": decision.action_context,
                "selection_score": decision.selection_score,
            },
        )

    def _build_related_paper_facts(
        self,
        *,
        user_id: UUID,
        config: PulseScoringConfig,
    ) -> list[PulseFact]:
        decisions = self.related_paper_builder.build(
            user_id=user_id,
            lookback_days=config.related_paper_lookback_days,
            max_candidates=config.related_paper_max_candidates_per_run,
            reference=self.now_provider(),
        )
        facts: list[PulseFact] = []
        for decision in decisions:
            facts.append(
                PulseFact(
                    id=(
                        f"related_paper:{decision.external_reference_key}:"
                        f"{decision.external_record_id}"
                    ),
                    user_id=user_id,
                    card_type=PulseCardType.RELATED_PAPER,
                    source_paper_id=decision.linked_paper_id,
                    source_timestamp=decision.source_timestamp,
                    paper_title=decision.title,
                    summary=decision.summary,
                    why_now=decision.why_now,
                    action_text="Review related paper",
                    deep_link=decision.external_url,
                    evidence_refs=[decision.external_url] if decision.external_url else [],
                    metadata={
                        "external_record_id": str(decision.external_record_id),
                        "external_reference_key": decision.external_reference_key,
                        "external_run_id": str(decision.external_run_id),
                        "external_plan_id": str(decision.external_plan_id),
                        "source_kind": decision.source_kind,
                        "retrieval_scope": decision.retrieval_scope,
                        "external_id": decision.external_id,
                        "external_url": decision.external_url,
                        "doi": decision.doi,
                        "title": decision.title,
                        "publication_year": decision.publication_year,
                        "publication_date": decision.publication_date,
                        "source_title": decision.source_title,
                        "authors_summary": decision.authors_summary,
                        "matched_reason_codes": decision.matched_reason_codes,
                        "linked_paper_id": (
                            str(decision.linked_paper_id) if decision.linked_paper_id else None
                        ),
                        "linked_paper_title": decision.linked_paper_title,
                        "run_finished_at": (
                            decision.run_finished_at.isoformat()
                            if decision.run_finished_at
                            else None
                        ),
                        "result_created_at": decision.result_created_at.isoformat(),
                        "top_reason_codes": decision.top_reason_codes,
                    },
                )
            )
        return facts

    def _resolve_effective_timezone_name(
        self,
        *,
        user_id: UUID,
        timezone_name: str | None,
    ) -> str:
        return self.yesterday_summary_builder.resolve_timezone_name(
            user_id=user_id,
            explicit_timezone=timezone_name,
        )

    def _select_candidates(
        self,
        candidates: list[PulseCandidate],
        config: PulseScoringConfig,
    ) -> tuple[list[PulseCandidate], dict[str, Any]]:
        eligible = [candidate for candidate in candidates if not candidate.is_suppressed]
        ordered = sorted(eligible, key=self._candidate_sort_key)
        selected = ordered[: config.max_cards_per_run]

        for rank, candidate in enumerate(
            ordered[config.max_cards_per_run :], start=config.max_cards_per_run + 1
        ):
            candidate.add_suppression(
                SuppressionReason(
                    code=SuppressionCode.FREQUENCY_CAP,
                    message="Candidate was ranked below the frequency cap selection line.",
                    details={
                        "selection_rank": rank,
                        "max_cards_per_run": config.max_cards_per_run,
                    },
                )
            )

        return selected, {
            "sort_fields": [
                "score_total desc",
                "card_type_order asc",
                "source_timestamp desc",
                "paper_title asc",
                "candidate_id asc",
            ],
            "card_type_order": [
                card_type.value
                for card_type, _order in sorted(
                    CARD_TYPE_TIE_BREAK_ORDER.items(),
                    key=lambda item: item[1],
                )
            ],
            "selection_limit": config.max_cards_per_run,
            "ordered_candidate_ids": [candidate.id for candidate in ordered],
            "selected_candidate_ids": [candidate.id for candidate in selected],
        }

    def _candidate_sort_key(self, candidate: PulseCandidate) -> tuple[Any, ...]:
        return (
            -candidate.score_total,
            CARD_TYPE_TIE_BREAK_ORDER[candidate.card_type],
            -int(candidate.source_timestamp.timestamp()),
            candidate.paper_title.lower(),
            candidate.id,
        )

    def _candidate_to_preview(self, candidate: PulseCandidate) -> PulseCardPreview:
        payload = dict(self.model_provider.generate(candidate))
        if not self.card_validator.validate(payload):
            raise ValidationFailedError("generated pulse card failed validation")
        return PulseCardPreview(
            card_type=candidate.card_type,
            source_paper_id=candidate.source_paper_id,
            score_total=candidate.score_total,
            score_breakdown=(
                candidate.score_breakdown.to_dict() if candidate.score_breakdown else None
            ),
            priority=_priority_from_score(candidate.score_total),
            title=str(payload["title"]),
            summary=str(payload["summary"]),
            why_now=str(payload["why_now"]),
            action_text=_maybe_str(payload.get("action_text")),
            deep_link=_maybe_str(payload.get("deep_link")),
            evidence_refs=list(payload.get("evidence_refs", [])),
            generated_by=dict(payload.get("generated_by", {})),
            candidate_metadata=dict(candidate.candidate_metadata),
        )

    def _persist_card(self, job: PulseJob, candidate: PulseCandidate) -> PulseCard:
        preview = self._candidate_to_preview(candidate)
        card = PulseCard(
            pulse_job_id=job.id,
            user_id=job.user_id,
            source_paper_id=preview.source_paper_id,
            card_type=preview.card_type,
            priority=preview.priority,
            score_total=preview.score_total,
            score_breakdown=(
                preview.score_breakdown.model_dump() if preview.score_breakdown else {}
            ),
            title=preview.title,
            summary=preview.summary,
            why_now=preview.why_now,
            action_text=preview.action_text,
            deep_link=preview.deep_link,
            external_reference_key=_maybe_str(
                preview.candidate_metadata.get("external_reference_key")
            ),
            evidence_refs=preview.evidence_refs,
            candidate_metadata=preview.candidate_metadata,
            generated_by=preview.generated_by,
            generated_at=self.now_provider(),
        )
        persisted = self.pulse_repository.add_card(card)
        self.sync_events.emit_pulse_card(
            persisted,
            event_source=SyncEventSource.WORKER,
        )
        return persisted

    def _enqueue_delivery_jobs(self, job: PulseJob, cards: list[PulseCard]) -> list[DeliveryJob]:
        policies = self._delivery_policies_for_job(job)
        delivery_jobs: list[DeliveryJob] = []
        for card in cards:
            for policy in policies:
                delivery_job = DeliveryJob(
                    pulse_card_id=card.id,
                    pulse_job_id=job.id,
                    user_id=job.user_id,
                    channel=policy.channel,
                    endpoint=policy.endpoint or f"{policy.channel.value}://default",
                    idem_key=f"{job.id}:{card.id}:{policy.id}",
                    payload={
                        "card_id": str(card.id),
                        "job_id": str(job.id),
                        "user_id": str(job.user_id),
                        "channel": policy.channel.value,
                        "card_type": card.card_type.value,
                        "source_paper_id": (
                            str(card.source_paper_id) if card.source_paper_id else None
                        ),
                        "score_total": card.score_total,
                        "score_breakdown": card.score_breakdown,
                        "title": card.title,
                        "summary": card.summary,
                        "why_now": card.why_now,
                        "action_text": card.action_text,
                        "deep_link": card.deep_link,
                        "evidence_refs": card.evidence_refs,
                    },
                    status=DeliveryJobStatus.PENDING,
                )
                delivery_jobs.append(self.delivery_repository.add(delivery_job))
        return delivery_jobs

    def _delivery_policies_for_job(self, job: PulseJob) -> list[Any]:
        if job.subscription_policy_id is None:
            return self.policy_repository.list(user_id=job.user_id, enabled_only=True)
        policy = self.policy_repository.get(job.subscription_policy_id)
        if policy is None or not policy.enabled:
            return []
        return [policy]

    def _matching_quiet_hours(
        self,
        now: datetime,
        quiet_hours: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for window in quiet_hours:
            if _quiet_hours_active(window, now):
                return window
        return None

    def _ensure_user_exists(self, user_id: UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")


def _normalize_quiet_hours(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload:
        return []
    windows = payload.get("windows")
    if isinstance(windows, list):
        normalized = []
        for window in windows:
            if isinstance(window, dict):
                merged = dict(window)
                if "timezone" not in merged and "timezone" in payload:
                    merged["timezone"] = payload["timezone"]
                normalized.append(merged)
        return normalized
    return [payload]


def _quiet_hours_active(window: dict[str, Any], now: datetime) -> bool:
    start = window.get("start")
    end = window.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        return False
    timezone_name = str(window.get("timezone", "UTC"))
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    localized = now.astimezone(zone)
    start_time = time.fromisoformat(start)
    end_time = time.fromisoformat(end)
    current_time = localized.time().replace(tzinfo=None)
    if start_time <= end_time:
        return start_time <= current_time < end_time
    return current_time >= start_time or current_time < end_time


def _coerce_card_type(value: str) -> PulseCardType | None:
    try:
        return PulseCardType(value)
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _coerce_utc(value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return _coerce_utc(datetime.fromisoformat(normalized))
        except ValueError:
            return None
    return None


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _priority_from_score(score_total: int) -> int:
    if score_total >= 30:
        return 5
    if score_total >= 20:
        return 4
    if score_total >= 15:
        return 3
    if score_total >= 10:
        return 2
    return 1


def _maybe_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)
