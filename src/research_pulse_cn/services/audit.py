"""Audit logging service."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from research_pulse_cn.core.request_context import get_request_id
from research_pulse_cn.db.models import AuditLog, utcnow
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AuditActorType
from research_pulse_cn.repositories.audit_log import AuditLogRepository
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)


class AuditService:
    """Persist security-relevant audit events without breaking primary flows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AuditLogRepository(session)

    def safe_record(
        self,
        *,
        actor: ActorContext | None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        request_id: str | None = None,
        route: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            effective_request_id = request_id or get_request_id()
            payload_metadata = dict(metadata or {})
            if effective_request_id and effective_request_id != "-":
                payload_metadata.setdefault("request_id", effective_request_id)
            effective_actor = actor or ActorContext(actor_type=AuditActorType.ANONYMOUS)
            audit_log = AuditLog(
                actor_type=effective_actor.actor_type,
                actor_id=effective_actor.actor_id,
                actor_label=effective_actor.actor_label,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=effective_request_id if effective_request_id != "-" else None,
                route=route,
                method=method,
                status_code=status_code,
                metadata_json=payload_metadata or None,
                created_at=utcnow(),
            )
            self.repository.add(audit_log)
            commit_session(self.session)
        except Exception:
            self.session.rollback()
            logger.warning("audit log write failed", exc_info=True)
