"""Operational inspection and control services."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db.models import utcnow
from research_pulse_cn.domain.enums import (
    DeliveryJobStatus,
    PulseJobScheduledReason,
    PulseJobStatus,
)
from research_pulse_cn.repositories.delivery import DeliveryRepository
from research_pulse_cn.repositories.heartbeat import WorkerHeartbeatRepository
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.services.delivery import DeliveryService
from research_pulse_cn.services.pulse import PulseService
from research_pulse_cn.services.scheduler import SchedulerService


class OpsService:
    """Expose readiness, listing, replay, and requeue capabilities."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.metrics = get_metrics()
        self.pulse_repository = PulseRepository(session)
        self.delivery_repository = DeliveryRepository(session)
        self.heartbeat_repository = WorkerHeartbeatRepository(session)
        self.scheduler_service = SchedulerService(session)
        self.pulse_service = PulseService(session)
        self.delivery_service = DeliveryService(session)

    def readiness(self) -> tuple[dict[str, object], bool]:
        components: dict[str, dict[str, str | None]] = {}
        healthy = True

        try:
            self.session.execute(text("SELECT 1"))
            components["database"] = {"status": "ok", "detail": "database responded to SELECT 1"}
        except Exception as exc:
            healthy = False
            components["database"] = {"status": "error", "detail": str(exc)}

        components["scheduler"] = {
            "status": "ok",
            "detail": "daily policies auto-schedule in v1; event policies remain manual",
        }
        components["delivery"] = {
            "status": "ok",
            "detail": "outbox delivery, retry, and dead-letter pipeline enabled",
        }
        return {"status": "ok" if healthy else "degraded", "components": components}, healthy

    def metrics_text(self) -> str:
        return self.metrics.render_prometheus()

    def list_heartbeats(
        self,
        *,
        worker_role=None,
        status=None,
        since_hours: int | None = None,
        limit: int = 100,
    ):
        since = None if since_hours is None else utcnow() - timedelta(hours=since_hours)
        return self.heartbeat_repository.list(
            worker_role=worker_role,
            status=status,
            since=since,
            limit=limit,
        )

    def list_pulse_jobs(
        self,
        *,
        user_id: UUID | None = None,
        status: PulseJobStatus | None = None,
        scheduled_reason: PulseJobScheduledReason | None = None,
        since_hours: int | None = None,
        limit: int = 100,
    ):
        since = None if since_hours is None else utcnow() - timedelta(hours=since_hours)
        return self.pulse_repository.list_jobs(
            user_id=user_id,
            status=status,
            scheduled_reason=scheduled_reason,
            since=since,
            limit=limit,
        )

    def list_delivery_jobs(
        self,
        *,
        user_id: UUID | None = None,
        status: DeliveryJobStatus | None = None,
        since_hours: int | None = None,
        limit: int = 100,
    ):
        since = None if since_hours is None else utcnow() - timedelta(hours=since_hours)
        return self.delivery_repository.list(
            user_id=user_id,
            status=status,
            since=since,
            limit=limit,
        )

    def list_delivery_attempts(
        self,
        *,
        delivery_job_id: UUID | None = None,
        since_hours: int | None = None,
        limit: int = 100,
    ):
        since = None if since_hours is None else utcnow() - timedelta(hours=since_hours)
        return self.delivery_repository.list_attempts(
            delivery_job_id=delivery_job_id,
            since=since,
            limit=limit,
        )

    def scheduler_tick(self) -> dict[str, object]:
        return self.scheduler_service.tick()

    def requeue_delivery_job(self, delivery_job_id: UUID):
        return self.delivery_service.requeue(delivery_job_id)

    def replay_pulse_job(self, pulse_job_id: UUID):
        source_job = self.pulse_repository.get_job(pulse_job_id)
        if source_job is None:
            raise NotFoundError(f"pulse job {pulse_job_id} was not found")

        if source_job.status in {PulseJobStatus.PENDING, PulseJobStatus.RUNNING}:
            return "source_job_already_active", source_job

        active_replay = self.pulse_repository.find_active_replay(pulse_job_id)
        if active_replay is not None:
            return "existing_active_replay", active_replay

        replay_job = self.pulse_service.enqueue_run(
            source_job.user_id,
            scheduled_for=utcnow(),
            subscription_policy_id=source_job.subscription_policy_id,
            scheduled_reason=PulseJobScheduledReason.REPLAY,
            source_pulse_job_id=source_job.id,
        )
        return "replay_created", replay_job
