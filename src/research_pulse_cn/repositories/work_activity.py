"""Persistence operations for work activity events."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import PaperProfile, WorkActivityEvent
from research_pulse_cn.domain.enums import WorkActivityType


class WorkActivityRepository:
    """Persistence operations for work activity events."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: WorkActivityEvent) -> WorkActivityEvent:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def list(
        self,
        *,
        user_id: UUID | None = None,
        paper_id: UUID | None = None,
        activity_type: WorkActivityType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[WorkActivityEvent]:
        statement = (
            select(WorkActivityEvent)
            .options(selectinload(WorkActivityEvent.paper))
            .order_by(WorkActivityEvent.happened_at.desc(), WorkActivityEvent.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(WorkActivityEvent.user_id == user_id)
        if paper_id is not None:
            statement = statement.where(WorkActivityEvent.paper_id == paper_id)
        if activity_type is not None:
            statement = statement.where(WorkActivityEvent.activity_type == activity_type)
        if date_from is not None:
            statement = statement.where(WorkActivityEvent.happened_at >= _start_of_day(date_from))
        if date_to is not None:
            statement = statement.where(WorkActivityEvent.happened_at < _start_of_next_day(date_to))
        return list(self.session.scalars(statement))

    def list_window_for_user(
        self,
        *,
        user_id: UUID,
        started_at: datetime,
        ended_at: datetime,
    ) -> list[WorkActivityEvent]:
        statement = (
            select(WorkActivityEvent)
            .options(selectinload(WorkActivityEvent.paper))
            .where(
                WorkActivityEvent.user_id == user_id,
                WorkActivityEvent.happened_at >= started_at,
                WorkActivityEvent.happened_at < ended_at,
            )
            .order_by(WorkActivityEvent.happened_at.desc(), WorkActivityEvent.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def paper_titles(self, paper_ids: set[UUID]) -> dict[UUID, str]:
        if not paper_ids:
            return {}
        statement = select(PaperProfile.id, PaperProfile.title).where(
            PaperProfile.id.in_(paper_ids)
        )
        return {paper_id: title for paper_id, title in self.session.execute(statement)}


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _start_of_next_day(value: date) -> datetime:
    return _start_of_day(value + timedelta(days=1))
