"""Audit log repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_pulse_cn.db.models import AuditLog
from research_pulse_cn.domain.enums import AuditActorType


class AuditLogRepository:
    """Persistence operations for audit logs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, audit_log: AuditLog) -> AuditLog:
        self.session.add(audit_log)
        self.session.flush()
        self.session.refresh(audit_log)
        return audit_log

    def list(
        self,
        *,
        actor_type: AuditActorType | None = None,
        action: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if actor_type is not None:
            statement = statement.where(AuditLog.actor_type == actor_type)
        if action:
            statement = statement.where(AuditLog.action == action)
        if since:
            statement = statement.where(AuditLog.created_at >= since)
        return list(self.session.scalars(statement))
