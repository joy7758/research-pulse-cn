"""Paper and child-resource schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import PaperType, SignalSource
from research_pulse_cn.schemas.common import ORMModel


class ProgressEventBase(BaseModel):
    stage: str = Field(min_length=1, max_length=255)
    happened_at: datetime
    summary: str = Field(min_length=1)
    evidence_links: list[str] = Field(default_factory=list)
    owner: str | None = None


class ProgressEventCreate(ProgressEventBase):
    pass


class ProgressEventRead(ORMModel):
    id: UUID
    paper_id: UUID
    stage: str
    happened_at: datetime
    summary: str
    evidence_links: list[str]
    owner: str | None


class SignalSnapshotBase(BaseModel):
    source: SignalSource
    citation_count: int | None = None
    download_count: int | None = None
    read_count: int | None = None
    inclusion_status: str | None = None
    fetched_at: datetime


class SignalSnapshotCreate(SignalSnapshotBase):
    pass


class SignalSnapshotRead(ORMModel):
    id: UUID
    paper_id: UUID
    source: SignalSource
    citation_count: int | None
    download_count: int | None
    read_count: int | None
    inclusion_status: str | None
    fetched_at: datetime


class PaperProfileBase(BaseModel):
    user_id: UUID
    title: str = Field(min_length=1, max_length=500)
    title_zh: str | None = None
    title_en: str | None = None
    type: PaperType
    stage: str = Field(min_length=1, max_length=255)
    venue: str | None = None
    identifiers: dict[str, Any] = Field(default_factory=dict)
    source_links: list[str] = Field(default_factory=list)
    last_touch_at: datetime | None = None
    next_action: str | None = None
    blocker: str | None = None
    priority: int = Field(default=3, ge=1, le=5)


class PaperProfileCreate(PaperProfileBase):
    pass


class PaperProfileUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    title_zh: str | None = None
    title_en: str | None = None
    type: PaperType | None = None
    stage: str | None = Field(default=None, min_length=1, max_length=255)
    venue: str | None = None
    identifiers: dict[str, Any] | None = None
    source_links: list[str] | None = None
    last_touch_at: datetime | None = None
    next_action: str | None = None
    blocker: str | None = None
    priority: int | None = Field(default=None, ge=1, le=5)


class PaperProfileRead(ORMModel):
    id: UUID
    user_id: UUID
    title: str
    title_zh: str | None
    title_en: str | None
    type: PaperType
    stage: str
    venue: str | None
    identifiers: dict[str, Any]
    source_links: list[str]
    last_touch_at: datetime | None
    next_action: str | None
    blocker: str | None
    priority: int
    created_at: datetime
    updated_at: datetime
    progress_events: list[ProgressEventRead] = Field(default_factory=list)
    signal_snapshots: list[SignalSnapshotRead] = Field(default_factory=list)
