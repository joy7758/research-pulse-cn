"""Schemas for pulse input layer APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    ExternalRetrievalMode,
    ExternalRetrievalPlanStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
    ResearchWatchProfileSourceMode,
    WorkActivitySource,
    WorkActivityType,
)
from research_pulse_cn.schemas.common import ORMModel


class WorkActivityEventRead(ORMModel):
    id: UUID
    user_id: UUID
    paper_id: UUID | None
    activity_type: WorkActivityType
    summary: str
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )
    happened_at: datetime
    source: WorkActivitySource
    created_at: datetime


class WorkActivityTouchedPaperRead(BaseModel):
    paper_id: UUID
    title: str
    activity_count: int


class WorkActivitySummaryRead(BaseModel):
    window_started_at: datetime
    window_ended_at: datetime
    total_events: int
    activity_type_counts: dict[str, int] = Field(default_factory=dict)
    touched_papers: list[WorkActivityTouchedPaperRead] = Field(default_factory=list)


class ResearchWatchProfileCreate(BaseModel):
    user_id: UUID
    paper_id: UUID | None = None
    label: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    authors_of_interest: list[str] | None = None


class ResearchWatchProfileUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    topics: list[str] | None = None
    keywords: list[str] | None = None
    venues: list[str] | None = None
    authors_of_interest: list[str] | None = None


class ResearchWatchProfileRead(ORMModel):
    id: UUID
    user_id: UUID
    paper_id: UUID | None
    label: str
    enabled: bool
    source_mode: ResearchWatchProfileSourceMode
    topics: list[str]
    keywords: list[str]
    venues: list[str]
    authors_of_interest: list[str] | None
    created_at: datetime
    updated_at: datetime


class EffectiveWatchSeedsRead(BaseModel):
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    authors_of_interest: list[str] = Field(default_factory=list)


class EffectiveRetrievalSeedsRead(BaseModel):
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)
    authors_of_interest: list[str] = Field(default_factory=list)
    touched_paper_titles: list[str] = Field(default_factory=list)


class ExternalRetrievalPlanPreviewRead(BaseModel):
    source_kind: ExternalRetrievalSourceKind
    retrieval_scope: ExternalRetrievalScope
    watch_profile_id: UUID | None = None
    paper_id: UUID | None = None
    plan_label: str
    query_text: str
    query_payload: dict[str, Any] = Field(default_factory=dict)
    effective_inputs: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    plan_hash: str


class ExternalRetrievalPlanCompactRead(BaseModel):
    source_kind: ExternalRetrievalSourceKind
    retrieval_scope: ExternalRetrievalScope
    plan_label: str
    query_text: str
    reason_codes: list[str] = Field(default_factory=list)


class ExternalRetrievalPlanRead(ORMModel):
    id: UUID
    user_id: UUID
    source_kind: ExternalRetrievalSourceKind
    retrieval_scope: ExternalRetrievalScope
    watch_profile_id: UUID | None
    paper_id: UUID | None
    plan_label: str
    query_text: str
    query_payload: dict[str, Any] = Field(default_factory=dict)
    effective_inputs: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    plan_hash: str
    status: ExternalRetrievalPlanStatus
    created_at: datetime
    updated_at: datetime


class ExternalRetrievalPlanningCompactRead(BaseModel):
    mode: ExternalRetrievalMode
    enabled_sources: list[ExternalRetrievalSourceKind] = Field(default_factory=list)
    preview_plan_count: int
    source_plan_previews: list[ExternalRetrievalPlanCompactRead] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExternalRetrievalInputPreviewResponse(BaseModel):
    user_id: UUID
    mode: ExternalRetrievalMode
    enabled_sources: list[ExternalRetrievalSourceKind] = Field(default_factory=list)
    enabled_watch_profiles: list[ResearchWatchProfileRead] = Field(default_factory=list)
    effective_retrieval_seeds: EffectiveRetrievalSeedsRead
    recent_activity_context_summary: WorkActivitySummaryRead
    source_plan_previews: list[ExternalRetrievalPlanPreviewRead] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ExternalRetrievalPlanBuildResponse(BaseModel):
    user_id: UUID
    mode: ExternalRetrievalMode
    built_plans: list[ExternalRetrievalPlanRead] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PulseInputPreviewResponse(BaseModel):
    user_id: UUID
    preview_date: date
    window_started_at: datetime
    window_ended_at: datetime
    work_activity_summary: WorkActivitySummaryRead
    work_activity_events: list[WorkActivityEventRead] = Field(default_factory=list)
    enabled_watch_profiles: list[ResearchWatchProfileRead] = Field(default_factory=list)
    effective_watch_seeds: EffectiveWatchSeedsRead
    retrieval_input_preview: ExternalRetrievalPlanningCompactRead | None = None
    notes: list[str] = Field(default_factory=list)
