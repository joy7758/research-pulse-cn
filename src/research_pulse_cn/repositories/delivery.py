"""Delivery repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import DeliveryAttempt, DeliveryJob
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
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[DeliveryJob]:
        statement = (
            select(DeliveryJob)
            .options(selectinload(DeliveryJob.attempts))
            .order_by(DeliveryJob.created_at.desc())
            .limit(limit)
        )
        if user_id:
            statement = statement.where(DeliveryJob.user_id == user_id)
        if status:
            statement = statement.where(DeliveryJob.status == status)
        if since:
            statement = statement.where(DeliveryJob.created_at >= since)
        return list(self.session.scalars(statement))

    def get(self, delivery_job_id: UUID) -> DeliveryJob | None:
        statement = (
            select(DeliveryJob)
            .options(selectinload(DeliveryJob.attempts))
            .where(DeliveryJob.id == delivery_job_id)
        )
        return self.session.scalar(statement)

    def add(self, delivery_job: DeliveryJob) -> DeliveryJob:
        self.session.add(delivery_job)
        self.session.flush()
        self.session.refresh(delivery_job)
        return delivery_job

    def add_attempt(self, attempt: DeliveryAttempt) -> DeliveryAttempt:
        self.session.add(attempt)
        self.session.flush()
        self.session.refresh(attempt)
        return attempt

    def list_attempts(
        self,
        *,
        delivery_job_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[DeliveryAttempt]:
        statement = select(DeliveryAttempt).order_by(DeliveryAttempt.started_at.desc()).limit(limit)
        if delivery_job_id:
            statement = statement.where(DeliveryAttempt.delivery_job_id == delivery_job_id)
        if since:
            statement = statement.where(DeliveryAttempt.started_at >= since)
        return list(self.session.scalars(statement))

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
