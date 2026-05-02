"""Worker heartbeat repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_pulse_cn.db.models import WorkerHeartbeat
from research_pulse_cn.domain.enums import WorkerRole, WorkerStatus


class WorkerHeartbeatRepository:
    """Persistence operations for worker heartbeat records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_identity(
        self,
        *,
        worker_name: str,
        hostname_or_instance: str,
    ) -> WorkerHeartbeat | None:
        statement = select(WorkerHeartbeat).where(
            WorkerHeartbeat.worker_name == worker_name,
            WorkerHeartbeat.hostname_or_instance == hostname_or_instance,
        )
        return self.session.scalar(statement)

    def add(self, heartbeat: WorkerHeartbeat) -> WorkerHeartbeat:
        self.session.add(heartbeat)
        self.session.flush()
        self.session.refresh(heartbeat)
        return heartbeat

    def list(
        self,
        *,
        worker_role: WorkerRole | None = None,
        status: WorkerStatus | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[WorkerHeartbeat]:
        statement = (
            select(WorkerHeartbeat).order_by(WorkerHeartbeat.last_heartbeat_at.desc()).limit(limit)
        )
        if worker_role:
            statement = statement.where(WorkerHeartbeat.worker_role == worker_role)
        if status:
            statement = statement.where(WorkerHeartbeat.status == status)
        if since:
            statement = statement.where(WorkerHeartbeat.last_heartbeat_at >= since)
        return list(self.session.scalars(statement))
