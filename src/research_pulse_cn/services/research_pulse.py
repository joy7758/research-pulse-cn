"""Research pulse drafts generated from imported papers and progress context."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.domain.enums import (
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.paper_progress import (
    PaperProgressItemRead,
    PaperProgressPulseContextRead,
)
from research_pulse_cn.schemas.research_pulse import (
    ResearchPulseItem,
    ResearchPulseRequest,
    ResearchPulseResult,
    ResearchPulseSection,
)
from research_pulse_cn.services.paper_progress import PaperProgressWorkbenchService

_ACTIVE_PRIORITIES = {PaperPriorityLevel.URGENT, PaperPriorityLevel.HIGH}
_ACTIVE_READING_STATUSES = {PaperReadingStatus.READING, PaperReadingStatus.SKIMMING}
_ACTIVE_RESEARCH_STAGES = {PaperResearchStage.REVIEWING, PaperResearchStage.RELEVANT}
_NEW_IMPORT_RESEARCH_STAGES = {PaperResearchStage.INBOX, PaperResearchStage.TRIAGE}

_PRIORITY_ORDER = {
    PaperPriorityLevel.URGENT: 0,
    PaperPriorityLevel.HIGH: 1,
    PaperPriorityLevel.NORMAL: 2,
    PaperPriorityLevel.LOW: 3,
}
_READING_STATUS_ORDER = {
    PaperReadingStatus.READING: 0,
    PaperReadingStatus.SKIMMING: 1,
    PaperReadingStatus.UNREAD: 2,
    PaperReadingStatus.READ: 3,
    PaperReadingStatus.ARCHIVED: 4,
}
_RESEARCH_STAGE_ORDER = {
    PaperResearchStage.REVIEWING: 0,
    PaperResearchStage.RELEVANT: 1,
    PaperResearchStage.TRIAGE: 2,
    PaperResearchStage.INBOX: 3,
    PaperResearchStage.CITED: 4,
    PaperResearchStage.IMPLEMENTED: 5,
    PaperResearchStage.PARKED: 6,
}


class ResearchPulseService:
    """Build deterministic Chinese research pulse drafts from imported papers."""

    def __init__(
        self,
        session: Session,
        *,
        progress_service: PaperProgressWorkbenchService | None = None,
        now_provider=None,
    ) -> None:
        self.user_repository = UserRepository(session)
        self.progress_service = progress_service or PaperProgressWorkbenchService(session)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def generate_daily_pulse(self, request: ResearchPulseRequest) -> ResearchPulseResult:
        if self.user_repository.get(request.user_id) is None:
            raise NotFoundError(f"user {request.user_id} was not found")

        warnings: list[str] = []
        timezone_name = request.timezone
        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            timezone_name = "Asia/Shanghai"
            timezone = ZoneInfo(timezone_name)
            warnings.append("未识别的时区已回退到 Asia/Shanghai。")

        now = self.now_provider()
        pulse_date = request.pulse_date or now.astimezone(timezone).date()
        if not request.dry_run:
            warnings.append("Pivot-5 当前只生成本地草稿，不会持久化保存或触发投递。")

        source_items = self.progress_service.list_papers_for_pulse_context(
            user_id=request.user_id,
            include_archived=request.include_archived,
            source_format_filter=request.source_format_filter,
        )
        progress_context = self.progress_service.get_progress_context_for_pulse(
            user_id=request.user_id,
            limit=max(10, request.max_items_per_section),
        )
        sections = self._build_sections(
            source_items=source_items,
            request=request,
        )
        total_items = sum(len(section.items) for section in sections)
        warnings.extend(_build_global_warnings(source_items=source_items, sections=sections))

        title = f"{pulse_date.isoformat()} 科研 Pulse 草稿"
        summary = _build_summary(source_items=source_items, sections=sections)
        source_context_notes = _build_source_context_notes(
            progress_context=progress_context,
            include_archived=request.include_archived,
            include_low_priority=request.include_low_priority,
            source_format_filter=request.source_format_filter,
        )
        draft_id = _build_draft_id(
            request=request,
            pulse_date=pulse_date.isoformat(),
            source_items=source_items,
            sections=sections,
        )

        return ResearchPulseResult(
            draft_id=draft_id,
            user_id=request.user_id,
            pulse_date=pulse_date,
            timezone=timezone_name,
            dry_run=request.dry_run,
            title=title,
            summary=summary,
            sections=sections,
            total_source_papers=len(source_items),
            total_items=total_items,
            warnings=_dedupe_preserving_order(warnings),
            generated_at=now,
            source_context_notes=source_context_notes,
        )

    def _build_sections(
        self,
        *,
        source_items: list[PaperProgressItemRead],
        request: ResearchPulseRequest,
    ) -> list[ResearchPulseSection]:
        max_items = request.max_items_per_section
        return [
            _build_section(
                section_id="today_focus",
                title="今日重点论文",
                description="优先处理高优先级、已有下一步动作、且仍在推进中的论文。",
                candidates=_rank_focus_items(
                    source_items,
                    include_low_priority=request.include_low_priority,
                ),
                max_items=max_items,
                empty_reason="当前没有需要优先推进的高优先级论文。",
            ),
            _build_section(
                section_id="continue_reading",
                title="继续阅读与分析",
                description="继续推进略读、精读和阅读分析阶段的论文。",
                candidates=_rank_continue_reading_items(source_items),
                max_items=max_items,
                empty_reason="当前没有正在推进阅读分析的论文。",
            ),
            _build_section(
                section_id="next_actions",
                title="下一步动作",
                description="直接执行已经明确写下 next_action 的论文任务。",
                candidates=_rank_next_action_items(source_items),
                max_items=max_items,
                empty_reason="当前没有已定义下一步动作的论文。",
            ),
            _build_section(
                section_id="metadata_attention",
                title="元数据待补全",
                description="优先补齐作者、年份、来源和 DOI 等关键元数据。",
                candidates=_rank_metadata_attention_items(source_items),
                max_items=max_items,
                empty_reason="当前没有明显需要补全元数据的论文记录。",
            ),
            _build_section(
                section_id="newly_imported_triage",
                title="新导入待筛选",
                description="帮助把新导入但尚未筛选的论文尽快进入研究流程。",
                candidates=_rank_newly_imported_items(source_items),
                max_items=max_items,
                empty_reason="当前没有处于收件箱或待筛选阶段的新导入论文。",
            ),
        ]


def _build_section(
    *,
    section_id: str,
    title: str,
    description: str,
    candidates: list[PaperProgressItemRead],
    max_items: int,
    empty_reason: str,
) -> ResearchPulseSection:
    items = [
        _build_section_item(section_id=section_id, item=item) for item in candidates[:max_items]
    ]
    return ResearchPulseSection(
        section_id=section_id,
        title=title,
        description=description,
        items=items,
        empty_reason=None if items else empty_reason,
    )


def _build_section_item(
    *,
    section_id: str,
    item: PaperProgressItemRead,
) -> ResearchPulseItem:
    return ResearchPulseItem(
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
        reason=_build_reason(section_id=section_id, item=item),
        suggested_action=_build_suggested_action(section_id=section_id, item=item),
        metadata_warnings=list(item.warnings),
        tags=list(item.tags),
        source_format=item.source_format,
    )


def _rank_focus_items(
    items: list[PaperProgressItemRead],
    *,
    include_low_priority: bool,
) -> list[PaperProgressItemRead]:
    candidates = [
        item
        for item in items
        if item.priority in _ACTIVE_PRIORITIES
        or (
            include_low_priority
            and item.priority in {PaperPriorityLevel.NORMAL, PaperPriorityLevel.LOW}
            and bool(item.next_action)
        )
    ]
    return sorted(candidates, key=lambda item: _pulse_sort_key(item, section_id="today_focus"))


def _rank_continue_reading_items(items: list[PaperProgressItemRead]) -> list[PaperProgressItemRead]:
    candidates = [
        item
        for item in items
        if item.reading_status in _ACTIVE_READING_STATUSES
        or item.research_stage in _ACTIVE_RESEARCH_STAGES
    ]
    return sorted(
        candidates,
        key=lambda item: _pulse_sort_key(item, section_id="continue_reading"),
    )


def _rank_next_action_items(items: list[PaperProgressItemRead]) -> list[PaperProgressItemRead]:
    candidates = [item for item in items if bool(item.next_action)]
    return sorted(candidates, key=lambda item: _pulse_sort_key(item, section_id="next_actions"))


def _rank_metadata_attention_items(
    items: list[PaperProgressItemRead],
) -> list[PaperProgressItemRead]:
    candidates = [item for item in items if bool(item.warnings)]
    return sorted(
        candidates,
        key=lambda item: _pulse_sort_key(item, section_id="metadata_attention"),
    )


def _rank_newly_imported_items(items: list[PaperProgressItemRead]) -> list[PaperProgressItemRead]:
    candidates = [
        item
        for item in items
        if item.research_stage in _NEW_IMPORT_RESEARCH_STAGES
        and item.reading_status == PaperReadingStatus.UNREAD
    ]
    return sorted(
        candidates,
        key=lambda item: _pulse_sort_key(item, section_id="newly_imported_triage"),
    )


def _pulse_sort_key(
    item: PaperProgressItemRead,
    *,
    section_id: str,
) -> tuple[object, ...]:
    next_action_rank = 0 if item.next_action else 1
    metadata_rank = 0 if item.warnings else 1
    recency_reference = item.last_touch_at or item.updated_at or item.created_at
    section_bias = {
        "today_focus": (0 if item.priority in _ACTIVE_PRIORITIES else 1, next_action_rank),
        "continue_reading": (0 if item.reading_status == PaperReadingStatus.READING else 1, 0),
        "next_actions": (next_action_rank, 0),
        "metadata_attention": (metadata_rank, 0),
        "newly_imported_triage": (
            0 if item.research_stage == PaperResearchStage.INBOX else 1,
            0 if item.reading_status == PaperReadingStatus.UNREAD else 1,
        ),
    }[section_id]
    return (
        section_bias,
        _PRIORITY_ORDER[item.priority],
        next_action_rank,
        _READING_STATUS_ORDER[item.reading_status],
        _RESEARCH_STAGE_ORDER[item.research_stage],
        -recency_reference.timestamp(),
        item.title.lower(),
        str(item.paper_id),
    )


def _build_reason(*, section_id: str, item: PaperProgressItemRead) -> str:
    if section_id == "today_focus":
        segments = [f"该论文当前标记为 {item.priority.value} 优先级"]
        if item.next_action:
            segments.append("且已经定义下一步动作")
        if item.reading_status == PaperReadingStatus.READING:
            segments.append("目前处于精读中")
        elif item.research_stage == PaperResearchStage.REVIEWING:
            segments.append("当前处于阅读分析阶段")
        return "，".join(segments) + "，适合作为今天的重点推进对象。"

    if section_id == "continue_reading":
        if item.reading_status == PaperReadingStatus.READING:
            return "该论文处于精读中，建议继续整理方法、实验设计与关键结论。"
        if item.reading_status == PaperReadingStatus.SKIMMING:
            return "该论文仍在略读阶段，建议尽快判断其与当前课题的相关性。"
        return "该论文仍在阅读分析流程中，适合继续推进阅读和比较工作。"

    if section_id == "next_actions":
        return "该论文已经有明确的下一步动作，适合直接转入执行。"

    if section_id == "metadata_attention":
        missing_topics = _summarize_missing_metadata(item)
        return f"该记录仍缺少 {missing_topics} 等关键元数据，后续筛选和引用追踪会受限。"

    return "该论文刚导入且仍处于待筛选阶段，建议先完成相关性判断。"


def _build_suggested_action(*, section_id: str, item: PaperProgressItemRead) -> str:
    if item.next_action:
        return item.next_action
    if section_id == "today_focus":
        return "先明确今天要推进的阅读、比较或整理动作。"
    if section_id == "continue_reading":
        return "继续阅读并补齐方法、实验和结论要点。"
    if section_id == "metadata_attention":
        return "先补全作者、年份、期刊或 DOI 等基础元数据。"
    if section_id == "newly_imported_triage":
        return "先判断是否与当前研究问题相关，并决定保留、推进或暂缓。"
    return "根据当前研究阶段补充一个清晰的下一步动作。"


def _summarize_missing_metadata(item: PaperProgressItemRead) -> str:
    missing: list[str] = []
    if not item.authors:
        missing.append("作者")
    if item.year is None:
        missing.append("年份")
    if not item.venue:
        missing.append("来源")
    if not item.doi:
        missing.append("DOI")
    if item.source_format is None:
        missing.append("导入来源格式")
    if not missing:
        return "部分关键信息"
    return "、".join(missing[:3])


def _build_summary(
    *,
    source_items: list[PaperProgressItemRead],
    sections: list[ResearchPulseSection],
) -> str:
    if not source_items:
        return "当前没有可用于生成 Research Pulse 的已导入论文。"

    section_map = {section.section_id: section for section in sections}
    focus_count = len(section_map["today_focus"].items)
    reading_count = len(section_map["continue_reading"].items)
    next_action_count = len(section_map["next_actions"].items)
    metadata_count = len(section_map["metadata_attention"].items)
    new_import_count = len(section_map["newly_imported_triage"].items)

    segments = [
        f"今日已从 {len(source_items)} 篇已导入论文中整理出 {focus_count} 篇重点推进论文",
        f"{reading_count} 篇继续阅读与分析论文",
        f"{next_action_count} 项明确的下一步动作",
    ]
    if metadata_count:
        segments.append(f"{metadata_count} 条元数据补全提醒")
    if new_import_count:
        segments.append(f"{new_import_count} 篇新导入待筛选论文")
    return "，".join(segments) + "。"


def _build_global_warnings(
    *,
    source_items: list[PaperProgressItemRead],
    sections: list[ResearchPulseSection],
) -> list[str]:
    warnings: list[str] = []
    if not source_items:
        warnings.append("当前用户没有可用于生成 Pulse 草稿的已导入论文。")
    for section in sections:
        if not section.items and section.empty_reason:
            warnings.append(section.empty_reason)
    return warnings


def _build_source_context_notes(
    *,
    progress_context: PaperProgressPulseContextRead,
    include_archived: bool,
    include_low_priority: bool,
    source_format_filter: list[Any],
) -> list[str]:
    notes = list(progress_context.notes)
    notes.append("本草稿仅基于本地已导入论文和论文进度上下文生成，不包含外部检索或外部模型推理。")
    if not include_archived:
        notes.append("默认已排除 archived 阅读状态的论文。")
    if not include_low_priority:
        notes.append("默认不会把 low 优先级论文纳入“今日重点论文” section。")
    if source_format_filter:
        notes.append(
            "本次草稿已按导入来源过滤："
            + "、".join(item.value for item in source_format_filter)
            + "。"
        )
    return _dedupe_preserving_order(notes)


def _build_draft_id(
    *,
    request: ResearchPulseRequest,
    pulse_date: str,
    source_items: list[PaperProgressItemRead],
    sections: list[ResearchPulseSection],
) -> str:
    payload = {
        "user_id": str(request.user_id),
        "pulse_date": pulse_date,
        "timezone": request.timezone,
        "max_items_per_section": request.max_items_per_section,
        "include_low_priority": request.include_low_priority,
        "include_archived": request.include_archived,
        "source_format_filter": [item.value for item in request.source_format_filter],
        "papers": [str(item.paper_id) for item in source_items],
        "sections": [
            {
                "section_id": section.section_id,
                "items": [str(item.paper_id) for item in section.items],
            }
            for section in sections
        ],
    }
    digest = hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()
    return digest[:16]


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
