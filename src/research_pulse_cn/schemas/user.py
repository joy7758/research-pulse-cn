"""User schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from research_pulse_cn.schemas.common import ORMModel


class UserProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    field: str | None = None
    interests: list[str] = Field(default_factory=list)
    watched_topics: list[str] = Field(default_factory=list)
    watched_venues: list[str] = Field(default_factory=list)
    reminder_preferences: dict[str, Any] = Field(default_factory=dict)
    risk_thresholds: dict[str, Any] = Field(default_factory=dict)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    field: str | None = None
    interests: list[str] | None = None
    watched_topics: list[str] | None = None
    watched_venues: list[str] | None = None
    reminder_preferences: dict[str, Any] | None = None
    risk_thresholds: dict[str, Any] | None = None


class UserProfileRead(ORMModel):
    id: UUID
    name: str
    email: str | None
    field: str | None
    interests: list[str]
    watched_topics: list[str]
    watched_venues: list[str]
    reminder_preferences: dict[str, Any]
    risk_thresholds: dict[str, Any]
    created_at: datetime
    updated_at: datetime
