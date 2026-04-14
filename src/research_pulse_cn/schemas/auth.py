"""Authentication schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from research_pulse_cn.domain.enums import AdminRole
from research_pulse_cn.schemas.common import ORMModel


class AdminSelfRead(ORMModel):
    id: UUID
    email: EmailStr
    role: AdminRole
    display_name: str | None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminRefreshRequest(BaseModel):
    refresh_token: str


class AdminLogoutRequest(BaseModel):
    refresh_token: str


class AuthTokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    admin: AdminSelfRead


class LogoutResponse(BaseModel):
    status: str


class AuthMeResponse(BaseModel):
    actor_type: str
    admin: AdminSelfRead
