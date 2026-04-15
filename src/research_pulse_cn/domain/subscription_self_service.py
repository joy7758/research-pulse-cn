"""Typed context objects for subscription self-service grant auth."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from research_pulse_cn.domain.enums import ChannelType, SubscriptionSelfServiceGrantStatus


@dataclass(slots=True)
class SubscriptionSelfServiceGrantContext:
    grant_id: UUID
    user_id: UUID
    binding_id: UUID | None
    channel: ChannelType
    status: SubscriptionSelfServiceGrantStatus
    grant_scope: dict[str, Any] = field(default_factory=dict)
    display_label: str | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None


@dataclass(slots=True)
class IssuedSubscriptionSelfServiceGrant:
    grant_id: UUID
    plain_text_token: str
    expires_at: datetime | None
