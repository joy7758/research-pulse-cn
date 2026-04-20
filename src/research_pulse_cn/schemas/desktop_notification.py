"""Schemas for desktop notification drafts derived from paper-based research pulse data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    DesktopNotificationActionKind,
    DesktopNotificationDeliveryState,
    DesktopNotificationType,
    DesktopNotificationUrgency,
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)


class DesktopNotificationRequest(BaseModel):
    """Request body for generating a local desktop notification draft."""

    user_id: UUID
    pulse_date: date | None = None
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=100)
    max_items: int = Field(default=3, ge=1, le=10)
    include_low_priority: bool = False
    include_archived: bool = False
    source_format_filter: list[PaperImportSourceFormat] = Field(default_factory=list)
    title_prefix: str = Field(default="今日科研 Pulse", min_length=1, max_length=50)
    include_actions: bool = True
    dry_run: bool = True


class DesktopNotificationItem(BaseModel):
    """One compact item suitable for a local desktop notification preview."""

    paper_id: UUID
    title: str
    line: str
    reason: str
    suggested_action: str
    priority: PaperPriorityLevel
    reading_status: PaperReadingStatus
    research_stage: PaperResearchStage
    metadata_warnings: list[str] = Field(default_factory=list)
    url: str | None = None
    doi: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_format: PaperImportSourceFormat | None = None


class DesktopNotificationAction(BaseModel):
    """One local action placeholder that a future desktop client may consume."""

    action_id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=50)
    kind: DesktopNotificationActionKind
    deep_link: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)


class DesktopNotificationResult(BaseModel):
    """Generated desktop notification draft and payload preview."""

    draft_id: str = Field(min_length=8, max_length=64)
    source_research_pulse_draft_id: str = Field(min_length=8, max_length=64)
    user_id: UUID
    pulse_date: date
    timezone: str
    title: str
    body: str
    notification_type: DesktopNotificationType
    urgency: DesktopNotificationUrgency
    badge_count: int = Field(ge=0, le=99)
    items: list[DesktopNotificationItem] = Field(default_factory=list)
    actions: list[DesktopNotificationAction] = Field(default_factory=list)
    deep_link: str = Field(min_length=1, max_length=255)
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    total_source_papers: int = Field(ge=0)
    total_items: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime
    delivery_state: DesktopNotificationDeliveryState
    delivery_notes: list[str] = Field(default_factory=list)
