"""Delivery repository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from research_pulse_cn.db.models import DeliveryJob
from research_pulse_cn.domain.enums import DeliveryJobStatus


class DeliveryRepository:
    """Persistence operations for outbox delivery jobs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        user_id: UUID | None = None,
        status: DeliveryJobStatus | None = None,
    ) -> list[DeliveryJob]:
        statement = select(DeliveryJob).order_by(DeliveryJob.created_at.desc())
        if user_id:
            statement = statement.where(DeliveryJob.user_id == user_id)
        if status:
            statement = statement.where(DeliveryJob.status == status)
        return list(self.session.scalars(statement))

    def get(self, delivery_job_id: UUID) -> DeliveryJob | None:
        return self.session.get(DeliveryJob, delivery_job_id)

    def add(self, delivery_job: DeliveryJob) -> DeliveryJob:
        self.session.add(delivery_job)
        self.session.flush()
        self.session.refresh(delivery_job)
        return delivery_job

    def list_due(self, *, as_of: datetime, limit: int = 50) -> list[DeliveryJob]:
        statement = (
            select(DeliveryJob)
            .where(
                or_(
                    DeliveryJob.status == DeliveryJobStatus.PENDING,
                    and_(
                        DeliveryJob.status == DeliveryJobStatus.FAILED,
                        DeliveryJob.next_retry_at.is_not(None),
                        DeliveryJob.next_retry_at <= as_of,
                    ),
                )
            )
            .order_by(DeliveryJob.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
