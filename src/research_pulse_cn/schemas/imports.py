"""Schemas for paper import parsing, preview, and commit foundations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    PaperImportCommitRecordStatus,
    PaperImportSourceFormat,
    PaperType,
)


class PaperImportProblem(BaseModel):
    """One structured warning or error emitted during parsing or preview."""

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
    """Normalized paper metadata used by preview and commit phases."""

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


class PaperImportPreviewCreateRequest(BaseModel):
    """Request body for one import preview run."""

    source_format: PaperImportSourceFormat
    payload: Any


class PaperImportPreviewRecord(BaseModel):
    """One preview row derived from a normalized import record."""

    source_index: int = Field(ge=1)
    normalized_record: PaperImportRecord
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    keywords: list[str] = Field(default_factory=list)
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)
    can_commit: bool = False
    selected: bool = False


class PaperImportPreviewResult(BaseModel):
    """Import preview summary used by API callers and later UI layers."""

    preview_id: str = Field(min_length=8, max_length=64)
    source_format: PaperImportSourceFormat
    created_at: datetime
    total_records: int = 0
    valid_records_count: int = 0
    warning_records_count: int = 0
    error_records_count: int = 0
    records: list[PaperImportPreviewRecord] = Field(default_factory=list)
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)


class PaperImportCommitRequest(BaseModel):
    """Commit request over preview records selected by the caller."""

    user_id: UUID
    source_format: PaperImportSourceFormat
    preview_id: str | None = None
    preview_records: list[PaperImportPreviewRecord] = Field(default_factory=list)
    selected_source_indexes: list[int] = Field(default_factory=list)
    collection_label: str | None = None
    dry_run: bool = False
    default_type: PaperType = PaperType.PUBLISHED
    default_stage: str = Field(default="imported", min_length=1, max_length=255)
    default_priority: int = Field(default=3, ge=1, le=5)


class PaperImportCommitRecordResult(BaseModel):
    """Per-record commit outcome."""

    source_index: int = Field(ge=1)
    status: PaperImportCommitRecordStatus
    reason: str = Field(min_length=1)
    paper_id: UUID | None = None
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)


class PaperImportCommitResult(BaseModel):
    """Batch commit result over one import preview."""

    preview_id: str | None = None
    user_id: UUID
    source_format: PaperImportSourceFormat
    dry_run: bool = False
    committed_at: datetime
    total_selected: int = 0
    committed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    committed_record_ids: list[UUID] = Field(default_factory=list)
    record_results: list[PaperImportCommitRecordResult] = Field(default_factory=list)
    warnings: list[PaperImportProblem] = Field(default_factory=list)
    errors: list[PaperImportProblem] = Field(default_factory=list)
