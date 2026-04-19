"""Official-account daily summary drafts generated from paper-based research pulse data."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.db.models import WeChatIdentityBinding
from research_pulse_cn.domain.enums import (
    OfficialAccountProviderMode,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.schemas.official_account_daily_summary import (
    OfficialAccountBindingPreview,
    OfficialAccountBindingTargetPreview,
    OfficialAccountDailySummaryHighlight,
    OfficialAccountDailySummaryItem,
    OfficialAccountDailySummaryRequest,
    OfficialAccountDailySummaryResult,
    OfficialAccountDailySummarySection,
    OfficialAccountProviderPreview,
    OfficialAccountPublicationPreview,
    OfficialAccountTemplatePayloadPreview,
)
from research_pulse_cn.schemas.research_pulse import (
    ResearchPulseItem,
    ResearchPulseRequest,
    ResearchPulseResult,
    ResearchPulseSection,
)
from research_pulse_cn.services.research_pulse import ResearchPulseService

_DEFAULT_TEMPLATE_FIELD_MAPPING = {
    "issue_title": "first",
    "issue_date": "keyword1",
    "highlight_count": "keyword2",
    "summary": "keyword3",
    "remark": "remark",
}
_LANDING_PATH = "/mini/today"


class OfficialAccountDailySummaryService:
    """Build official-account daily summary drafts without creating send jobs."""

    def __init__(
        self,
        session: Session,
        *,
        research_pulse_service: ResearchPulseService | None = None,
        digest_repository: DigestRepository | None = None,
        now_provider=None,
    ) -> None:
        self.settings = get_settings()
        self.research_pulse_service = research_pulse_service or ResearchPulseService(session)
        self.digest_repository = digest_repository or DigestRepository(session)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def build_daily_summary(
        self,
        request: OfficialAccountDailySummaryRequest,
    ) -> OfficialAccountDailySummaryResult:
        pulse_result = self.research_pulse_service.generate_daily_pulse(
            ResearchPulseRequest(
                user_id=request.user_id,
                pulse_date=request.pulse_date,
                timezone=request.timezone,
                max_items_per_section=request.max_items_per_section,
                include_low_priority=request.include_low_priority,
                include_archived=request.include_archived,
                source_format_filter=request.source_format_filter,
                dry_run=True,
            )
        )

        active_bindings = self.digest_repository.list_active_official_account_bindings(
            user_id=request.user_id
        )
        selected_binding = self._select_binding(
            active_bindings=active_bindings,
            binding_id=request.binding_id,
        )

        sections = _build_summary_sections(pulse_result.sections)
        highlights = _build_highlights(sections=sections, max_highlights=request.max_highlights)
        headline = _build_headline(sections=sections)
        summary = _build_public_summary(
            pulse_result=pulse_result,
            sections=sections,
            highlight_count=len(highlights),
        )
        publication_preview = _build_publication_preview(
            digest_title=headline,
            digest_subtitle=summary,
            highlights=highlights,
            settings=self.settings,
        )
        template_payload_preview = _build_template_payload_preview(
            publication_preview=publication_preview,
            pulse_date=pulse_result.pulse_date.isoformat(),
            selected_binding=selected_binding,
            settings=self.settings,
        )
        binding_preview = _build_binding_preview(
            active_bindings=active_bindings,
            selected_binding=selected_binding,
        )
        provider_preview = _build_provider_preview(self.settings)

        warnings = list(pulse_result.warnings)
        if not request.dry_run:
            warnings.append("Pivot-6 当前只生成公众号每日摘要草稿，不创建发布任务或发送记录。")
        if not active_bindings:
            warnings.append("当前用户没有可用的公众号绑定，本轮仅生成摘要草稿与 payload 预览。")
        if not self.settings.wechat_official_digest_template_id:
            warnings.append("未配置公众号模板 ID，当前仅返回模板字段与 payload 结构预览。")
        if publication_preview.article_url is None:
            warnings.append("未配置公众号文章基础 URL，当前仅提供小程序落地路径预览。")
        if (
            publication_preview.mini_program_path
            and not self.settings.official_account_default_mini_program_app_id
        ):
            warnings.append("未配置默认小程序 AppID，当前 payload 预览不包含小程序落地信息。")

        generated_at = self.now_provider()
        return OfficialAccountDailySummaryResult(
            draft_id=_build_daily_summary_draft_id(
                source_draft_id=pulse_result.draft_id,
                selected_binding=selected_binding,
                max_highlights=request.max_highlights,
            ),
            source_research_pulse_draft_id=pulse_result.draft_id,
            user_id=request.user_id,
            pulse_date=pulse_result.pulse_date,
            timezone=pulse_result.timezone,
            dry_run=True,
            title=f"{pulse_result.pulse_date.isoformat()} 公众号每日摘要草稿",
            headline=headline,
            summary=summary,
            sections=sections,
            highlight_count=len(highlights),
            publication_preview=publication_preview,
            template_payload_preview=template_payload_preview,
            binding_preview=binding_preview,
            provider_preview=provider_preview,
            total_source_papers=pulse_result.total_source_papers,
            warnings=_dedupe_preserving_order(warnings),
            generated_at=generated_at,
            source_context_notes=_dedupe_preserving_order(
                [
                    *pulse_result.source_context_notes,
                    "本阶段只整理适合公众号模板的每日摘要草稿，不进入真实投递。",
                    (
                        "publication_preview 字段与既有 digest 预览结构保持兼容，"
                        "便于后续接到发送链路。"
                    ),
                ]
            ),
        )

    def _select_binding(
        self,
        *,
        active_bindings: list[WeChatIdentityBinding],
        binding_id: UUID | None,
    ) -> WeChatIdentityBinding | None:
        if binding_id is None:
            return active_bindings[0] if active_bindings else None
        for binding in active_bindings:
            if binding.id == binding_id:
                return binding
        raise NotFoundError(f"active official-account binding {binding_id} was not found")


def _build_summary_sections(
    pulse_sections: list[ResearchPulseSection],
) -> list[OfficialAccountDailySummarySection]:
    sections: list[OfficialAccountDailySummarySection] = []
    for section in pulse_sections:
        items = [
            OfficialAccountDailySummaryItem(
                paper_id=item.paper_id,
                title=item.title,
                authors=list(item.authors),
                year=item.year,
                venue=item.venue,
                doi=item.doi,
                url=item.url,
                priority=item.priority,
                reading_status=item.reading_status,
                research_stage=item.research_stage,
                next_action=item.next_action,
                reason=item.reason,
                suggested_action=item.suggested_action,
                summary_line=_build_item_summary_line(item),
                metadata_warnings=list(item.metadata_warnings),
                tags=list(item.tags),
                source_format=item.source_format,
            )
            for item in section.items
        ]
        sections.append(
            OfficialAccountDailySummarySection(
                section_id=section.section_id,
                title=section.title,
                description=section.description,
                items=items,
                empty_reason=section.empty_reason,
            )
        )
    return sections


def _build_highlights(
    *,
    sections: list[OfficialAccountDailySummarySection],
    max_highlights: int,
) -> list[OfficialAccountDailySummaryHighlight]:
    highlights: list[OfficialAccountDailySummaryHighlight] = []
    seen_paper_ids: set[UUID] = set()
    for section in sections:
        for item in section.items:
            if item.paper_id in seen_paper_ids:
                continue
            seen_paper_ids.add(item.paper_id)
            highlights.append(
                OfficialAccountDailySummaryHighlight(
                    sort_order=len(highlights) + 1,
                    section_id=section.section_id,
                    section_title=section.title,
                    paper_id=item.paper_id,
                    title=item.title,
                    summary=item.summary_line,
                    why_now=item.reason,
                    suggested_action=item.suggested_action,
                )
            )
            if len(highlights) >= max_highlights:
                return highlights
    return highlights


def _build_headline(sections: list[OfficialAccountDailySummarySection]) -> str:
    focus_count = _section_item_count(sections, "today_focus")
    action_count = _section_item_count(sections, "next_actions")
    triage_count = _section_item_count(sections, "newly_imported_triage")
    metadata_count = _section_item_count(sections, "metadata_attention")
    if focus_count and action_count:
        return f"今日优先推进 {focus_count} 篇重点论文，明确执行 {action_count} 项下一步动作"
    if focus_count:
        return f"今日建议优先处理 {focus_count} 篇重点论文"
    if action_count:
        return f"今日已有 {action_count} 项明确下一步动作待推进"
    if triage_count:
        return f"今日建议先筛选 {triage_count} 篇新导入论文"
    if metadata_count:
        return f"今日建议先补全 {metadata_count} 条论文元数据"
    return "今日暂无需要推送的重点论文，可先整理导入与阅读计划"


def _build_public_summary(
    *,
    pulse_result: ResearchPulseResult,
    sections: list[OfficialAccountDailySummarySection],
    highlight_count: int,
) -> str:
    focus_count = _section_item_count(sections, "today_focus")
    reading_count = _section_item_count(sections, "continue_reading")
    action_count = _section_item_count(sections, "next_actions")
    metadata_count = _section_item_count(sections, "metadata_attention")
    triage_count = _section_item_count(sections, "newly_imported_triage")
    if pulse_result.total_source_papers == 0:
        return "今日还没有可整理成公众号摘要的论文进度内容，建议先导入论文并标记阅读状态。"

    parts: list[str] = []
    if focus_count:
        parts.append(f"{focus_count} 篇重点论文")
    if reading_count:
        parts.append(f"{reading_count} 篇继续阅读与分析")
    if action_count:
        parts.append(f"{action_count} 项下一步动作")
    if metadata_count:
        parts.append(f"{metadata_count} 条元数据补全提醒")
    if triage_count:
        parts.append(f"{triage_count} 篇新导入待筛选")

    if not parts:
        return (
            f"今日已检查 {pulse_result.total_source_papers} 篇已导入论文，"
            "当前没有适合放入公众号摘要的重点项。"
        )
    return (
        f"今日已从 {pulse_result.total_source_papers} 篇已导入论文中整理出 "
        f"{'，'.join(parts)}，共准备 {highlight_count} 条公众号摘要重点。"
    )


def _build_publication_preview(
    *,
    digest_title: str,
    digest_subtitle: str,
    highlights: list[OfficialAccountDailySummaryHighlight],
    settings,
) -> OfficialAccountPublicationPreview:
    article_url = None
    if settings.official_account_default_article_base_url:
        article_url = settings.official_account_default_article_base_url.rstrip("/") + _LANDING_PATH
    return OfficialAccountPublicationPreview(
        digest_title=_normalize_text(digest_title, limit=80),
        digest_subtitle=_normalize_text(digest_subtitle, limit=120),
        digest_highlights=highlights,
        primary_cta_text="查看今日摘要",
        primary_cta_path=_LANDING_PATH,
        mini_program_path=_LANDING_PATH.lstrip("/"),
        article_url=article_url,
    )


def _build_template_payload_preview(
    *,
    publication_preview: OfficialAccountPublicationPreview,
    pulse_date: str,
    selected_binding: WeChatIdentityBinding | None,
    settings,
) -> OfficialAccountTemplatePayloadPreview:
    field_mapping = dict(settings.official_account_template_field_mapping_json or {})
    if not field_mapping:
        field_mapping = dict(_DEFAULT_TEMPLATE_FIELD_MAPPING)

    logical_fields = {
        "issue_title": _normalize_text(publication_preview.digest_title, limit=80),
        "issue_date": pulse_date,
        "highlight_count": str(len(publication_preview.digest_highlights)),
        "summary": _normalize_text(publication_preview.digest_subtitle, limit=120),
        "remark": _normalize_text(
            f"点击查看今日摘要，落地路径：{publication_preview.primary_cta_path}",
            limit=120,
        ),
    }
    payload_preview: dict[str, Any] = {
        "data": {
            template_field: {"value": logical_fields[logical_field]}
            for logical_field, template_field in field_mapping.items()
            if logical_field in logical_fields and template_field
        }
    }
    if settings.wechat_official_digest_template_id:
        payload_preview["template_id"] = settings.wechat_official_digest_template_id
    if selected_binding is not None:
        payload_preview["touser_masked"] = _mask_openid(selected_binding.openid)
        payload_preview["binding_id"] = str(selected_binding.id)
    if publication_preview.article_url:
        payload_preview["url"] = publication_preview.article_url
    if (
        settings.official_account_default_mini_program_app_id
        and publication_preview.mini_program_path
    ):
        payload_preview["miniprogram"] = {
            "appid": settings.official_account_default_mini_program_app_id,
            "pagepath": publication_preview.mini_program_path,
        }

    return OfficialAccountTemplatePayloadPreview(
        template_id_configured=bool(settings.wechat_official_digest_template_id),
        field_mapping=field_mapping,
        logical_fields=logical_fields,
        payload_preview=payload_preview,
    )


def _build_binding_preview(
    *,
    active_bindings: list[WeChatIdentityBinding],
    selected_binding: WeChatIdentityBinding | None,
) -> OfficialAccountBindingPreview:
    notes = [
        "当前只预览摘要与 payload，不会创建真实发送任务。",
    ]
    if not active_bindings:
        notes.append("尚未发现已订阅且启用 digest 的公众号绑定。")
    elif selected_binding is None:
        notes.append("当前未指定预览绑定，后续真实投递阶段仍需明确目标绑定。")
    else:
        notes.append("当前预览绑定仅用于展示模板 payload 的目标形状。")

    selected_binding_preview = None
    if selected_binding is not None:
        selected_binding_preview = OfficialAccountBindingTargetPreview(
            binding_id=selected_binding.id,
            channel_type=selected_binding.channel_type,
            bind_state=selected_binding.bind_state,
            display_label=selected_binding.display_label,
            subscribed=selected_binding.subscribed,
            digest_enabled=selected_binding.digest_enabled,
            masked_openid=_mask_openid(selected_binding.openid),
        )

    return OfficialAccountBindingPreview(
        active_binding_count=len(active_bindings),
        selected_binding=selected_binding_preview,
        notes=notes,
    )


def _build_provider_preview(settings) -> OfficialAccountProviderPreview:
    notes = [
        "本阶段只做公众号摘要草稿和 payload 预览，不要求 provider 进入真实发送模式。",
    ]
    if settings.official_account_provider_mode == OfficialAccountProviderMode.DISABLED:
        notes.append("当前 provider mode 为 disabled，但这不影响摘要草稿预览。")
    if not settings.wechat_official_digest_template_id:
        notes.append("未配置模板 ID，后续真实投递前需要补齐。")
    if not settings.official_account_template_field_mapping_json:
        notes.append("当前使用内置模板字段映射默认值。")
    return OfficialAccountProviderPreview(
        provider_mode=settings.official_account_provider_mode,
        transport_kind=settings.official_account_transport_kind,
        template_id_configured=bool(settings.wechat_official_digest_template_id),
        template_field_mapping_configured=bool(
            settings.official_account_template_field_mapping_json
        ),
        article_base_url_configured=bool(settings.official_account_default_article_base_url),
        mini_program_app_id_configured=bool(settings.official_account_default_mini_program_app_id),
        callback_enabled=settings.official_account_callback_enabled,
        real_send_enabled=settings.official_account_real_send_enabled,
        notes=notes,
    )


def _build_item_summary_line(item: ResearchPulseItem) -> str:
    parts = [_normalize_text(item.reason, limit=90)]
    if item.suggested_action and item.suggested_action != item.reason:
        parts.append(f"建议：{_normalize_text(item.suggested_action, limit=40)}")
    return _normalize_text("；".join(part for part in parts if part), limit=120)


def _build_daily_summary_draft_id(
    *,
    source_draft_id: str,
    selected_binding: WeChatIdentityBinding | None,
    max_highlights: int,
) -> str:
    binding_fragment = "none" if selected_binding is None else str(selected_binding.id)
    digest = hashlib.sha1(
        f"official-account:{source_draft_id}:{binding_fragment}:{max_highlights}".encode()
    ).hexdigest()
    return digest[:16]


def _mask_openid(openid: str) -> str:
    text = openid.strip()
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:3]}***{text[-2:]}"


def _section_item_count(
    sections: list[OfficialAccountDailySummarySection],
    section_id: str,
) -> int:
    for section in sections:
        if section.section_id == section_id:
            return len(section.items)
    return 0


def _normalize_text(value: str, *, limit: int) -> str:
    text = " ".join(value.strip().split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
