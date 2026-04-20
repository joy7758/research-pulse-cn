"""Mini-program detail previews derived from paper progress and research pulse drafts."""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.domain.enums import (
    MiniProgramDetailActionKind,
    MiniProgramDetailCardType,
    MiniProgramDetailDeliveryState,
    MiniProgramDetailType,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.mini_program_detail import (
    MiniProgramDetailAction,
    MiniProgramDetailCard,
    MiniProgramDetailItem,
    MiniProgramDetailRequest,
    MiniProgramDetailResult,
    MiniProgramNavigation,
    MiniProgramShareCard,
)
from research_pulse_cn.schemas.paper_progress import PaperProgressItemRead
from research_pulse_cn.schemas.research_pulse import (
    ResearchPulseItem,
    ResearchPulseRequest,
    ResearchPulseResult,
    ResearchPulseSection,
)
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.paper_progress import PaperProgressWorkbenchService
from research_pulse_cn.services.research_pulse import ResearchPulseService

_DAILY_PULSE_PATH = "/pages/pulse/detail"
_PAPERS_LIST_PATH = "/pages/papers/list"
_PAPER_DETAIL_PATH = "/pages/papers/detail"
_HOME_PATH = "/pages/home/index"
_MINI_REDACTED_FIELDS = [
    "原始导入内容",
    "来源标识占位字段",
    "用户笔记",
    "研究笔记",
    "内部调试字段",
]
_PRIORITY_LABELS = {
    PaperPriorityLevel.URGENT: "紧急",
    PaperPriorityLevel.HIGH: "高优先级",
    PaperPriorityLevel.NORMAL: "普通优先级",
    PaperPriorityLevel.LOW: "低优先级",
}
_READING_STATUS_LABELS = {
    PaperReadingStatus.UNREAD: "未读",
    PaperReadingStatus.SKIMMING: "略读中",
    PaperReadingStatus.READING: "精读中",
    PaperReadingStatus.READ: "已读",
    PaperReadingStatus.ARCHIVED: "已归档",
}
_RESEARCH_STAGE_LABELS = {
    PaperResearchStage.INBOX: "收件箱",
    PaperResearchStage.TRIAGE: "待筛选",
    PaperResearchStage.RELEVANT: "相关",
    PaperResearchStage.REVIEWING: "阅读分析中",
    PaperResearchStage.CITED: "已引用",
    PaperResearchStage.IMPLEMENTED: "已转化为研究动作",
    PaperResearchStage.PARKED: "暂停",
}
_SECTION_CARD_TYPE = {
    "today_focus": MiniProgramDetailCardType.TODAY_FOCUS,
    "continue_reading": MiniProgramDetailCardType.CONTINUE_READING,
    "next_actions": MiniProgramDetailCardType.NEXT_ACTIONS,
    "metadata_attention": MiniProgramDetailCardType.METADATA_ATTENTION,
    "newly_imported_triage": MiniProgramDetailCardType.TRIAGE,
}


class MiniProgramDetailService:
    """Build deterministic mini-program detail previews without any real WeChat integration."""

    def __init__(
        self,
        session: Session,
        *,
        research_pulse_service: ResearchPulseService | None = None,
        progress_service: PaperProgressWorkbenchService | None = None,
        paper_service: PaperService | None = None,
        now_provider=None,
    ) -> None:
        self.user_repository = UserRepository(session)
        self.research_pulse_service = research_pulse_service or ResearchPulseService(session)
        self.progress_service = progress_service or PaperProgressWorkbenchService(session)
        self.paper_service = paper_service or PaperService(session)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def generate_detail_preview(
        self,
        request: MiniProgramDetailRequest,
    ) -> MiniProgramDetailResult:
        if self.user_repository.get(request.user_id) is None:
            raise NotFoundError(f"user {request.user_id} was not found")

        warnings: list[str] = []
        timezone_name, timezone = _resolve_timezone(request.timezone, warnings)
        generated_at = self.now_provider()
        pulse_date = request.pulse_date or generated_at.astimezone(timezone).date()
        if not request.dry_run:
            warnings.append("Pivot-8 当前只生成小程序详情预览，不会进入真实微信或投递流程。")

        if request.detail_type == MiniProgramDetailType.PAPER:
            payload = self._build_paper_detail(
                request=request,
                pulse_date=pulse_date,
            )
        else:
            pulse_result = self.research_pulse_service.generate_daily_pulse(
                ResearchPulseRequest(
                    user_id=request.user_id,
                    pulse_date=pulse_date,
                    timezone=timezone_name,
                    max_items_per_section=request.max_items,
                    include_low_priority=request.include_low_priority,
                    include_archived=request.include_archived,
                    source_format_filter=request.source_format_filter,
                    dry_run=True,
                )
            )
            if (
                request.source_research_pulse_draft_id
                and request.source_research_pulse_draft_id != pulse_result.draft_id
            ):
                warnings.append(
                    "当前 source_research_pulse_draft_id 仅作为前端占位，已返回现算预览结果。"
                )
            payload = self._build_pulse_based_detail(
                request=request,
                pulse_date=pulse_date,
                pulse_result=pulse_result,
            )

        warnings.extend(payload["warnings"])
        visibility_notes = _dedupe_preserving_order(
            payload["visibility_notes"] + _build_visibility_notes(share_safe=request.share_safe)
        )

        return MiniProgramDetailResult(
            detail_id=_build_detail_id(
                user_id=request.user_id,
                detail_type=request.detail_type,
                pulse_date=pulse_date,
                paper_id=request.paper_id,
                source_research_pulse_draft_id=payload["source_research_pulse_draft_id"],
                share_safe=request.share_safe,
                max_items=request.max_items,
            ),
            detail_type=request.detail_type,
            user_id=request.user_id,
            pulse_date=pulse_date,
            timezone=timezone_name,
            title=payload["title"],
            subtitle=payload["subtitle"],
            summary=payload["summary"],
            cards=payload["cards"],
            actions=payload["actions"],
            share_card=payload["share_card"],
            navigation=payload["navigation"],
            source_research_pulse_draft_id=payload["source_research_pulse_draft_id"],
            total_source_papers=payload["total_source_papers"],
            total_items=payload["total_items"],
            warnings=_dedupe_preserving_order(warnings),
            generated_at=generated_at,
            delivery_state=MiniProgramDetailDeliveryState.PREVIEW,
            visibility_notes=visibility_notes,
        )

    def _build_pulse_based_detail(
        self,
        *,
        request: MiniProgramDetailRequest,
        pulse_date: date,
        pulse_result: ResearchPulseResult,
    ) -> dict[str, Any]:
        section_map = {section.section_id: section for section in pulse_result.sections}
        if request.detail_type == MiniProgramDetailType.DAILY_PULSE:
            return _build_daily_pulse_detail_payload(
                pulse_date=pulse_date,
                pulse_result=pulse_result,
                section_map=section_map,
                share_safe=request.share_safe,
                include_low_priority=request.include_low_priority,
            )
        if request.detail_type == MiniProgramDetailType.NEXT_ACTIONS:
            return _build_section_detail_payload(
                pulse_date=pulse_date,
                pulse_result=pulse_result,
                section=_section_or_empty(section_map, "next_actions"),
                detail_type=request.detail_type,
                share_safe=request.share_safe,
                include_low_priority=request.include_low_priority,
            )
        if request.detail_type == MiniProgramDetailType.METADATA_ATTENTION:
            return _build_section_detail_payload(
                pulse_date=pulse_date,
                pulse_result=pulse_result,
                section=_section_or_empty(section_map, "metadata_attention"),
                detail_type=request.detail_type,
                share_safe=request.share_safe,
                include_low_priority=request.include_low_priority,
            )
        return _build_section_detail_payload(
            pulse_date=pulse_date,
            pulse_result=pulse_result,
            section=_section_or_empty(section_map, "newly_imported_triage"),
            detail_type=request.detail_type,
            share_safe=request.share_safe,
            include_low_priority=request.include_low_priority,
        )

    def _build_paper_detail(
        self,
        *,
        request: MiniProgramDetailRequest,
        pulse_date: date,
    ) -> dict[str, Any]:
        warnings: list[str] = []
        current_path = _paper_detail_path(request.paper_id)
        if request.paper_id is None:
            warnings.append("paper detail 预览需要提供 paper_id。")
            return _build_empty_paper_payload(
                pulse_date=pulse_date,
                current_path=current_path,
                warnings=warnings,
                share_safe=request.share_safe,
            )

        try:
            paper = self.paper_service.get_paper(request.paper_id)
        except NotFoundError:
            warnings.append("未找到对应的论文，当前返回空状态预览。")
            return _build_empty_paper_payload(
                pulse_date=pulse_date,
                current_path=current_path,
                warnings=warnings,
                share_safe=request.share_safe,
            )

        if paper.user_id != request.user_id:
            warnings.append("该论文不属于当前用户，当前返回空状态预览。")
            return _build_empty_paper_payload(
                pulse_date=pulse_date,
                current_path=current_path,
                warnings=warnings,
                share_safe=request.share_safe,
            )

        progress_item = self.progress_service.get_progress_item(request.paper_id)
        if (
            progress_item.reading_status == PaperReadingStatus.ARCHIVED
            and not request.include_archived
        ):
            warnings.append("当前请求默认排除了 archived 论文，请启用 include_archived 后重试。")
            return _build_empty_paper_payload(
                pulse_date=pulse_date,
                current_path=current_path,
                warnings=warnings,
                share_safe=request.share_safe,
            )

        if request.source_format_filter and progress_item.source_format not in set(
            request.source_format_filter
        ):
            warnings.append("当前请求已按导入来源过滤，目标论文不在允许的 source_format 范围内。")
            return _build_empty_paper_payload(
                pulse_date=pulse_date,
                current_path=current_path,
                warnings=warnings,
                share_safe=request.share_safe,
            )

        safe_abstract = _extract_safe_abstract(paper.identifiers, share_safe=request.share_safe)
        item = _build_item_from_progress_item(
            progress_item,
            reason=_paper_reason(progress_item),
            suggested_action=_paper_suggested_action(progress_item),
            safe_abstract=safe_abstract,
        )
        card = MiniProgramDetailCard(
            card_id=f"paper-{progress_item.paper_id}",
            card_type=MiniProgramDetailCardType.PAPER_DETAIL,
            title="论文详情",
            subtitle=_paper_card_subtitle(progress_item),
            body=_paper_card_body(progress_item),
            items=[item],
            badges=[
                _PRIORITY_LABELS[progress_item.priority],
                _READING_STATUS_LABELS[progress_item.reading_status],
                _RESEARCH_STAGE_LABELS[progress_item.research_stage],
            ],
            warnings=_sanitize_warnings(progress_item.warnings, share_safe=request.share_safe),
            empty_reason=None,
        )
        current_path = _paper_detail_path(progress_item.paper_id)
        summary = _paper_summary(progress_item)
        actions = _dedupe_actions(
            [
                MiniProgramDetailAction(
                    action_id="open_daily_pulse",
                    label="查看今日 Pulse",
                    kind=MiniProgramDetailActionKind.OPEN_DAILY_PULSE,
                    path=_daily_pulse_path(pulse_date),
                    payload={"date": pulse_date.isoformat()},
                ),
                MiniProgramDetailAction(
                    action_id="open_papers_list",
                    label="返回论文列表",
                    kind=MiniProgramDetailActionKind.OPEN_PAPERS_LIST,
                    path=_papers_list_path(),
                    payload={},
                ),
            ]
            + _conditional_paper_actions(progress_item)
        )
        return {
            "title": progress_item.title,
            "subtitle": "论文详情预览",
            "summary": summary,
            "cards": [card],
            "actions": actions,
            "share_card": _build_share_card(
                title=f"论文详情：{progress_item.title}",
                summary=summary,
                path=current_path,
                share_safe=request.share_safe,
            ),
            "navigation": MiniProgramNavigation(
                current_path=current_path,
                back_path=_daily_pulse_path(pulse_date),
                related_paths=_dedupe_preserving_order(
                    [
                        _papers_list_path(),
                        _next_actions_path(),
                        _metadata_attention_path(),
                    ]
                ),
            ),
            "source_research_pulse_draft_id": request.source_research_pulse_draft_id,
            "total_source_papers": 1,
            "total_items": 1,
            "warnings": warnings,
            "visibility_notes": [
                "当前 paper detail 预览只暴露适合小程序详情页展示的论文基础字段。",
            ],
        }


def _build_daily_pulse_detail_payload(
    *,
    pulse_date: date,
    pulse_result: ResearchPulseResult,
    section_map: dict[str, ResearchPulseSection],
    share_safe: bool,
    include_low_priority: bool,
) -> dict[str, Any]:
    filtered_sections = {
        section_id: _filter_section_for_detail(
            _section_or_empty(section_map, section_id),
            include_low_priority=include_low_priority,
        )
        for section_id in (
            "today_focus",
            "continue_reading",
            "next_actions",
            "metadata_attention",
            "newly_imported_triage",
        )
    }
    cards = [
        MiniProgramDetailCard(
            card_id="overview",
            card_type=MiniProgramDetailCardType.OVERVIEW,
            title="今日概览",
            subtitle="来自已导入论文与进度上下文的结构化预览",
            body=pulse_result.summary,
            items=[],
            badges=[
                f"重点 {len(filtered_sections['today_focus'].items)}",
                f"动作 {len(filtered_sections['next_actions'].items)}",
                "小程序预览",
            ],
            warnings=[],
            empty_reason=None,
        )
    ]
    for section_id in (
        "today_focus",
        "continue_reading",
        "next_actions",
        "metadata_attention",
        "newly_imported_triage",
    ):
        cards.append(
            _build_card_from_section(
                section=filtered_sections[section_id],
                share_safe=share_safe,
            )
        )
    current_path = _daily_pulse_path(pulse_date)
    return {
        "title": f"{pulse_date.isoformat()} 科研 Pulse 详情",
        "subtitle": "面向微信小程序详情页的结构化预览",
        "summary": pulse_result.summary,
        "cards": cards,
        "actions": _dedupe_actions(
            [
                MiniProgramDetailAction(
                    action_id="open_next_actions",
                    label="查看下一步动作",
                    kind=MiniProgramDetailActionKind.OPEN_NEXT_ACTIONS,
                    path=_next_actions_path(),
                    payload={"filter": "next_action"},
                ),
                MiniProgramDetailAction(
                    action_id="open_metadata_attention",
                    label="查看元数据待补全",
                    kind=MiniProgramDetailActionKind.OPEN_METADATA_ATTENTION,
                    path=_metadata_attention_path(),
                    payload={"filter": "metadata_attention"},
                ),
                MiniProgramDetailAction(
                    action_id="open_triage",
                    label="查看待筛选论文",
                    kind=MiniProgramDetailActionKind.OPEN_TRIAGE,
                    path=_triage_path(),
                    payload={"filter": "triage"},
                ),
            ]
        ),
        "share_card": _build_share_card(
            title=f"{pulse_date.isoformat()} 今日科研 Pulse",
            summary=pulse_result.summary,
            path=current_path,
            share_safe=share_safe,
        ),
        "navigation": MiniProgramNavigation(
            current_path=current_path,
            back_path=_HOME_PATH,
            related_paths=_dedupe_preserving_order(
                [
                    _next_actions_path(),
                    _metadata_attention_path(),
                    _triage_path(),
                    _papers_list_path(),
                ]
            ),
        ),
        "source_research_pulse_draft_id": pulse_result.draft_id,
        "total_source_papers": pulse_result.total_source_papers,
        "total_items": sum(len(card.items) for card in cards),
        "warnings": list(pulse_result.warnings),
        "visibility_notes": [
            "当前 daily_pulse 详情只用于小程序详情页预览，不对应真实微信投递。",
        ],
    }


def _build_section_detail_payload(
    *,
    pulse_date: date,
    pulse_result: ResearchPulseResult,
    section: ResearchPulseSection,
    detail_type: MiniProgramDetailType,
    share_safe: bool,
    include_low_priority: bool,
) -> dict[str, Any]:
    mapping = {
        MiniProgramDetailType.NEXT_ACTIONS: (
            "下一步动作详情",
            "集中展示当前已定义 next_action 的论文。",
            _next_actions_path(),
            MiniProgramDetailActionKind.OPEN_NEXT_ACTIONS,
            "查看下一步动作",
        ),
        MiniProgramDetailType.METADATA_ATTENTION: (
            "元数据待补全详情",
            "集中展示作者、年份、来源或 DOI 待补全的论文。",
            _metadata_attention_path(),
            MiniProgramDetailActionKind.OPEN_METADATA_ATTENTION,
            "查看元数据待补全",
        ),
        MiniProgramDetailType.TRIAGE: (
            "新导入待筛选详情",
            "集中展示仍处于 inbox / triage / unread 的论文。",
            _triage_path(),
            MiniProgramDetailActionKind.OPEN_TRIAGE,
            "查看待筛选论文",
        ),
    }
    title, subtitle, current_path, action_kind, action_label = mapping[detail_type]
    card = _build_card_from_section(
        section=_filter_section_for_detail(section, include_low_priority=include_low_priority),
        share_safe=share_safe,
    )
    summary = (
        f"当前共有 {len(card.items)} 项适合在小程序里继续处理。"
        if card.items
        else (section.empty_reason or "当前没有可展示的内容。")
    )
    return {
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "cards": [card],
        "actions": _dedupe_actions(
            [
                MiniProgramDetailAction(
                    action_id="open_daily_pulse",
                    label="查看今日 Pulse",
                    kind=MiniProgramDetailActionKind.OPEN_DAILY_PULSE,
                    path=_daily_pulse_path(pulse_date),
                    payload={"date": pulse_date.isoformat()},
                ),
                MiniProgramDetailAction(
                    action_id=action_kind.value,
                    label=action_label,
                    kind=action_kind,
                    path=current_path,
                    payload={"detail_type": detail_type.value},
                ),
            ]
        ),
        "share_card": _build_share_card(
            title=title,
            summary=summary,
            path=current_path,
            share_safe=share_safe,
        ),
        "navigation": MiniProgramNavigation(
            current_path=current_path,
            back_path=_daily_pulse_path(pulse_date),
            related_paths=_dedupe_preserving_order(
                [_daily_pulse_path(pulse_date), _papers_list_path()]
            ),
        ),
        "source_research_pulse_draft_id": pulse_result.draft_id,
        "total_source_papers": pulse_result.total_source_papers,
        "total_items": len(card.items),
        "warnings": list(pulse_result.warnings),
        "visibility_notes": [
            "当前列表详情只包含适合小程序阅读和筛选的结构化字段。",
        ],
    }


def _build_empty_paper_payload(
    *,
    pulse_date: date,
    current_path: str,
    warnings: list[str],
    share_safe: bool,
) -> dict[str, Any]:
    summary = "当前没有可展示的论文详情。"
    return {
        "title": "论文详情预览",
        "subtitle": "当前没有可展示的论文",
        "summary": summary,
        "cards": [
            MiniProgramDetailCard(
                card_id="paper-empty",
                card_type=MiniProgramDetailCardType.PAPER_DETAIL,
                title="论文详情",
                subtitle="空状态",
                body="需要提供有效的论文上下文，才能生成适合小程序消费的详情数据。",
                items=[],
                badges=[],
                warnings=[],
                empty_reason="当前 paper detail 预览没有可展示的论文。",
            )
        ],
        "actions": [
            MiniProgramDetailAction(
                action_id="open_daily_pulse",
                label="查看今日 Pulse",
                kind=MiniProgramDetailActionKind.OPEN_DAILY_PULSE,
                path=_daily_pulse_path(pulse_date),
                payload={"date": pulse_date.isoformat()},
            ),
            MiniProgramDetailAction(
                action_id="open_papers_list",
                label="返回论文列表",
                kind=MiniProgramDetailActionKind.OPEN_PAPERS_LIST,
                path=_papers_list_path(),
                payload={},
            ),
        ],
        "share_card": _build_share_card(
            title="论文详情预览",
            summary=summary,
            path=current_path,
            share_safe=share_safe,
        ),
        "navigation": MiniProgramNavigation(
            current_path=current_path,
            back_path=_daily_pulse_path(pulse_date),
            related_paths=_dedupe_preserving_order(
                [_daily_pulse_path(pulse_date), _papers_list_path()]
            ),
        ),
        "source_research_pulse_draft_id": None,
        "total_source_papers": 0,
        "total_items": 0,
        "warnings": warnings,
        "visibility_notes": [
            "当 paper_id 缺失或无效时，服务返回结构化空状态而不是抛出小程序侧错误。",
        ],
    }


def _build_card_from_section(
    *,
    section: ResearchPulseSection,
    share_safe: bool,
) -> MiniProgramDetailCard:
    items = [_build_item_from_pulse_item(item, share_safe=share_safe) for item in section.items]
    return MiniProgramDetailCard(
        card_id=section.section_id,
        card_type=_SECTION_CARD_TYPE.get(section.section_id, MiniProgramDetailCardType.OVERVIEW),
        title=section.title,
        subtitle=None if section.items else "空状态",
        body=section.description,
        items=items,
        badges=[f"{len(items)} 项"] if items else [],
        warnings=[],
        empty_reason=section.empty_reason,
    )


def _build_item_from_pulse_item(
    item: ResearchPulseItem,
    *,
    share_safe: bool,
) -> MiniProgramDetailItem:
    return MiniProgramDetailItem(
        item_id=f"paper-{item.paper_id}",
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
        metadata_warnings=_sanitize_warnings(item.metadata_warnings, share_safe=share_safe),
        tags=list(item.tags),
        source_format=item.source_format,
        safe_abstract=None,
        detail_path=_paper_detail_path(item.paper_id),
    )


def _build_item_from_progress_item(
    item: PaperProgressItemRead,
    *,
    reason: str,
    suggested_action: str,
    safe_abstract: str | None,
) -> MiniProgramDetailItem:
    return MiniProgramDetailItem(
        item_id=f"paper-{item.paper_id}",
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
        reason=reason,
        suggested_action=suggested_action,
        metadata_warnings=list(item.warnings),
        tags=list(item.tags),
        source_format=item.source_format,
        safe_abstract=safe_abstract,
        detail_path=_paper_detail_path(item.paper_id),
    )


def _paper_reason(item: PaperProgressItemRead) -> str:
    if item.next_action:
        return "该论文已经定义下一步动作，适合在小程序详情页直接查看并继续推进。"
    if item.warnings:
        return "该论文仍有元数据待补全，建议先补齐基础信息再继续后续整理。"
    if item.priority in {PaperPriorityLevel.HIGH, PaperPriorityLevel.URGENT}:
        return "该论文目前处于高优先级推进状态，适合继续跟进研究动作。"
    return "该论文已经进入研究工作台，可继续维护阅读状态、研究阶段和后续动作。"


def _paper_suggested_action(item: PaperProgressItemRead) -> str:
    if item.next_action:
        return item.next_action
    if item.warnings:
        return "先补全作者、年份、来源或 DOI，再继续推进阅读和筛选。"
    if item.reading_status in {PaperReadingStatus.READING, PaperReadingStatus.SKIMMING}:
        return "继续整理方法、实验设计和结论要点。"
    return "补充一个清晰的下一步动作，方便后续在小程序和桌面端继续跟进。"


def _paper_summary(item: PaperProgressItemRead) -> str:
    return (
        f"当前为{_PRIORITY_LABELS[item.priority]}，"
        f"{_READING_STATUS_LABELS[item.reading_status]}，"
        f"研究阶段为{_RESEARCH_STAGE_LABELS[item.research_stage]}。"
    )


def _paper_card_subtitle(item: PaperProgressItemRead) -> str:
    year_text = str(item.year) if item.year is not None else "年份待补全"
    venue_text = item.venue or "来源待补全"
    return f"{year_text} · {venue_text}"


def _paper_card_body(item: PaperProgressItemRead) -> str:
    body = (
        f"当前阅读状态为{_READING_STATUS_LABELS[item.reading_status]}，"
        f"研究阶段为{_RESEARCH_STAGE_LABELS[item.research_stage]}，"
        f"优先级为{_PRIORITY_LABELS[item.priority]}。"
    )
    if item.next_action:
        body += f" 下一步动作：{item.next_action}"
    elif item.warnings:
        body += " 当前仍有元数据待补全。"
    return body


def _conditional_paper_actions(item: PaperProgressItemRead) -> list[MiniProgramDetailAction]:
    actions: list[MiniProgramDetailAction] = []
    if item.next_action:
        actions.append(
            MiniProgramDetailAction(
                action_id="open_next_actions",
                label="查看下一步动作",
                kind=MiniProgramDetailActionKind.OPEN_NEXT_ACTIONS,
                path=_next_actions_path(),
                payload={"filter": "next_action"},
            )
        )
    if item.warnings:
        actions.append(
            MiniProgramDetailAction(
                action_id="open_metadata_attention",
                label="查看元数据待补全",
                kind=MiniProgramDetailActionKind.OPEN_METADATA_ATTENTION,
                path=_metadata_attention_path(),
                payload={"filter": "metadata_attention"},
            )
        )
    return actions


def _build_share_card(
    *,
    title: str,
    summary: str,
    path: str,
    share_safe: bool,
) -> MiniProgramShareCard:
    return MiniProgramShareCard(
        title=_compact_text(title, limit=60),
        summary=_compact_text(summary, limit=120),
        path=path,
        image_placeholder=None,
        share_safe=share_safe,
        redacted_fields=list(_MINI_REDACTED_FIELDS if share_safe else []),
    )


def _sanitize_warnings(warnings: list[str], *, share_safe: bool) -> list[str]:
    filtered: list[str] = []
    for warning in warnings:
        if share_safe and any(
            token in warning.lower()
            for token in ("raw_source_payload", "debug", "internal", "token", "unionid", "openid")
        ):
            continue
        filtered.append(warning)
    return _dedupe_preserving_order(filtered)


def _filter_section_for_detail(
    section: ResearchPulseSection,
    *,
    include_low_priority: bool,
) -> ResearchPulseSection:
    filtered_items = [
        item
        for item in section.items
        if _should_include_section_item(
            item,
            section_id=section.section_id,
            include_low_priority=include_low_priority,
        )
    ]
    return ResearchPulseSection(
        section_id=section.section_id,
        title=section.title,
        description=section.description,
        items=filtered_items,
        empty_reason=section.empty_reason if not filtered_items else None,
    )


def _should_include_section_item(
    item: ResearchPulseItem,
    *,
    section_id: str,
    include_low_priority: bool,
) -> bool:
    if not include_low_priority and item.priority == PaperPriorityLevel.LOW:
        return False
    if section_id == "metadata_attention":
        return _is_metadata_attention_item(item)
    return True


def _is_metadata_attention_item(item: ResearchPulseItem) -> bool:
    metadata_markers = (
        "作者",
        "年份",
        "期刊",
        "会议",
        "来源",
        "DOI",
        "元数据",
        "PDF 文件夹占位导入",
    )
    return any(
        any(marker in warning for marker in metadata_markers) for warning in item.metadata_warnings
    )


def _extract_safe_abstract(identifiers: dict[str, Any], *, share_safe: bool) -> str | None:
    candidates: list[Any] = [identifiers.get("abstract")]
    raw_source_payload = identifiers.get("import_raw_source_payload")
    if isinstance(raw_source_payload, dict):
        candidates.extend(
            [
                raw_source_payload.get("abstract"),
                raw_source_payload.get("AB"),
            ]
        )
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        cleaned = " ".join(candidate.strip().split())
        if not cleaned:
            continue
        return _compact_text(cleaned, limit=180 if share_safe else 300)
    return None


def _build_visibility_notes(*, share_safe: bool) -> list[str]:
    notes = [
        "当前结果仅为小程序详情页 preview，不代表真实微信小程序页面、登录或订阅能力。",
        "当前 path 仅为前端占位路径，不会触发真实微信 API。",
    ]
    if share_safe:
        notes.append("share_safe=true 时，已裁剪原始导入内容、研究笔记和内部调试字段。")
    else:
        notes.append(
            "即使 share_safe=false，当前预览仍不会暴露 token、微信身份字段或原始导入 payload。"
        )
    return notes


def _resolve_timezone(timezone_name: str, warnings: list[str]) -> tuple[str, ZoneInfo]:
    try:
        return timezone_name, ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        warnings.append("未识别的时区已回退到 Asia/Shanghai。")
        return "Asia/Shanghai", ZoneInfo("Asia/Shanghai")


def _build_detail_id(
    *,
    user_id: UUID,
    detail_type: MiniProgramDetailType,
    pulse_date: date,
    paper_id: UUID | None,
    source_research_pulse_draft_id: str | None,
    share_safe: bool,
    max_items: int,
) -> str:
    digest = hashlib.sha1(
        (
            f"mini-detail:{user_id}:{detail_type.value}:{pulse_date.isoformat()}:"
            f"{paper_id}:{source_research_pulse_draft_id}:{share_safe}:{max_items}"
        ).encode()
    ).hexdigest()
    return digest[:16]


def _section_or_empty(
    section_map: dict[str, ResearchPulseSection],
    section_id: str,
) -> ResearchPulseSection:
    return section_map.get(section_id, _empty_section(section_id))


def _empty_section(section_id: str) -> ResearchPulseSection:
    titles = {
        "today_focus": ("今日重点论文", "当前没有需要优先推进的高优先级论文。"),
        "continue_reading": ("继续阅读与分析", "当前没有正在推进阅读分析的论文。"),
        "next_actions": ("下一步动作", "当前没有已定义下一步动作的论文。"),
        "metadata_attention": ("元数据待补全", "当前没有明显需要补全元数据的论文记录。"),
        "newly_imported_triage": ("新导入待筛选", "当前没有处于收件箱或待筛选阶段的新导入论文。"),
    }
    title, empty_reason = titles[section_id]
    return ResearchPulseSection(
        section_id=section_id,
        title=title,
        description=empty_reason,
        items=[],
        empty_reason=empty_reason,
    )


def _daily_pulse_path(pulse_date: date) -> str:
    return f"{_DAILY_PULSE_PATH}?date={pulse_date.isoformat()}"


def _paper_detail_path(paper_id: UUID | None) -> str:
    return _PAPER_DETAIL_PATH if paper_id is None else f"{_PAPER_DETAIL_PATH}?id={paper_id}"


def _next_actions_path() -> str:
    return f"{_PAPERS_LIST_PATH}?filter=next_action"


def _metadata_attention_path() -> str:
    return f"{_PAPERS_LIST_PATH}?filter=metadata_attention"


def _triage_path() -> str:
    return f"{_PAPERS_LIST_PATH}?filter=triage"


def _papers_list_path() -> str:
    return _PAPERS_LIST_PATH


def _compact_text(value: str, *, limit: int) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def _dedupe_actions(actions: list[MiniProgramDetailAction]) -> list[MiniProgramDetailAction]:
    seen: set[tuple[str, str]] = set()
    deduped: list[MiniProgramDetailAction] = []
    for action in actions:
        key = (action.action_id, action.path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(action)
    return deduped


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
