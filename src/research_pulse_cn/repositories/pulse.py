"""Pulse job and card repositories."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import DeliveryJob, PulseCard, PulseJob
from research_pulse_cn.domain.enums import PulseCardType, PulseJobScheduledReason, PulseJobStatus


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
                selectinload(PulseJob.subscription_policy),
                selectinload(PulseJob.source_pulse_job),
            )
            .where(PulseJob.id == job_id)
        )
        return self.session.scalar(statement)

    def list_pending_jobs(self, *, as_of: datetime, limit: int = 20) -> list[PulseJob]:
        statement = (
            select(PulseJob)
            .where(
                PulseJob.status == PulseJobStatus.PENDING,
                PulseJob.scheduled_for <= as_of,
                or_(
                    PulseJob.lease_expires_at.is_(None),
                    PulseJob.lease_expires_at <= as_of,
                ),
            )
            .order_by(PulseJob.scheduled_for.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add_card(self, card: PulseCard) -> PulseCard:
        self.session.add(card)
        self.session.flush()
        self.session.refresh(card)
        return card

    def get_by_schedule_key(self, schedule_key: str) -> PulseJob | None:
        statement = select(PulseJob).where(PulseJob.schedule_key == schedule_key)
        return self.session.scalar(statement)

    def acquire_lease(
        self,
        *,
        job_id: UUID,
        owner: str,
        lease_expires_at: datetime,
        as_of: datetime,
    ) -> bool:
        statement = (
            update(PulseJob)
            .where(
                PulseJob.id == job_id,
                PulseJob.status == PulseJobStatus.PENDING,
                or_(
                    PulseJob.lease_expires_at.is_(None),
                    PulseJob.lease_expires_at <= as_of,
                ),
            )
            .values(lease_owner=owner, lease_expires_at=lease_expires_at)
        )
        result = self.session.execute(statement)
        self.session.flush()
        return result.rowcount > 0

    def list_jobs(
        self,
        *,
        user_id: UUID | None = None,
        status: PulseJobStatus | None = None,
        scheduled_reason: PulseJobScheduledReason | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PulseJob]:
        statement = (
            select(PulseJob)
            .options(
                selectinload(PulseJob.cards),
                selectinload(PulseJob.delivery_jobs),
                selectinload(PulseJob.subscription_policy),
            )
            .order_by(PulseJob.created_at.desc())
            .limit(limit)
        )
        if user_id:
            statement = statement.where(PulseJob.user_id == user_id)
        if status:
            statement = statement.where(PulseJob.status == status)
        if scheduled_reason:
            statement = statement.where(PulseJob.scheduled_reason == scheduled_reason)
        if since:
            statement = statement.where(PulseJob.created_at >= since)
        return list(self.session.scalars(statement))

    def find_active_replay(self, source_pulse_job_id: UUID) -> PulseJob | None:
        statement = (
            select(PulseJob)
            .where(
                PulseJob.source_pulse_job_id == source_pulse_job_id,
                PulseJob.scheduled_reason == PulseJobScheduledReason.REPLAY,
                PulseJob.status.in_([PulseJobStatus.PENDING, PulseJobStatus.RUNNING]),
            )
            .order_by(PulseJob.created_at.desc())
        )
        return self.session.scalar(statement)

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

    def list_recent_yesterday_summary_dates(
        self,
        *,
        user_id: UUID,
        since: datetime,
    ) -> set[str]:
        statement = (
            select(PulseCard)
            .outerjoin(DeliveryJob, DeliveryJob.pulse_card_id == PulseCard.id)
            .where(
                PulseCard.user_id == user_id,
                PulseCard.card_type == PulseCardType.YESTERDAY_SUMMARY,
                or_(
                    PulseCard.generated_at >= since,
                    DeliveryJob.created_at >= since,
                    DeliveryJob.sent_at >= since,
                ),
            )
        )
        summary_dates: set[str] = set()
        for card in self.session.scalars(statement):
            metadata = card.candidate_metadata if isinstance(card.candidate_metadata, dict) else {}
            summary_date = metadata.get("summary_date")
            if isinstance(summary_date, str) and summary_date:
                summary_dates.add(summary_date)
        return summary_dates
