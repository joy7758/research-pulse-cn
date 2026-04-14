"""Pulse job and card repositories."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import DeliveryJob, PulseCard, PulseJob
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
            .options(
                selectinload(PulseJob.cards).selectinload(PulseCard.source_paper),
                selectinload(PulseJob.delivery_jobs),
            )
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

    def list_recent_card_signatures(
        self,
        *,
        user_id: UUID,
        since: datetime,
    ) -> set[tuple[str, str]]:
        statement = (
            select(PulseCard)
            .outerjoin(DeliveryJob, DeliveryJob.pulse_card_id == PulseCard.id)
            .where(
                PulseCard.user_id == user_id,
                PulseCard.source_paper_id.is_not(None),
                or_(
                    PulseCard.generated_at >= since,
                    DeliveryJob.created_at >= since,
                    DeliveryJob.sent_at >= since,
                ),
            )
        )
        signatures: set[tuple[str, str]] = set()
        for card in self.session.scalars(statement):
            if card.source_paper_id is None:
                continue
            signatures.add((card.card_type.value, str(card.source_paper_id)))
        return signatures
