"""Desktop notification drafts generated from paper-based research pulse data."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from research_pulse_cn.domain.enums import (
    DesktopNotificationActionKind,
    DesktopNotificationDeliveryState,
    DesktopNotificationType,
    DesktopNotificationUrgency,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)
from research_pulse_cn.schemas.desktop_notification import (
    DesktopNotificationAction,
    DesktopNotificationItem,
    DesktopNotificationRequest,
    DesktopNotificationResult,
)
from research_pulse_cn.schemas.research_pulse import (
    ResearchPulseItem,
    ResearchPulseRequest,
    ResearchPulseSection,
)
from research_pulse_cn.services.research_pulse import ResearchPulseService

_ACTIONABLE_SECTION_IDS = (
    "today_focus",
    "next_actions",
    "metadata_attention",
    "newly_imported_triage",
)
_ITEM_SECTION_ORDER = (
    "today_focus",
    "next_actions",
    "metadata_attention",
    "newly_imported_triage",
    "continue_reading",
)
_ACTIVE_NOTIFICATION_PRIORITIES = {PaperPriorityLevel.URGENT, PaperPriorityLevel.HIGH}
_FOCUS_NOTIFICATION_READING_STATUSES = {
    PaperReadingStatus.READING,
    PaperReadingStatus.SKIMMING,
}
_FOCUS_NOTIFICATION_RESEARCH_STAGES = {
    PaperResearchStage.REVIEWING,
    PaperResearchStage.RELEVANT,
}


class DesktopNotificationService:
    """Build deterministic desktop notification drafts without local client delivery."""

    def __init__(
        self,
        session: Session,
        *,
        research_pulse_service: ResearchPulseService | None = None,
        now_provider=None,
    ) -> None:
        self.research_pulse_service = research_pulse_service or ResearchPulseService(session)
        self.now_provider = now_provider or (lambda: datetime.now(UTC))

    def generate_daily_notification_draft(
        self,
        request: DesktopNotificationRequest,
    ) -> DesktopNotificationResult:
        pulse_result = self.research_pulse_service.generate_daily_pulse(
            ResearchPulseRequest(
                user_id=request.user_id,
                pulse_date=request.pulse_date,
                timezone=request.timezone,
                max_items_per_section=request.max_items,
                include_low_priority=request.include_low_priority,
                include_archived=request.include_archived,
                source_format_filter=request.source_format_filter,
                dry_run=True,
            )
        )

        sections_by_id = {section.section_id: section for section in pulse_result.sections}
        items = _select_notification_items(
            pulse_result.sections,
            max_items=request.max_items,
            include_low_priority=request.include_low_priority,
        )
        badge_count = _build_badge_count(
            sections_by_id,
            include_low_priority=request.include_low_priority,
        )
        urgency = _build_urgency(
            sections_by_id,
            items,
            include_low_priority=request.include_low_priority,
        )
        title = _build_title(
            title_prefix=request.title_prefix,
            total_source_papers=pulse_result.total_source_papers,
            sections_by_id=sections_by_id,
            include_low_priority=request.include_low_priority,
        )
        body = _build_body(
            total_source_papers=pulse_result.total_source_papers,
            sections_by_id=sections_by_id,
            include_low_priority=request.include_low_priority,
        )
        deep_link = _build_daily_pulse_deep_link(pulse_result.pulse_date.isoformat())
        actions = (
            _build_actions(
                sections_by_id=sections_by_id,
                pulse_date=pulse_result.pulse_date.isoformat(),
                total_source_papers=pulse_result.total_source_papers,
                include_low_priority=request.include_low_priority,
            )
            if request.include_actions
            else []
        )
        generated_at = self.now_provider()

        warnings = list(pulse_result.warnings)
        if not request.dry_run:
            warnings.append("Pivot-7 当前只生成桌面通知草稿，不会进入实际投递流程。")
        if pulse_result.total_source_papers == 0:
            warnings.append("当前没有可用于桌面提醒的论文进度内容。")
        if not request.include_actions:
            warnings.append("当前请求已关闭 actions 输出，仅保留通知正文与 payload 预览。")

        payload_preview = {
            "notification_title": title,
            "notification_body": body,
            "badge_count": badge_count,
            "urgency": urgency.value,
            "deep_link": deep_link,
            "actions": [
                {
                    "action_id": action.action_id,
                    "label": action.label,
                    "kind": action.kind.value,
                    "deep_link": action.deep_link,
                    "payload": action.payload,
                }
                for action in actions
            ],
            "source_pulse_draft_id": pulse_result.draft_id,
            "generated_at": generated_at.isoformat(),
            "delivery_state": DesktopNotificationDeliveryState.DRAFT.value,
            "notification_type": DesktopNotificationType.DAILY_RESEARCH_PULSE.value,
        }

        return DesktopNotificationResult(
            draft_id=_build_notification_draft_id(
                source_draft_id=pulse_result.draft_id,
                include_actions=request.include_actions,
                max_items=request.max_items,
            ),
            source_research_pulse_draft_id=pulse_result.draft_id,
            user_id=request.user_id,
            pulse_date=pulse_result.pulse_date,
            timezone=pulse_result.timezone,
            title=title,
            body=body,
            notification_type=DesktopNotificationType.DAILY_RESEARCH_PULSE,
            urgency=urgency,
            badge_count=badge_count,
            items=items,
            actions=actions,
            deep_link=deep_link,
            payload_preview=payload_preview,
            total_source_papers=pulse_result.total_source_papers,
            total_items=len(items),
            warnings=_dedupe_preserving_order(warnings),
            generated_at=generated_at,
            delivery_state=DesktopNotificationDeliveryState.DRAFT,
            delivery_notes=[
                "当前结果仅为桌面端本地提醒草稿。",
                "后续桌面客户端可复用 payload_preview、actions 和 deep_link 占位信息。",
            ],
        )


def _select_notification_items(
    sections: list[ResearchPulseSection],
    *,
    max_items: int,
    include_low_priority: bool,
) -> list[DesktopNotificationItem]:
    section_map = {section.section_id: section for section in sections}
    selected: list[DesktopNotificationItem] = []
    seen_paper_ids: set[str] = set()
    for section_id in _ITEM_SECTION_ORDER:
        section = section_map.get(section_id)
        if section is None:
            continue
        for item in section.items:
            if not _should_include_notification_item(
                item,
                section_id=section_id,
                include_low_priority=include_low_priority,
            ):
                continue
            paper_id = str(item.paper_id)
            if paper_id in seen_paper_ids:
                continue
            seen_paper_ids.add(paper_id)
            selected.append(_build_notification_item(item))
            if len(selected) >= max_items:
                return selected
    return selected


def _build_notification_item(item: ResearchPulseItem) -> DesktopNotificationItem:
    return DesktopNotificationItem(
        paper_id=item.paper_id,
        title=item.title,
        line=_build_item_line(item),
        reason=item.reason,
        suggested_action=item.suggested_action,
        priority=item.priority,
        reading_status=item.reading_status,
        research_stage=item.research_stage,
        metadata_warnings=list(item.metadata_warnings),
        url=item.url,
        doi=item.doi,
        tags=list(item.tags),
        source_format=item.source_format,
    )


def _build_item_line(item: ResearchPulseItem) -> str:
    line = _normalize_text(item.reason, limit=70)
    if item.suggested_action and item.suggested_action != item.reason:
        return _normalize_text(f"{line}；建议：{item.suggested_action}", limit=100)
    return line


def _build_title(
    *,
    title_prefix: str,
    total_source_papers: int,
    sections_by_id: dict[str, ResearchPulseSection],
    include_low_priority: bool,
) -> str:
    focus_count = _section_count(
        sections_by_id,
        "today_focus",
        include_low_priority=include_low_priority,
    )
    action_count = _section_count(
        sections_by_id,
        "next_actions",
        include_low_priority=include_low_priority,
    )
    metadata_count = _section_count(sections_by_id, "metadata_attention")
    triage_count = _section_count(sections_by_id, "newly_imported_triage")
    if total_source_papers == 0:
        return f"{title_prefix}：今天没有重点提醒"
    if focus_count:
        return f"{title_prefix}：{focus_count} 个重点事项"
    if action_count:
        return f"{title_prefix}：{action_count} 个下一步动作"
    if metadata_count:
        return f"{title_prefix}：{metadata_count} 条待补全提醒"
    if triage_count:
        return f"{title_prefix}：{triage_count} 篇新导入待筛选"
    return f"{title_prefix}：今天先整理论文队列"


def _build_body(
    *,
    total_source_papers: int,
    sections_by_id: dict[str, ResearchPulseSection],
    include_low_priority: bool,
) -> str:
    if total_source_papers == 0:
        return "今天还没有可提醒的论文进度内容，建议先导入论文并标记阅读状态。"

    focus_count = _section_count(
        sections_by_id,
        "today_focus",
        include_low_priority=include_low_priority,
    )
    action_count = _section_count(
        sections_by_id,
        "next_actions",
        include_low_priority=include_low_priority,
    )
    metadata_count = _section_count(sections_by_id, "metadata_attention")
    triage_count = _section_count(sections_by_id, "newly_imported_triage")

    parts: list[str] = []
    if focus_count:
        parts.append(f"{focus_count} 篇高优先级论文")
    if action_count:
        parts.append(f"{action_count} 个下一步动作")
    if metadata_count:
        parts.append(f"{metadata_count} 条元数据待补全")
    if triage_count:
        parts.append(f"{triage_count} 篇新导入待筛选")

    if parts:
        return "有 " + "、".join(parts) + "。"
    return "今天没有高优先级论文，建议先筛选新导入记录。"


def _build_urgency(
    sections_by_id: dict[str, ResearchPulseSection],
    items: list[DesktopNotificationItem],
    *,
    include_low_priority: bool,
) -> DesktopNotificationUrgency:
    focus_items = _filtered_section_items(
        sections_by_id,
        "today_focus",
        include_low_priority=include_low_priority,
    )
    if any(
        item.priority in {PaperPriorityLevel.URGENT, PaperPriorityLevel.HIGH}
        for item in focus_items
    ):
        return DesktopNotificationUrgency.HIGH
    if any(item.priority == PaperPriorityLevel.URGENT for item in items):
        return DesktopNotificationUrgency.HIGH
    if items:
        return DesktopNotificationUrgency.NORMAL
    return DesktopNotificationUrgency.LOW


def _build_badge_count(
    sections_by_id: dict[str, ResearchPulseSection],
    *,
    include_low_priority: bool,
) -> int:
    seen_paper_ids: set[str] = set()
    count = 0
    for section_id in _ACTIONABLE_SECTION_IDS:
        for item in _filtered_section_items(
            sections_by_id,
            section_id,
            include_low_priority=include_low_priority,
        ):
            paper_id = str(item.paper_id)
            if paper_id in seen_paper_ids:
                continue
            seen_paper_ids.add(paper_id)
            count += 1
            if count >= 99:
                return 99
    return count


def _build_actions(
    *,
    sections_by_id: dict[str, ResearchPulseSection],
    pulse_date: str,
    total_source_papers: int,
    include_low_priority: bool,
) -> list[DesktopNotificationAction]:
    if total_source_papers == 0:
        return []

    actions = [
        DesktopNotificationAction(
            action_id="open_daily_pulse",
            label="查看今日 Pulse",
            kind=DesktopNotificationActionKind.OPEN_DAILY_PULSE,
            deep_link=_build_daily_pulse_deep_link(pulse_date),
            payload={"pulse_date": pulse_date},
        )
    ]
    if _section_count(
        sections_by_id,
        "next_actions",
        include_low_priority=include_low_priority,
    ):
        actions.append(
            DesktopNotificationAction(
                action_id="open_next_actions",
                label="查看下一步动作",
                kind=DesktopNotificationActionKind.OPEN_NEXT_ACTIONS,
                deep_link="research-pulse://papers/progress?filter=next_action",
                payload={"filter": "next_action"},
            )
        )
    if _section_count(sections_by_id, "metadata_attention"):
        actions.append(
            DesktopNotificationAction(
                action_id="open_metadata_attention",
                label="补全元数据",
                kind=DesktopNotificationActionKind.OPEN_METADATA_ATTENTION,
                deep_link="research-pulse://papers/progress?filter=metadata_attention",
                payload={"filter": "metadata_attention"},
            )
        )
    if _section_count(sections_by_id, "newly_imported_triage"):
        actions.append(
            DesktopNotificationAction(
                action_id="open_triage_queue",
                label="筛选新导入论文",
                kind=DesktopNotificationActionKind.OPEN_TRIAGE_QUEUE,
                deep_link="research-pulse://papers/progress?filter=triage",
                payload={"filter": "triage"},
            )
        )
    return actions


def _build_daily_pulse_deep_link(pulse_date: str) -> str:
    return f"research-pulse://pulse/daily/{pulse_date}"


def _section_count(
    sections_by_id: dict[str, ResearchPulseSection],
    section_id: str,
    *,
    include_low_priority: bool = True,
) -> int:
    return len(
        _filtered_section_items(
            sections_by_id,
            section_id,
            include_low_priority=include_low_priority,
        )
    )


def _filtered_section_items(
    sections_by_id: dict[str, ResearchPulseSection],
    section_id: str,
    *,
    include_low_priority: bool,
) -> list[ResearchPulseItem]:
    section = sections_by_id.get(section_id)
    if section is None:
        return []
    return [
        item
        for item in section.items
        if _should_include_notification_item(
            item,
            section_id=section_id,
            include_low_priority=include_low_priority,
        )
    ]


def _should_include_notification_item(
    item: ResearchPulseItem,
    *,
    section_id: str,
    include_low_priority: bool,
) -> bool:
    if not include_low_priority and item.priority == PaperPriorityLevel.LOW:
        return False
    if section_id == "today_focus":
        return _is_focus_notification_item(item, include_low_priority=include_low_priority)
    return True


def _is_focus_notification_item(
    item: ResearchPulseItem,
    *,
    include_low_priority: bool,
) -> bool:
    if item.priority in _ACTIVE_NOTIFICATION_PRIORITIES:
        return (
            bool(item.next_action)
            or item.reading_status in _FOCUS_NOTIFICATION_READING_STATUSES
            or item.research_stage in _FOCUS_NOTIFICATION_RESEARCH_STAGES
        )
    if include_low_priority:
        return bool(item.next_action)
    return False


def _build_notification_draft_id(
    *,
    source_draft_id: str,
    include_actions: bool,
    max_items: int,
) -> str:
    digest = hashlib.sha1(
        f"desktop-notification:{source_draft_id}:{include_actions}:{max_items}".encode()
    ).hexdigest()
    return digest[:16]


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
