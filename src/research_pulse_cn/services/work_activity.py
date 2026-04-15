"""Services for lightweight user work activity capture and preview."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import WorkActivityEvent, utcnow
from research_pulse_cn.domain.enums import SyncEventSource, WorkActivitySource, WorkActivityType
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.repositories.work_activity import WorkActivityRepository
from research_pulse_cn.schemas.pulse_input import (
    WorkActivitySummaryRead,
    WorkActivityTouchedPaperRead,
)

logger = logging.getLogger(__name__)

DESKTOP_WORK_ACTIVITY_TYPES = frozenset(
    {
        WorkActivityType.ATTACHMENT_IMPORTED,
        WorkActivityType.NOTE_CREATED,
        WorkActivityType.NOTE_SAVED,
        WorkActivityType.REVIEW_ROUND_CREATED,
        WorkActivityType.REVIEWER_MATRIX_GENERATED,
        WorkActivityType.RESPONSE_LETTER_GENERATED,
    }
)


class WorkActivityService:
    """Record and summarize user work activity."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = WorkActivityRepository(session)
        self.user_repository = UserRepository(session)
        self.paper_repository = PaperRepository(session)
        self.metrics = get_metrics()

    def record_event(
        self,
        *,
        user_id: UUID,
        paper_id: UUID | None,
        activity_type: WorkActivityType,
        summary: str,
        metadata: dict | None = None,
        happened_at: datetime | None = None,
        source: WorkActivitySource,
    ) -> WorkActivityEvent:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")
        if paper_id is not None:
            paper = self.paper_repository.get(paper_id)
            if paper is None or paper.user_id != user_id:
                raise NotFoundError(f"paper {paper_id} was not found")

        clean_summary = summary.strip()
        if not clean_summary:
            raise ValidationFailedError("work activity summary must not be empty")

        event = WorkActivityEvent(
            user_id=user_id,
            paper_id=paper_id,
            activity_type=activity_type,
            summary=clean_summary,
            metadata_json=dict(metadata or {}) or None,
            happened_at=_coerce_utc(happened_at or utcnow()),
            source=source,
        )
        self.repository.add(event)
        self.metrics.increment("work_activity_events_recorded_total")
        with bind_log_context(user_id=user_id):
            logger.info(
                "recorded work activity event",
                extra={
                    "paper_id": str(paper_id) if paper_id else None,
                    "activity_type": activity_type.value,
                },
            )
        return event

    def list_events(
        self,
        *,
        user_id: UUID | None = None,
        paper_id: UUID | None = None,
        activity_type: WorkActivityType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[WorkActivityEvent]:
        return self.repository.list(
            user_id=user_id,
            paper_id=paper_id,
            activity_type=activity_type,
            date_from=date_from,
            date_to=date_to,
        )

    def previous_day_window(
        self,
        *,
        reference: datetime | None = None,
    ) -> tuple[date, datetime, datetime]:
        current = _coerce_utc(reference or utcnow())
        preview_date = (current - timedelta(days=1)).date()
        started_at = datetime.combine(preview_date, time.min, tzinfo=UTC)
        ended_at = started_at + timedelta(days=1)
        return preview_date, started_at, ended_at

    def summarize_window(
        self,
        *,
        user_id: UUID,
        started_at: datetime,
        ended_at: datetime,
    ) -> WorkActivitySummaryRead:
        events = self.repository.list_window_for_user(
            user_id=user_id,
            started_at=_coerce_utc(started_at),
            ended_at=_coerce_utc(ended_at),
        )
        return self._build_summary(
            events,
            started_at=_coerce_utc(started_at),
            ended_at=_coerce_utc(ended_at),
        )

    def summary_and_events_for_previous_day(
        self,
        *,
        user_id: UUID,
    ) -> tuple[date, datetime, datetime, WorkActivitySummaryRead, list[WorkActivityEvent]]:
        preview_date, started_at, ended_at = self.previous_day_window()
        events = self.repository.list_window_for_user(
            user_id=user_id,
            started_at=started_at,
            ended_at=ended_at,
        )
        return (
            preview_date,
            started_at,
            ended_at,
            self._build_summary(events, started_at=started_at, ended_at=ended_at),
            events,
        )

    def validate_desktop_activity_type(self, activity_type: WorkActivityType) -> None:
        if activity_type not in DESKTOP_WORK_ACTIVITY_TYPES:
            allowed = ", ".join(sorted(item.value for item in DESKTOP_WORK_ACTIVITY_TYPES))
            raise ValidationFailedError(
                f"work_activity.record activity_type must be one of: {allowed}"
            )

    @staticmethod
    def source_from_event_source(event_source: SyncEventSource) -> WorkActivitySource:
        if event_source == SyncEventSource.API:
            return WorkActivitySource.API
        if event_source == SyncEventSource.SYNC_PUSH:
            return WorkActivitySource.SYNC_MUTATION
        return WorkActivitySource.SYSTEM

    def _build_summary(
        self,
        events: list[WorkActivityEvent],
        *,
        started_at: datetime,
        ended_at: datetime,
    ) -> WorkActivitySummaryRead:
        type_counts = Counter(event.activity_type.value for event in events)
        paper_counts = Counter(event.paper_id for event in events if event.paper_id is not None)
        paper_titles = self.repository.paper_titles(set(paper_counts))
        touched_papers = [
            WorkActivityTouchedPaperRead(
                paper_id=paper_id,
                title=paper_titles.get(paper_id, str(paper_id)),
                activity_count=count,
            )
            for paper_id, count in sorted(
                paper_counts.items(),
                key=lambda item: (-item[1], paper_titles.get(item[0], str(item[0])).lower()),
            )
        ]
        return WorkActivitySummaryRead(
            window_started_at=started_at,
            window_ended_at=ended_at,
            total_events=len(events),
            activity_type_counts=dict(sorted(type_counts.items())),
            touched_papers=touched_papers,
        )


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
