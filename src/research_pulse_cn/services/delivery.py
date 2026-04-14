"""Delivery orchestration service."""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.adapters.channels.registry import (
    ChannelAdapterRegistry,
    build_channel_registry,
)
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import DeliveryDispatchError, NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import DeliveryAttempt, utcnow
from research_pulse_cn.domain.enums import DeliveryAttemptStatus, DeliveryJobStatus
from research_pulse_cn.repositories.delivery import DeliveryRepository
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)


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
        self.metrics = get_metrics()

    def list_delivery_jobs(
        self,
        *,
        user_id: UUID | None = None,
        status: DeliveryJobStatus | None = None,
        since=None,
    ):
        return self.repository.list(user_id=user_id, status=status, since=since)

    def list_attempts(
        self,
        *,
        delivery_job_id: UUID | None = None,
        since=None,
        limit: int = 100,
    ):
        return self.repository.list_attempts(
            delivery_job_id=delivery_job_id,
            since=since,
            limit=limit,
        )

    def dispatch_due_jobs(self, *, limit: int = 50):
        jobs = self.repository.list_due(as_of=utcnow(), limit=limit)
        processed = []
        for job in jobs:
            with bind_log_context(delivery_job_id=job.id, user_id=job.user_id):
                attempt = self._start_attempt(job)
                try:
                    adapter = self.adapter_registry.for_channel(job.channel)
                    adapter.send({"endpoint": job.endpoint, **job.payload})
                    self._mark_sent(job.id, attempt.id, adapter_name=type(adapter).__name__)
                except DeliveryDispatchError as exc:
                    self.session.rollback()
                    self._mark_failed(
                        job.id,
                        attempt.id,
                        adapter_name=type(adapter).__name__,
                        error=exc,
                    )
            refreshed = self.repository.get(job.id)
            if refreshed is not None:
                processed.append(refreshed)
        return processed

    def requeue(self, delivery_job_id: UUID):
        job = self.repository.get(delivery_job_id)
        if job is None:
            raise NotFoundError(f"delivery job {delivery_job_id} was not found")

        action = "already_active"
        if job.status in {DeliveryJobStatus.FAILED, DeliveryJobStatus.DEAD_LETTER}:
            job.status = DeliveryJobStatus.PENDING
            job.next_retry_at = None
            job.last_error = None
            action = "requeued"
            commit_session(self.session)
        elif job.status == DeliveryJobStatus.SENT:
            action = "already_sent"

        return action, self.repository.get(delivery_job_id) or job

    def _start_attempt(self, job):
        attempt = DeliveryAttempt(
            delivery_job_id=job.id,
            attempt_number=job.retry_count + 1,
            channel=job.channel,
            adapter_name=self.adapter_registry.adapter_name(job.channel),
            status=DeliveryAttemptStatus.STARTED,
            started_at=utcnow(),
        )
        job.status = DeliveryJobStatus.SENDING
        job.last_error = None
        self.repository.add_attempt(attempt)
        commit_session(self.session)
        logger.info("delivery attempt started")
        return attempt

    def _mark_sent(self, delivery_job_id: UUID, attempt_id: UUID, *, adapter_name: str) -> None:
        job = self.repository.get(delivery_job_id)
        if job is None:
            return
        attempt = next(
            (item for item in job.attempts if item.id == attempt_id),
            None,
        )
        if attempt is not None:
            attempt.adapter_name = adapter_name
            attempt.status = DeliveryAttemptStatus.SENT
            attempt.response_summary = "adapter dispatched successfully"
            attempt.finished_at = utcnow()
        job.status = DeliveryJobStatus.SENT
        job.sent_at = utcnow()
        job.next_retry_at = None
        commit_session(self.session)
        self.metrics.increment("delivery_jobs_sent_total")
        logger.info("delivery job sent")

    def _mark_failed(
        self,
        delivery_job_id: UUID,
        attempt_id: UUID,
        *,
        adapter_name: str,
        error: DeliveryDispatchError,
    ) -> None:
        job = self.repository.get(delivery_job_id)
        if job is None:
            return
        attempt = next(
            (item for item in job.attempts if item.id == attempt_id),
            None,
        )
        if attempt is not None:
            attempt.adapter_name = adapter_name
            attempt.status = DeliveryAttemptStatus.FAILED
            attempt.error_summary = str(error)
            attempt.finished_at = utcnow()

        job.retry_count += 1
        job.last_error = str(error)
        if not error.retryable or job.retry_count >= self.settings.max_delivery_retries:
            job.status = DeliveryJobStatus.DEAD_LETTER
            job.next_retry_at = None
            self.metrics.increment("delivery_jobs_dead_letter_total")
        else:
            job.status = DeliveryJobStatus.FAILED
            job.next_retry_at = utcnow() + timedelta(
                seconds=self.settings.delivery_retry_delay_seconds
            )
            self.metrics.increment("delivery_jobs_failed_total")
        commit_session(self.session)
        logger.warning("delivery job failed", extra={"adapter_name": adapter_name})
