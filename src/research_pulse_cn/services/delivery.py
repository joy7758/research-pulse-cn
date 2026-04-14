"""Delivery orchestration service."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.adapters.channels.registry import (
    ChannelAdapterRegistry,
    build_channel_registry,
)
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import DeliveryDispatchError
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import DeliveryJobStatus
from research_pulse_cn.repositories.delivery import DeliveryRepository
from research_pulse_cn.services.common import commit_session


class DeliveryService:
    """Manage outbox delivery state transitions."""

    def __init__(
        self,
        session: Session,
        *,
        adapter_registry: ChannelAdapterRegistry | None = None,
    ) -> None:
        self.session = session
        self.repository = DeliveryRepository(session)
        self.adapter_registry = adapter_registry or build_channel_registry()
        self.settings = get_settings()

    def list_delivery_jobs(
        self,
        *,
        user_id: UUID | None = None,
        status: DeliveryJobStatus | None = None,
    ):
        return self.repository.list(user_id=user_id, status=status)

    def dispatch_due_jobs(self, *, limit: int = 50):
        jobs = self.repository.list_due(as_of=utcnow(), limit=limit)
        for job in jobs:
            adapter = self.adapter_registry.for_channel(job.channel)
            try:
                job.status = DeliveryJobStatus.SENDING
                job.last_error = None
                commit_session(self.session)

                adapter.send({"endpoint": job.endpoint, **job.payload})
                job.status = DeliveryJobStatus.SENT
                job.sent_at = utcnow()
                job.next_retry_at = None
                commit_session(self.session)
            except DeliveryDispatchError as exc:
                self.session.rollback()
                self._mark_failed(job, exc)
        return self.repository.list(status=DeliveryJobStatus.SENT)

    def _mark_failed(self, job, error: DeliveryDispatchError) -> None:
        job = self.repository.get(job.id)
        if job is None:
            return
        job.retry_count += 1
        job.last_error = str(error)

        if not error.retryable or job.retry_count >= self.settings.max_delivery_retries:
            job.status = DeliveryJobStatus.DEAD_LETTER
            job.next_retry_at = None
        else:
            job.status = DeliveryJobStatus.FAILED
            job.next_retry_at = utcnow() + timedelta(
                seconds=self.settings.delivery_retry_delay_seconds
            )
        commit_session(self.session)
