"""Subscription policy schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import ChannelType, SubscriptionFrequency
from research_pulse_cn.schemas.common import ORMModel


class SubscriptionPolicyBase(BaseModel):
    user_id: UUID
    channel: ChannelType
    enabled: bool = True
    frequency: SubscriptionFrequency
    quiet_hours: dict[str, Any] | None = None
    frequency_cap: int = Field(default=3, ge=1, le=20)
    endpoint: str | None = None
    policy: dict[str, Any] = Field(default_factory=dict)


class SubscriptionPolicyCreate(SubscriptionPolicyBase):
    pass


class SubscriptionPolicyUpdate(BaseModel):
    channel: ChannelType | None = None
    enabled: bool | None = None
    frequency: SubscriptionFrequency | None = None
    quiet_hours: dict[str, Any] | None = None
    frequency_cap: int | None = Field(default=None, ge=1, le=20)
    endpoint: str | None = None
    policy: dict[str, Any] | None = None


class SubscriptionPolicyRead(ORMModel):
    id: UUID
    user_id: UUID
    channel: ChannelType
    enabled: bool
    frequency: SubscriptionFrequency
    quiet_hours: dict[str, Any] | None
    frequency_cap: int
    endpoint: str | None
    policy: dict[str, Any]
    created_at: datetime
    updated_at: datetime
