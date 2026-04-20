"""Schemas for research pulse drafts generated from imported papers."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)


class ResearchPulseRequest(BaseModel):
    """Request body for generating a deterministic research pulse draft."""

    user_id: UUID
    pulse_date: date | None = None
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=100)
    max_items_per_section: int = Field(default=3, ge=1, le=20)
    include_low_priority: bool = False
    include_archived: bool = False
    source_format_filter: list[PaperImportSourceFormat] = Field(default_factory=list)
    dry_run: bool = True


class ResearchPulseItem(BaseModel):
    """One paper item selected into one pulse section."""

    paper_id: UUID
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    priority: PaperPriorityLevel
    reading_status: PaperReadingStatus
    research_stage: PaperResearchStage
    next_action: str | None = None
    reason: str
    suggested_action: str
    metadata_warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_format: PaperImportSourceFormat | None = None


class ResearchPulseSection(BaseModel):
    """One structured section in the paper-based research pulse draft."""

    section_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    items: list[ResearchPulseItem] = Field(default_factory=list)
    empty_reason: str | None = None


class ResearchPulseResult(BaseModel):
    """Generated research pulse draft for imported papers and progress context."""

    draft_id: str = Field(min_length=8, max_length=64)
    user_id: UUID
    pulse_date: date
    timezone: str
    dry_run: bool = True
    title: str
    summary: str
    sections: list[ResearchPulseSection] = Field(default_factory=list)
    total_source_papers: int = Field(ge=0)
    total_items: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime
    source_context_notes: list[str] = Field(default_factory=list)
