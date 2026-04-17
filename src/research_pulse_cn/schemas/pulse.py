"""Pulse schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import PulseCardType, PulseJobStatus
from research_pulse_cn.schemas.common import ORMModel
from research_pulse_cn.schemas.delivery import DeliveryJobRead


class ScoreBreakdownRead(BaseModel):
    base_weight: int
    modifiers: dict[str, int] = Field(default_factory=dict)
    total: int


class SuppressionReasonRead(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class PulseFactRead(BaseModel):
    id: str
    card_type: PulseCardType
    source_paper_id: UUID | None = None
    source_timestamp: datetime
    paper_title: str
    summary: str
    why_now: str
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PulseCandidateRead(BaseModel):
    id: str
    fact_id: str
    card_type: PulseCardType
    source_paper_id: UUID | None = None
    source_timestamp: datetime
    paper_title: str
    title_hint: str
    score_total: int
    score_breakdown: ScoreBreakdownRead | None = None
    suppression_reasons: list[SuppressionReasonRead] = Field(default_factory=list)
    candidate_metadata: dict[str, Any] = Field(default_factory=dict)
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    title: str
    summary: str
    why_now: str
    generated_by: dict[str, Any] = Field(default_factory=dict)


class PulseCardPreview(BaseModel):
    card_type: PulseCardType
    source_paper_id: UUID | None = None
    score_total: int
    score_breakdown: ScoreBreakdownRead | None = None
    priority: int
    title: str
    summary: str
    why_now: str
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    generated_by: dict[str, Any] = Field(default_factory=dict)
    candidate_metadata: dict[str, Any] = Field(default_factory=dict)


class PulsePreviewResponse(BaseModel):
    user_id: UUID
    fact_summary: dict[str, Any] = Field(default_factory=dict)
    facts: list[PulseFactRead] = Field(default_factory=list)
    candidates: list[PulseCandidateRead] = Field(default_factory=list)
    selected_cards: list[PulseCardPreview] = Field(default_factory=list)
    suppressed_candidates: list[PulseCandidateRead] = Field(default_factory=list)
    ordering_explanation: dict[str, Any] = Field(default_factory=dict)
    cards: list[PulseCardPreview] = Field(default_factory=list)


class PulseCardRead(ORMModel):
    id: UUID
    pulse_job_id: UUID
    user_id: UUID
    source_paper_id: UUID | None
    card_type: PulseCardType
    priority: int
    score_total: int
    score_breakdown: dict[str, Any]
    title: str
    summary: str
    why_now: str
    action_text: str | None
    deep_link: str | None
    external_reference_key: str | None = None
    evidence_refs: list[str]
    candidate_metadata: dict[str, Any] | None
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
    fact_summary: dict[str, Any] = Field(default_factory=dict)
    suppressed_candidates: list[PulseCandidateRead] = Field(default_factory=list)
    ordering_explanation: dict[str, Any] = Field(default_factory=dict)
    cards: list[PulseCardRead] = Field(default_factory=list)
    delivery_jobs: list[DeliveryJobRead] = Field(default_factory=list)
