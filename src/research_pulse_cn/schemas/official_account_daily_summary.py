"""Schemas for official-account daily summary drafts built from imported-paper pulse data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    OfficialAccountProviderMode,
    OfficialAccountTransportKind,
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
    WeChatBindingChannelType,
    WeChatBindingState,
)


class OfficialAccountDailySummaryRequest(BaseModel):
    """Request body for generating an official-account daily summary draft."""

    user_id: UUID
    pulse_date: date | None = None
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=100)
    max_items_per_section: int = Field(default=3, ge=1, le=20)
    max_highlights: int = Field(default=3, ge=1, le=5)
    include_low_priority: bool = False
    include_archived: bool = False
    source_format_filter: list[PaperImportSourceFormat] = Field(default_factory=list)
    binding_id: UUID | None = None
    dry_run: bool = True


class OfficialAccountDailySummaryItem(BaseModel):
    """One compact paper item shaped for official-account summary preview."""

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
    summary_line: str
    metadata_warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_format: PaperImportSourceFormat | None = None


class OfficialAccountDailySummarySection(BaseModel):
    """One section in the official-account daily summary draft."""

    section_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    items: list[OfficialAccountDailySummaryItem] = Field(default_factory=list)
    empty_reason: str | None = None


class OfficialAccountDailySummaryHighlight(BaseModel):
    """One highlight entry prepared for publication preview rendering."""

    sort_order: int = Field(ge=1)
    section_id: str = Field(min_length=1, max_length=100)
    section_title: str = Field(min_length=1, max_length=100)
    paper_id: UUID
    title: str
    summary: str
    why_now: str
    suggested_action: str


class OfficialAccountPublicationPreview(BaseModel):
    """Publication-preview payload aligned with the existing digest preview contract."""

    digest_title: str
    digest_subtitle: str
    digest_highlights: list[OfficialAccountDailySummaryHighlight] = Field(default_factory=list)
    primary_cta_text: str
    primary_cta_path: str | None = None
    mini_program_path: str | None = None
    article_url: str | None = None


class OfficialAccountTemplatePayloadPreview(BaseModel):
    """Safe preview of a template-notice payload without exposing live recipient ids."""

    template_id_configured: bool
    field_mapping: dict[str, str] = Field(default_factory=dict)
    logical_fields: dict[str, str] = Field(default_factory=dict)
    payload_preview: dict[str, Any] = Field(default_factory=dict)


class OfficialAccountBindingTargetPreview(BaseModel):
    """Safe binding target preview for one active official-account recipient."""

    binding_id: UUID
    channel_type: WeChatBindingChannelType
    bind_state: WeChatBindingState
    display_label: str | None = None
    subscribed: bool
    digest_enabled: bool
    masked_openid: str


class OfficialAccountBindingPreview(BaseModel):
    """Active binding availability summary for official-account payload previews."""

    active_binding_count: int = Field(ge=0)
    selected_binding: OfficialAccountBindingTargetPreview | None = None
    notes: list[str] = Field(default_factory=list)


class OfficialAccountProviderPreview(BaseModel):
    """Safe provider-configuration preview for official-account daily summary generation."""

    provider_mode: OfficialAccountProviderMode
    transport_kind: OfficialAccountTransportKind
    template_id_configured: bool
    template_field_mapping_configured: bool
    article_base_url_configured: bool
    mini_program_app_id_configured: bool
    callback_enabled: bool
    real_send_enabled: bool
    notes: list[str] = Field(default_factory=list)


class OfficialAccountDailySummaryResult(BaseModel):
    """Generated official-account daily summary draft."""

    draft_id: str = Field(min_length=8, max_length=64)
    source_research_pulse_draft_id: str = Field(min_length=8, max_length=64)
    user_id: UUID
    pulse_date: date
    timezone: str
    dry_run: bool = True
    title: str
    headline: str
    summary: str
    sections: list[OfficialAccountDailySummarySection] = Field(default_factory=list)
    highlight_count: int = Field(ge=0)
    publication_preview: OfficialAccountPublicationPreview
    template_payload_preview: OfficialAccountTemplatePayloadPreview
    binding_preview: OfficialAccountBindingPreview
    provider_preview: OfficialAccountProviderPreview
    total_source_papers: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime
    source_context_notes: list[str] = Field(default_factory=list)
