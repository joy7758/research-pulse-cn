"""Pulse schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import PulseCardType, PulseJobStatus
from research_pulse_cn.schemas.common import ORMModel
from research_pulse_cn.schemas.delivery import DeliveryJobRead


class PulseCardPreview(BaseModel):
    card_type: PulseCardType
    priority: int
    title: str
    summary: str
    why_now: str
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    generated_by: dict[str, Any] = Field(default_factory=dict)
    paper_id: UUID


class PulsePreviewResponse(BaseModel):
    user_id: UUID
    cards: list[PulseCardPreview] = Field(default_factory=list)


class PulseCardRead(ORMModel):
    id: UUID
    pulse_job_id: UUID
    user_id: UUID
    card_type: PulseCardType
    priority: int
    title: str
    summary: str
    why_now: str
    action_text: str | None
    deep_link: str | None
    evidence_refs: list[str]
    generated_by: dict[str, Any]
    generated_at: datetime


class PulseJobRead(ORMModel):
    id: UUID
    user_id: UUID
    scheduled_for: datetime
    status: PulseJobStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class PulseRunResponse(BaseModel):
    job: PulseJobRead
    cards: list[PulseCardRead] = Field(default_factory=list)
    delivery_jobs: list[DeliveryJobRead] = Field(default_factory=list)
