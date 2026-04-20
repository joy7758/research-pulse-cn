"""Schemas for mini-program detail payload previews derived from paper-based pulse data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    MiniProgramDetailActionKind,
    MiniProgramDetailCardType,
    MiniProgramDetailDeliveryState,
    MiniProgramDetailType,
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)


class MiniProgramDetailRequest(BaseModel):
    """Request body for generating a mini-program detail preview."""

    user_id: UUID
    detail_type: MiniProgramDetailType
    pulse_date: date | None = None
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=100)
    paper_id: UUID | None = None
    source_research_pulse_draft_id: str | None = Field(default=None, min_length=8, max_length=64)
    max_items: int = Field(default=5, ge=1, le=20)
    include_low_priority: bool = False
    include_archived: bool = False
    source_format_filter: list[PaperImportSourceFormat] = Field(default_factory=list)
    share_safe: bool = True
    dry_run: bool = True


class MiniProgramDetailItem(BaseModel):
    """One item displayed inside a mini-program detail card."""

    item_id: str = Field(min_length=1, max_length=120)
    paper_id: UUID | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    priority: PaperPriorityLevel | None = None
    reading_status: PaperReadingStatus | None = None
    research_stage: PaperResearchStage | None = None
    next_action: str | None = None
    reason: str
    suggested_action: str
    metadata_warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_format: PaperImportSourceFormat | None = None
    safe_abstract: str | None = None
    detail_path: str = Field(min_length=1, max_length=255)


class MiniProgramDetailCard(BaseModel):
    """One card shown in a mini-program detail preview."""

    card_id: str = Field(min_length=1, max_length=120)
    card_type: MiniProgramDetailCardType
    title: str
    subtitle: str | None = None
    body: str
    items: list[MiniProgramDetailItem] = Field(default_factory=list)
    badges: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    empty_reason: str | None = None


class MiniProgramDetailAction(BaseModel):
    """One navigation or CTA placeholder for a future mini-program client."""

    action_id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=50)
    kind: MiniProgramDetailActionKind
    path: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class MiniProgramShareCard(BaseModel):
    """Compact share-safe card summary for future mini-program share flows."""

    title: str
    summary: str
    path: str = Field(min_length=1, max_length=255)
    image_placeholder: str | None = None
    share_safe: bool
    redacted_fields: list[str] = Field(default_factory=list)


class MiniProgramNavigation(BaseModel):
    """Navigation placeholders for a future mini-program client."""

    current_path: str = Field(min_length=1, max_length=255)
    back_path: str = Field(min_length=1, max_length=255)
    related_paths: list[str] = Field(default_factory=list)


class MiniProgramDetailResult(BaseModel):
    """Generated mini-program detail preview and share-safe payload."""

    detail_id: str = Field(min_length=8, max_length=64)
    detail_type: MiniProgramDetailType
    user_id: UUID
    pulse_date: date | None = None
    timezone: str
    title: str
    subtitle: str
    summary: str
    cards: list[MiniProgramDetailCard] = Field(default_factory=list)
    actions: list[MiniProgramDetailAction] = Field(default_factory=list)
    share_card: MiniProgramShareCard
    navigation: MiniProgramNavigation
    source_research_pulse_draft_id: str | None = None
    total_source_papers: int = Field(ge=0)
    total_items: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime
    delivery_state: MiniProgramDetailDeliveryState
    visibility_notes: list[str] = Field(default_factory=list)
