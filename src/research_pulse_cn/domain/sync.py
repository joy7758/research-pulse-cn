"""Typed sync-domain helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from research_pulse_cn.domain.enums import ClientType


@dataclass(slots=True)
class DeviceContext:
    """Authenticated sync device context."""

    client_device_id: UUID
    user_id: UUID
    client_type: ClientType
    display_name: str
    token_id: UUID
    is_active: bool


@dataclass(slots=True)
class IssuedClientDeviceToken:
    """One-time plaintext device credential response."""

    client_device_id: UUID
    plain_text_token: str
    expires_at: datetime | None
