"""Worker heartbeat persistence helpers."""

from __future__ import annotations

import os
import socket
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from research_pulse_cn.db.models import WorkerHeartbeat
from research_pulse_cn.repositories.heartbeat import WorkerHeartbeatRepository
from research_pulse_cn.services.common import commit_session


class WorkerHeartbeatService:
    """Upsert worker heartbeat rows for operational inspection."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = WorkerHeartbeatRepository(session)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def beat(
        self,
        *,
        worker_name: str,
        worker_role,
        status,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> WorkerHeartbeat:
        heartbeat = self.repository.get_by_identity(
            worker_name=worker_name,
            hostname_or_instance=self.hostname,
        )
        if heartbeat is None:
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                worker_role=worker_role,
                status=status,
                hostname_or_instance=self.hostname,
                pid=self.pid,
                started_at=now,
                last_heartbeat_at=now,
                metadata_json=dict(metadata or {}),
            )
            self.repository.add(heartbeat)
        else:
            heartbeat.worker_role = worker_role
            heartbeat.status = status
            heartbeat.pid = self.pid
            heartbeat.last_heartbeat_at = now
            heartbeat.metadata_json = dict(metadata or {})
        commit_session(self.session)
        return heartbeat
