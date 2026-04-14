"""Pulse engine, orchestration, and worker flow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.adapters.channels.registry import ChannelAdapterRegistry
from research_pulse_cn.adapters.models.dummy import DummyModelProvider
from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.db.models import DeliveryJob, PulseCard, PulseJob
from research_pulse_cn.db.models import utcnow as db_utcnow
from research_pulse_cn.domain.contracts import (
    CardValidator,
    FactCollector,
    ModelProvider,
    RuleEngine,
)
from research_pulse_cn.domain.enums import (
    DeliveryJobStatus,
    PulseCardType,
    PulseJobStatus,
)
from research_pulse_cn.repositories.delivery import DeliveryRepository
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.pulse import PulseCardPreview
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.delivery import DeliveryService


@dataclass(slots=True)
class PulseDraft:
    """Internal pulse card draft."""

    card_type: PulseCardType
    priority: int
    title: str
    summary: str
    why_now: str
    action_text: str | None
    deep_link: str | None
    evidence_refs: list[str]
    generated_by: dict[str, Any]
    paper_id: UUID

    def to_preview(self) -> PulseCardPreview:
        return PulseCardPreview(
            card_type=self.card_type,
            priority=self.priority,
            title=self.title,
            summary=self.summary,
            why_now=self.why_now,
            action_text=self.action_text,
            deep_link=self.deep_link,
            evidence_refs=self.evidence_refs,
            generated_by=self.generated_by,
            paper_id=self.paper_id,
        )


class DeterministicFactCollector(FactCollector):
    """Build deterministic pulse facts from current paper state."""

    def __init__(self, session: Session) -> None:
        self.paper_repository = PaperRepository(session)

    def collect(self, subject_id: str) -> list[dict[str, Any]]:
        user_id = UUID(subject_id)
        now = db_utcnow()
        facts: list[dict[str, Any]] = []

        for paper in self.paper_repository.list(user_id=user_id):
            if paper.next_action:
                facts.append(
                    {
                        "card_type": PulseCardType.NEXT_ACTION,
                        "priority": min(paper.priority + 1, 5),
                        "paper_id": paper.id,
                        "paper_title": paper.title,
                        "summary": paper.next_action,
                        "why_now": f"{paper.title} already has a defined next action.",
                        "action_text": paper.next_action,
                        "deep_link": f"/papers/{paper.id}",
                        "evidence_refs": paper.source_links[:3],
                    }
                )

            latest_touch = paper.last_touch_at or paper.created_at
            if latest_touch and latest_touch.tzinfo is None:
                latest_touch = latest_touch.replace(tzinfo=UTC)
            if now - latest_touch >= timedelta(days=14):
                stalled_summary = (
                    f"No material update has been recorded since {latest_touch.date().isoformat()}."
                )
                facts.append(
                    {
                        "card_type": PulseCardType.STALLED_PROGRESS,
                        "priority": min(paper.priority + 2, 5),
                        "paper_id": paper.id,
                        "paper_title": paper.title,
                        "summary": stalled_summary,
                        "why_now": "The paper may be stuck and requires owner attention.",
                        "action_text": "Review blockers and schedule the next move.",
                        "deep_link": f"/papers/{paper.id}",
                        "evidence_refs": paper.source_links[:3],
                    }
                )

            snapshots = sorted(paper.signal_snapshots, key=lambda item: item.fetched_at)
            if len(snapshots) >= 2:
                previous = snapshots[-2]
                latest = snapshots[-1]
                signal_deltas: list[str] = []
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
                        signal_deltas.append(f"{label}: {previous_value} -> {latest_value}")
                if previous.inclusion_status != latest.inclusion_status and latest.inclusion_status:
                    inclusion_transition = (
                        "inclusion status: "
                        f"{previous.inclusion_status or 'unknown'}"
                        f" -> {latest.inclusion_status}"
                    )
                    signal_deltas.append(inclusion_transition)
                if signal_deltas:
                    facts.append(
                        {
                            "card_type": PulseCardType.SIGNAL_CHANGE,
                            "priority": min(paper.priority + 2, 5),
                            "paper_id": paper.id,
                            "paper_title": paper.title,
                            "summary": "; ".join(signal_deltas),
                            "why_now": (
                                "External paper signals changed since the previous snapshot."
                            ),
                            "action_text": "Review the new signal trend.",
                            "deep_link": f"/papers/{paper.id}",
                            "evidence_refs": paper.source_links[:3],
                        }
                    )
        return facts


class DeterministicRuleEngine(RuleEngine):
    """Select the highest-priority deterministic pulse facts."""

    def select(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[tuple[UUID, PulseCardType], dict[str, Any]] = {}
        for fact in facts:
            key = (fact["paper_id"], fact["card_type"])
            current = deduped.get(key)
            if current is None or fact["priority"] > current["priority"]:
                deduped[key] = fact
        ordered = sorted(
            deduped.values(),
            key=lambda fact: (-fact["priority"], fact["paper_title"], fact["card_type"].value),
        )
        return ordered[:10]


class SimpleCardValidator(CardValidator):
    """Reject incomplete deterministic cards before persistence."""

    def validate(self, payload: dict[str, Any]) -> bool:
        required_fields = ("title", "summary", "why_now", "card_type", "priority")
        return all(payload.get(field) for field in required_fields)


class PulseService:
    """Orchestrate pulse preview, queueing, processing, and dispatch."""

    def __init__(
        self,
        session: Session,
        *,
        fact_collector: FactCollector | None = None,
        rule_engine: RuleEngine | None = None,
        model_provider: ModelProvider | None = None,
        card_validator: CardValidator | None = None,
        adapter_registry: ChannelAdapterRegistry | None = None,
    ) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.pulse_repository = PulseRepository(session)
        self.policy_repository = SubscriptionPolicyRepository(session)
        self.delivery_repository = DeliveryRepository(session)
        self.fact_collector = fact_collector or DeterministicFactCollector(session)
        self.rule_engine = rule_engine or DeterministicRuleEngine()
        self.model_provider = model_provider or DummyModelProvider()
        self.card_validator = card_validator or SimpleCardValidator()
        self.delivery_service = DeliveryService(session, adapter_registry=adapter_registry)

    def preview(self, user_id: UUID) -> list[PulseDraft]:
        self._ensure_user_exists(user_id)
        facts = self.fact_collector.collect(str(user_id))
        selected_facts = self.rule_engine.select(facts)
        return [self._fact_to_draft(fact) for fact in selected_facts]

    def enqueue_run(self, user_id: UUID) -> PulseJob:
        self._ensure_user_exists(user_id)
        job = PulseJob(user_id=user_id, scheduled_for=db_utcnow(), status=PulseJobStatus.PENDING)
        self.pulse_repository.add_job(job)
        commit_session(self.session)
        return self.pulse_repository.get_job(job.id) or job

    def run_now(self, user_id: UUID) -> PulseJob:
        job = self.enqueue_run(user_id)
        self.process_job(job.id)
        return self.get_job(job.id)

    def process_pending_jobs(self, *, limit: int = 20) -> list[PulseJob]:
        jobs = self.pulse_repository.list_pending_jobs(as_of=db_utcnow(), limit=limit)
        for job in jobs:
            self.process_job(job.id)
        return [self.get_job(job.id) for job in jobs]

    def process_job(self, job_id: UUID) -> PulseJob:
        job = self.get_job(job_id)
        job.status = PulseJobStatus.RUNNING
        job.error = None
        commit_session(self.session)

        try:
            drafts = self.preview(job.user_id)
            cards = [self._persist_card(job, draft) for draft in drafts]
            self._enqueue_delivery_jobs(job, cards)
            job.status = PulseJobStatus.COMPLETED
            commit_session(self.session)
        except Exception as exc:
            self.session.rollback()
            failed_job = self.get_job(job_id)
            failed_job.status = PulseJobStatus.FAILED
            failed_job.error = str(exc)
            commit_session(self.session)
            raise

        self.delivery_service.dispatch_due_jobs()
        return self.get_job(job_id)

    def get_job(self, job_id: UUID) -> PulseJob:
        job = self.pulse_repository.get_job(job_id)
        if job is None:
            raise NotFoundError(f"pulse job {job_id} was not found")
        return job

    def _ensure_user_exists(self, user_id: UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")

    def _fact_to_draft(self, fact: dict[str, Any]) -> PulseDraft:
        payload = dict(self.model_provider.generate(fact))
        if not self.card_validator.validate(payload):
            raise ValidationFailedError("generated pulse card failed validation")
        return PulseDraft(
            card_type=payload["card_type"],
            priority=payload["priority"],
            title=payload["title"],
            summary=payload["summary"],
            why_now=payload["why_now"],
            action_text=payload.get("action_text"),
            deep_link=payload.get("deep_link"),
            evidence_refs=list(payload.get("evidence_refs", [])),
            generated_by=dict(payload.get("generated_by", {})),
            paper_id=fact["paper_id"],
        )

    def _persist_card(self, job: PulseJob, draft: PulseDraft) -> PulseCard:
        card = PulseCard(
            pulse_job_id=job.id,
            user_id=job.user_id,
            card_type=draft.card_type,
            priority=draft.priority,
            title=draft.title,
            summary=draft.summary,
            why_now=draft.why_now,
            action_text=draft.action_text,
            deep_link=draft.deep_link,
            evidence_refs=draft.evidence_refs,
            generated_by=draft.generated_by,
            generated_at=db_utcnow(),
        )
        return self.pulse_repository.add_card(card)

    def _enqueue_delivery_jobs(self, job: PulseJob, cards: list[PulseCard]) -> list[DeliveryJob]:
        policies = self.policy_repository.list(user_id=job.user_id, enabled_only=True)
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
        commit_session(self.session)
        return delivery_jobs
