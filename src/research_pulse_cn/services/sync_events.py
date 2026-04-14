"""Sync event emission service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db.models import (
    PaperProfile,
    ProgressEvent,
    PulseCard,
    PulseDigestIssue,
    SignalSnapshot,
    SubscriptionPolicy,
    SyncEvent,
    utcnow,
)
from research_pulse_cn.domain.enums import SyncEventSource, SyncEventType
from research_pulse_cn.repositories.sync import SyncRepository


class SyncEventService:
    """Emit compact sync events in the same transaction as source writes."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SyncRepository(session)
        self.metrics = get_metrics()

    def emit_paper_profile(
        self,
        paper: PaperProfile,
        *,
        event_type: SyncEventType,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=paper.user_id,
            entity_type="paper_profile",
            entity_id=str(paper.id),
            event_type=event_type,
            event_source=event_source,
            payload={
                "id": str(paper.id),
                "user_id": str(paper.user_id),
                "title": paper.title,
                "type": paper.type.value,
                "stage": paper.stage,
                "venue": paper.venue,
                "last_touch_at": _iso_or_none(paper.last_touch_at),
                "next_action": paper.next_action,
                "blocker": paper.blocker,
                "priority": paper.priority,
                "updated_at": _iso_or_none(paper.updated_at),
            },
        )

    def emit_progress_event(
        self,
        progress_event: ProgressEvent,
        *,
        user_id: UUID,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=user_id,
            entity_type="progress_event",
            entity_id=str(progress_event.id),
            event_type=SyncEventType.CREATED,
            event_source=event_source,
            payload={
                "id": str(progress_event.id),
                "paper_id": str(progress_event.paper_id),
                "stage": progress_event.stage,
                "happened_at": progress_event.happened_at.isoformat(),
                "summary": progress_event.summary,
                "evidence_links": list(progress_event.evidence_links),
                "owner": progress_event.owner,
            },
        )

    def emit_signal_snapshot(
        self,
        signal_snapshot: SignalSnapshot,
        *,
        user_id: UUID,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=user_id,
            entity_type="signal_snapshot",
            entity_id=str(signal_snapshot.id),
            event_type=SyncEventType.CREATED,
            event_source=event_source,
            payload={
                "id": str(signal_snapshot.id),
                "paper_id": str(signal_snapshot.paper_id),
                "source": signal_snapshot.source.value,
                "citation_count": signal_snapshot.citation_count,
                "download_count": signal_snapshot.download_count,
                "read_count": signal_snapshot.read_count,
                "inclusion_status": signal_snapshot.inclusion_status,
                "fetched_at": signal_snapshot.fetched_at.isoformat(),
            },
        )

    def emit_subscription_policy(
        self,
        policy: SubscriptionPolicy,
        *,
        event_type: SyncEventType,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=policy.user_id,
            entity_type="subscription_policy",
            entity_id=str(policy.id),
            event_type=event_type,
            event_source=event_source,
            payload={
                "id": str(policy.id),
                "user_id": str(policy.user_id),
                "channel": policy.channel.value,
                "enabled": policy.enabled,
                "frequency": policy.frequency.value,
                "quiet_hours": policy.quiet_hours,
                "frequency_cap": policy.frequency_cap,
                "endpoint": policy.endpoint,
                "policy": dict(policy.policy or {}),
                "updated_at": _iso_or_none(policy.updated_at),
            },
        )

    def emit_pulse_card(
        self,
        pulse_card: PulseCard,
        *,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=pulse_card.user_id,
            entity_type="pulse_card",
            entity_id=str(pulse_card.id),
            event_type=SyncEventType.CREATED,
            event_source=event_source,
            payload={
                "id": str(pulse_card.id),
                "pulse_job_id": str(pulse_card.pulse_job_id),
                "user_id": str(pulse_card.user_id),
                "source_paper_id": (
                    str(pulse_card.source_paper_id) if pulse_card.source_paper_id else None
                ),
                "card_type": pulse_card.card_type.value,
                "score_total": pulse_card.score_total,
                "title": pulse_card.title,
                "summary": pulse_card.summary,
                "generated_at": pulse_card.generated_at.isoformat(),
            },
        )

    def emit_pulse_digest_issue(
        self,
        digest_issue: PulseDigestIssue,
        *,
        event_type: SyncEventType,
        event_source: SyncEventSource,
    ) -> SyncEvent:
        return self._emit(
            user_id=digest_issue.user_id,
            entity_type="pulse_digest_issue",
            entity_id=str(digest_issue.id),
            event_type=event_type,
            event_source=event_source,
            payload={
                "id": str(digest_issue.id),
                "user_id": str(digest_issue.user_id),
                "issue_date": digest_issue.issue_date.isoformat(),
                "source_pulse_job_id": (
                    None
                    if digest_issue.source_pulse_job_id is None
                    else str(digest_issue.source_pulse_job_id)
                ),
                "status": digest_issue.status.value,
                "title": digest_issue.title,
                "summary": digest_issue.summary,
                "highlight_count": digest_issue.highlight_count,
                "selected_card_count": digest_issue.selected_card_count,
                "deep_link_path": digest_issue.deep_link_path,
                "updated_at": _iso_or_none(digest_issue.updated_at),
            },
        )

    def get_latest_event_for_entity(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: str,
    ) -> SyncEvent | None:
        return self.repository.get_latest_event_for_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def _emit(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: str,
        event_type: SyncEventType,
        event_source: SyncEventSource,
        payload: dict[str, Any],
    ) -> SyncEvent:
        event = SyncEvent(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload,
            event_source=event_source,
            occurred_at=utcnow(),
        )
        emitted = self.repository.add_event(event)
        self.metrics.increment("sync_events_emitted_total")
        return emitted


def _iso_or_none(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()
