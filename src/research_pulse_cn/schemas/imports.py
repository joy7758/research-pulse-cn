"""Schemas for normalized paper import foundations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import PaperImportSourceFormat


class PaperImportProblem(BaseModel):
    """One structured warning or error emitted during parsing."""

    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1)
    field: str | None = None


class PaperImportAttachmentPlaceholder(BaseModel):
    """Attachment metadata reserved for later import commit phases."""

    label: str = Field(min_length=1)
    path_hint: str | None = None
    media_type: str | None = None
    source_kind: str = "placeholder"


class PaperImportNotePlaceholder(BaseModel):
    """Note metadata reserved for later import commit phases."""

    label: str = Field(min_length=1)
    content_hint: str | None = None


class PaperImportRecord(BaseModel):
    """Normalized paper metadata used by later import preview/commit phases."""

    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    language: str | None = None
    source_format: PaperImportSourceFormat
    source_identifier: str | None = None
    raw_source_payload: dict[str, Any] = Field(default_factory=dict)
    attachments: list[PaperImportAttachmentPlaceholder] = Field(default_factory=list)
    notes: list[PaperImportNotePlaceholder] = Field(default_factory=list)
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)


class PaperImportParseResult(BaseModel):
    """Parse outcome for one payload in one source format."""

    source_format: PaperImportSourceFormat
    parsed_at: datetime
    records: list[PaperImportRecord] = Field(default_factory=list)
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)
