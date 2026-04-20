"""Paper progress workbench schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from research_pulse_cn.domain.enums import (
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
TagText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class PaperProgressItemRead(BaseModel):
    """One paper item shaped for the progress workbench."""

    paper_id: UUID
    user_id: UUID
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    source_format: PaperImportSourceFormat | None = None
    reading_status: PaperReadingStatus
    research_stage: PaperResearchStage
    priority: PaperPriorityLevel
    priority_score: int = Field(ge=1, le=5)
    next_action: str | None = None
    user_note: str | None = None
    research_note: str | None = None
    tags: list[str] = Field(default_factory=list)
    imported_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_touch_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list)


class PaperProgressListResponse(BaseModel):
    """Filtered paper progress list with pagination metadata."""

    total_items: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    items: list[PaperProgressItemRead] = Field(default_factory=list)


class PaperProgressUpdateRequest(BaseModel):
    """Patch payload for one paper progress item."""

    reading_status: PaperReadingStatus | None = None
    research_stage: PaperResearchStage | None = None
    priority: PaperPriorityLevel | None = None
    next_action: ShortText | None = None
    clear_next_action: bool = False
    user_note: LongText | None = None
    research_note: LongText | None = None
    tags: list[TagText] | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> PaperProgressUpdateRequest:
        provided_fields = {field for field in self.model_fields_set if field != "clear_next_action"}
        if self.clear_next_action:
            return self
        if not provided_fields:
            raise ValueError("at least one progress field must be provided")
        return self


class PaperProgressSummaryRead(BaseModel):
    """Aggregated progress counts for list filters and dashboard summaries."""

    total_papers: int = Field(ge=0)
    unread_count: int = Field(ge=0)
    reading_count: int = Field(ge=0)
    read_count: int = Field(ge=0)
    high_priority_count: int = Field(ge=0)
    urgent_count: int = Field(ge=0)
    with_next_action_count: int = Field(ge=0)
    by_reading_status: dict[str, int] = Field(default_factory=dict)
    by_research_stage: dict[str, int] = Field(default_factory=dict)
    by_priority: dict[str, int] = Field(default_factory=dict)


class PaperProgressPulseContextRead(BaseModel):
    """Structured paper-progress context reserved for later pulse generation."""

    generated_at: datetime
    high_priority_papers: list[PaperProgressItemRead] = Field(default_factory=list)
    papers_with_next_action: list[PaperProgressItemRead] = Field(default_factory=list)
    active_review_papers: list[PaperProgressItemRead] = Field(default_factory=list)
    metadata_attention_papers: list[PaperProgressItemRead] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
