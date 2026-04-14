"""Admin account and audit log schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from research_pulse_cn.domain.enums import AdminRole, AuditActorType
from research_pulse_cn.schemas.common import ORMModel


class AdminAccountRead(ORMModel):
    id: UUID
    email: EmailStr
    role: AdminRole
    display_name: str | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminAccountCreate(BaseModel):
    email: EmailStr
    password: str
    role: AdminRole = AdminRole.VIEWER
    display_name: str | None = None
    is_active: bool = True
    must_change_password: bool = True


class AdminAccountUpdate(BaseModel):
    role: AdminRole | None = None
    display_name: str | None = None
    is_active: bool | None = None
    must_change_password: bool | None = None


class AdminPasswordSetRequest(BaseModel):
    password: str
    must_change_password: bool = True


class AuditLogRead(ORMModel):
    id: UUID
    actor_type: AuditActorType
    actor_id: UUID | None
    actor_label: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    request_id: str | None
    route: str | None
    method: str | None
    status_code: int | None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    created_at: datetime
