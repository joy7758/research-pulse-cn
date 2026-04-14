"""Pulse job and card repositories."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import PulseCard, PulseJob
from research_pulse_cn.domain.enums import PulseJobStatus


class PulseRepository:
    """Persistence operations for pulse jobs and pulse cards."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, job: PulseJob) -> PulseJob:
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job

    def get_job(self, job_id: UUID) -> PulseJob | None:
        statement = (
            select(PulseJob)
            .execution_options(populate_existing=True)
            .options(selectinload(PulseJob.cards), selectinload(PulseJob.delivery_jobs))
            .where(PulseJob.id == job_id)
        )
        return self.session.scalar(statement)

    def list_pending_jobs(self, *, as_of: datetime, limit: int = 20) -> list[PulseJob]:
        statement = (
            select(PulseJob)
            .where(PulseJob.status == PulseJobStatus.PENDING, PulseJob.scheduled_for <= as_of)
            .order_by(PulseJob.scheduled_for.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add_card(self, card: PulseCard) -> PulseCard:
        self.session.add(card)
        self.session.flush()
        self.session.refresh(card)
        return card
