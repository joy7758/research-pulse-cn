"""Typed auth and actor boundary objects."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from research_pulse_cn.domain.enums import AdminRole, AuditActorType


@dataclass(slots=True)
class ActorContext:
    """Authenticated or anonymous caller identity used for RBAC and audit."""

    actor_type: AuditActorType
    actor_id: UUID | None = None
    actor_label: str | None = None
    admin_role: AdminRole | None = None
    is_active: bool = False

    @property
    def is_admin(self) -> bool:
        return self.actor_type == AuditActorType.ADMIN

    @property
    def is_service(self) -> bool:
        return self.actor_type == AuditActorType.SERVICE

    @property
    def is_anonymous(self) -> bool:
        return self.actor_type == AuditActorType.ANONYMOUS
