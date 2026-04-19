"""Paper progress workbench service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from research_pulse_cn.db.models import PaperProfile
from research_pulse_cn.domain.enums import (
    PaperImportSourceFormat,
    PaperPriorityLevel,
    PaperReadingStatus,
    PaperResearchStage,
)
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.schemas.paper import PaperProfileUpdate
from research_pulse_cn.schemas.paper_progress import (
    PaperProgressItemRead,
    PaperProgressListResponse,
    PaperProgressPulseContextRead,
    PaperProgressSummaryRead,
    PaperProgressUpdateRequest,
)
from research_pulse_cn.services.paper import PaperService

_PROGRESS_METADATA_KEY = "progress_workbench"
_LEGACY_STAGE_ALIASES: dict[str, PaperResearchStage] = {
    "imported": PaperResearchStage.INBOX,
    "published": PaperResearchStage.RELEVANT,
    "under_review": PaperResearchStage.REVIEWING,
    "revision": PaperResearchStage.REVIEWING,
    "in_prep": PaperResearchStage.TRIAGE,
    "paused": PaperResearchStage.PARKED,
}
_PRIORITY_LEVEL_TO_SCORE: dict[PaperPriorityLevel, int] = {
    PaperPriorityLevel.LOW: 1,
    PaperPriorityLevel.NORMAL: 3,
    PaperPriorityLevel.HIGH: 4,
    PaperPriorityLevel.URGENT: 5,
}


class PaperProgressWorkbenchService:
    """Build read/update models for paper progress workbench workflows."""

    def __init__(self, session) -> None:
        self.paper_repository = PaperRepository(session)
        self.paper_service = PaperService(session)

    def list_progress_items(
        self,
        *,
        user_id: UUID | None = None,
        reading_status: PaperReadingStatus | None = None,
        research_stage: PaperResearchStage | None = None,
        priority: PaperPriorityLevel | None = None,
        keyword: str | None = None,
        has_next_action: bool | None = None,
        source_format: PaperImportSourceFormat | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaperProgressListResponse:
        items = self._filtered_items(
            user_id=user_id,
            reading_status=reading_status,
            research_stage=research_stage,
            priority=priority,
            keyword=keyword,
            has_next_action=has_next_action,
            source_format=source_format,
        )
        paged_items = items[offset : offset + limit]
        return PaperProgressListResponse(
            total_items=len(items),
            limit=limit,
            offset=offset,
            items=paged_items,
        )

    def get_progress_item(self, paper_id: UUID) -> PaperProgressItemRead:
        paper = self.paper_service.get_paper(paper_id)
        return self._build_progress_item(paper)

    def update_progress_item(
        self,
        paper_id: UUID,
        payload: PaperProgressUpdateRequest,
    ) -> PaperProgressItemRead:
        paper = self.paper_service.get_paper(paper_id)
        identifiers = _normalize_identifiers(paper.identifiers)
        progress_metadata = _extract_progress_metadata(identifiers)
        update_data = payload.model_dump(exclude_unset=True)

        if "reading_status" in update_data:
            _store_optional_enum(
                progress_metadata,
                key="reading_status",
                value=payload.reading_status,
            )
        if "user_note" in update_data:
            _store_optional_text(progress_metadata, key="user_note", value=payload.user_note)
        if "research_note" in update_data:
            _store_optional_text(
                progress_metadata,
                key="research_note",
                value=payload.research_note,
            )
        if "tags" in update_data:
            _store_optional_tags(progress_metadata, key="tags", value=payload.tags)

        if progress_metadata:
            identifiers[_PROGRESS_METADATA_KEY] = progress_metadata
        else:
            identifiers.pop(_PROGRESS_METADATA_KEY, None)

        patch = PaperProfileUpdate(
            identifiers=identifiers,
            last_touch_at=datetime.now(UTC),
        )
        if payload.research_stage is not None:
            patch.stage = payload.research_stage.value
        if payload.priority is not None:
            patch.priority = _priority_level_to_score(payload.priority)
        if payload.clear_next_action:
            patch.next_action = None
        elif "next_action" in update_data:
            patch.next_action = payload.next_action

        updated = self.paper_service.update_paper(paper_id, patch)
        return self._build_progress_item(updated)

    def build_summary(
        self,
        *,
        user_id: UUID | None = None,
        reading_status: PaperReadingStatus | None = None,
        research_stage: PaperResearchStage | None = None,
        priority: PaperPriorityLevel | None = None,
        keyword: str | None = None,
        has_next_action: bool | None = None,
        source_format: PaperImportSourceFormat | None = None,
    ) -> PaperProgressSummaryRead:
        items = self._filtered_items(
            user_id=user_id,
            reading_status=reading_status,
            research_stage=research_stage,
            priority=priority,
            keyword=keyword,
            has_next_action=has_next_action,
            source_format=source_format,
        )

        by_reading_status = {status.value: 0 for status in PaperReadingStatus}
        by_research_stage = {stage.value: 0 for stage in PaperResearchStage}
        by_priority = {level.value: 0 for level in PaperPriorityLevel}
        for item in items:
            by_reading_status[item.reading_status.value] += 1
            by_research_stage[item.research_stage.value] += 1
            by_priority[item.priority.value] += 1

        return PaperProgressSummaryRead(
            total_papers=len(items),
            unread_count=by_reading_status[PaperReadingStatus.UNREAD.value],
            reading_count=(
                by_reading_status[PaperReadingStatus.SKIMMING.value]
                + by_reading_status[PaperReadingStatus.READING.value]
            ),
            read_count=by_reading_status[PaperReadingStatus.READ.value],
            high_priority_count=by_priority[PaperPriorityLevel.HIGH.value],
            urgent_count=by_priority[PaperPriorityLevel.URGENT.value],
            with_next_action_count=sum(1 for item in items if bool(item.next_action)),
            by_reading_status=by_reading_status,
            by_research_stage=by_research_stage,
            by_priority=by_priority,
        )

    def get_progress_context_for_pulse(
        self,
        *,
        user_id: UUID | None = None,
        limit: int = 10,
    ) -> PaperProgressPulseContextRead:
        items = self._filtered_items(user_id=user_id)
        high_priority_papers = [item for item in items if item.priority in _ACTIVE_PRIORITIES][
            :limit
        ]
        papers_with_next_action = [item for item in items if bool(item.next_action)][:limit]
        active_review_papers = [
            item
            for item in items
            if item.reading_status in _ACTIVE_READING_STATUSES
            or item.research_stage == PaperResearchStage.REVIEWING
        ][:limit]
        metadata_attention_papers = [item for item in items if item.warnings][:limit]
        return PaperProgressPulseContextRead(
            generated_at=datetime.now(UTC),
            high_priority_papers=high_priority_papers,
            papers_with_next_action=papers_with_next_action,
            active_review_papers=active_review_papers,
            metadata_attention_papers=metadata_attention_papers,
            notes=[
                "该上下文只返回结构化论文进度信息，不生成实际 Research Pulse 内容。",
                (
                    "metadata_attention_papers 用于提示 DOI、年份、作者、"
                    "来源格式或下一步动作等缺失项。"
                ),
            ],
        )

    def _filtered_items(
        self,
        *,
        user_id: UUID | None = None,
        reading_status: PaperReadingStatus | None = None,
        research_stage: PaperResearchStage | None = None,
        priority: PaperPriorityLevel | None = None,
        keyword: str | None = None,
        has_next_action: bool | None = None,
        source_format: PaperImportSourceFormat | None = None,
    ) -> list[PaperProgressItemRead]:
        papers = self.paper_repository.list(user_id=user_id)
        items = [self._build_progress_item(paper) for paper in papers]
        if reading_status is not None:
            items = [item for item in items if item.reading_status == reading_status]
        if research_stage is not None:
            items = [item for item in items if item.research_stage == research_stage]
        if priority is not None:
            items = [item for item in items if item.priority == priority]
        if has_next_action is not None:
            items = [item for item in items if bool(item.next_action) is has_next_action]
        if source_format is not None:
            items = [item for item in items if item.source_format == source_format]
        if keyword:
            keyword_lower = keyword.strip().lower()
            if keyword_lower:
                items = [item for item in items if keyword_lower in _searchable_text(item)]
        return sorted(items, key=_progress_sort_key)

    def _build_progress_item(self, paper: PaperProfile) -> PaperProgressItemRead:
        identifiers = _normalize_identifiers(paper.identifiers)
        progress_metadata = _extract_progress_metadata(identifiers)
        authors = _coerce_string_list(
            progress_metadata.get("authors")
            or identifiers.get("authors")
            or identifiers.get("import_authors")
        )
        tags = _extract_tags(progress_metadata, identifiers)
        source_format = _extract_source_format(identifiers.get("import_source_format"))
        reading_status = _extract_reading_status(progress_metadata.get("reading_status"))
        research_stage, stage_warning = _extract_research_stage(paper.stage)
        priority = _score_to_priority_level(paper.priority)
        user_note = _coerce_optional_text(progress_metadata.get("user_note"))
        research_note = _coerce_optional_text(progress_metadata.get("research_note"))
        year = _extract_year(identifiers)
        doi = _coerce_optional_text(identifiers.get("doi"))
        url = next((item for item in paper.source_links if item), None)

        warnings: list[str] = []
        if stage_warning:
            warnings.append(stage_warning)
        if not authors:
            warnings.append("缺少作者信息，后续筛选和 Pulse 上下文会受限。")
        if year is None:
            warnings.append("缺少发表年份，建议在导入预览或后续整理中补全。")
        if not paper.venue:
            warnings.append("缺少期刊或会议信息，后续按来源筛选会受限。")
        if not doi:
            warnings.append("缺少 DOI，后续去重与引用追踪能力会受限。")
        if source_format is None:
            warnings.append("缺少导入来源格式标记，后续来源分析会受限。")
        if priority in _ACTIVE_PRIORITIES and not paper.next_action:
            warnings.append("高优先级论文尚未定义下一步动作。")
        if source_format == PaperImportSourceFormat.PDF_FOLDER and (
            not authors or year is None or not paper.venue
        ):
            warnings.append("PDF 文件夹占位导入的元数据仍不完整，建议尽快补全。")

        return PaperProgressItemRead(
            paper_id=paper.id,
            user_id=paper.user_id,
            title=paper.title,
            authors=authors,
            year=year,
            venue=paper.venue,
            doi=doi,
            url=url,
            source_format=source_format,
            reading_status=reading_status,
            research_stage=research_stage,
            priority=priority,
            priority_score=paper.priority,
            next_action=paper.next_action,
            user_note=user_note,
            research_note=research_note,
            tags=tags,
            imported_at=paper.created_at if source_format is not None else None,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
            last_touch_at=paper.last_touch_at,
            warnings=_dedupe_preserving_order(warnings),
        )


_ACTIVE_PRIORITIES = {PaperPriorityLevel.HIGH, PaperPriorityLevel.URGENT}
_ACTIVE_READING_STATUSES = {PaperReadingStatus.SKIMMING, PaperReadingStatus.READING}


def _normalize_identifiers(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _extract_progress_metadata(identifiers: dict[str, Any]) -> dict[str, Any]:
    raw = identifiers.get(_PROGRESS_METADATA_KEY)
    if isinstance(raw, dict):
        return dict(raw)
    legacy_keys = ("reading_status", "user_note", "research_note", "tags")
    extracted: dict[str, Any] = {}
    for key in legacy_keys:
        if key in identifiers:
            extracted[key] = identifiers[key]
    return extracted


def _extract_tags(progress_metadata: dict[str, Any], identifiers: dict[str, Any]) -> list[str]:
    if "tags" in progress_metadata:
        return _coerce_string_list(progress_metadata.get("tags"))
    return _coerce_string_list(identifiers.get("keywords") or identifiers.get("import_keywords"))


def _extract_reading_status(value: Any) -> PaperReadingStatus:
    if isinstance(value, PaperReadingStatus):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        for status in PaperReadingStatus:
            if status.value == cleaned:
                return status
    return PaperReadingStatus.UNREAD


def _extract_research_stage(raw_stage: str) -> tuple[PaperResearchStage, str | None]:
    cleaned = raw_stage.strip().lower()
    for stage in PaperResearchStage:
        if stage.value == cleaned:
            return stage, None
    aliased = _LEGACY_STAGE_ALIASES.get(cleaned)
    if aliased is not None:
        return aliased, f'历史 stage "{raw_stage}" 已映射为研究阶段 "{aliased.value}"。'
    return PaperResearchStage.TRIAGE, f'未识别的 stage "{raw_stage}" 已暂时归为 "triage"。'


def _score_to_priority_level(score: int) -> PaperPriorityLevel:
    if score >= 5:
        return PaperPriorityLevel.URGENT
    if score >= 4:
        return PaperPriorityLevel.HIGH
    if score <= 2:
        return PaperPriorityLevel.LOW
    return PaperPriorityLevel.NORMAL


def _priority_level_to_score(level: PaperPriorityLevel) -> int:
    return _PRIORITY_LEVEL_TO_SCORE[level]


def _extract_source_format(value: Any) -> PaperImportSourceFormat | None:
    if isinstance(value, PaperImportSourceFormat):
        return value
    if isinstance(value, str):
        cleaned = value.strip().lower()
        for source_format in PaperImportSourceFormat:
            if source_format.value == cleaned:
                return source_format
    return None


def _extract_year(identifiers: dict[str, Any]) -> int | None:
    candidates = [
        identifiers.get("year"),
        identifiers.get("import_year"),
    ]
    raw_source_payload = identifiers.get("import_raw_source_payload")
    if isinstance(raw_source_payload, dict):
        candidates.extend(
            [
                raw_source_payload.get("year"),
                raw_source_payload.get("PY"),
                raw_source_payload.get("Y1"),
            ]
        )
        issued = raw_source_payload.get("issued")
        if isinstance(issued, dict):
            date_parts = issued.get("date-parts")
            if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
                candidates.append(date_parts[0][0] if date_parts[0] else None)

    for candidate in candidates:
        year = _coerce_year(candidate)
        if year is not None:
            return year
    return None


def _coerce_year(value: Any) -> int | None:
    if isinstance(value, int):
        if 1000 <= value <= 3000:
            return value
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            year = int(stripped)
            if 1000 <= year <= 3000:
                return year
    return None


def _coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [segment.strip() for segment in value.replace("；", ";").split(";")]
        return [part for part in parts if part]
    if isinstance(value, (list, tuple, set)):
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            stripped = item.strip()
            if stripped:
                cleaned.append(stripped)
        return cleaned
    return []


def _coerce_optional_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _store_optional_enum(
    metadata: dict[str, Any],
    *,
    key: str,
    value: PaperReadingStatus | None,
) -> None:
    if value is None:
        metadata.pop(key, None)
        return
    metadata[key] = value.value


def _store_optional_text(metadata: dict[str, Any], *, key: str, value: str | None) -> None:
    if value is None:
        metadata.pop(key, None)
        return
    metadata[key] = value


def _store_optional_tags(metadata: dict[str, Any], *, key: str, value: list[str] | None) -> None:
    if value is None:
        metadata.pop(key, None)
        return
    metadata[key] = list(value)


def _searchable_text(item: PaperProgressItemRead) -> str:
    haystack = [
        item.title,
        " ".join(item.authors),
        item.venue or "",
        item.doi or "",
        item.url or "",
        " ".join(item.tags),
        item.next_action or "",
        item.user_note or "",
        item.research_note or "",
        item.reading_status.value,
        item.research_stage.value,
        item.priority.value,
        item.source_format.value if item.source_format is not None else "",
    ]
    return " ".join(segment.lower() for segment in haystack if segment)


def _progress_sort_key(item: PaperProgressItemRead) -> tuple[object, ...]:
    updated_reference = item.last_touch_at or item.updated_at or item.created_at
    return (
        -item.priority_score,
        -updated_reference.timestamp(),
        item.title.lower(),
        str(item.paper_id),
    )


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
