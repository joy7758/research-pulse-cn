"""Deterministic related-paper candidate builder from normalized retrieval records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.db.models import ExternalRetrievedRecord, utcnow
from research_pulse_cn.domain.enums import ExternalRetrievalScope
from research_pulse_cn.repositories.external_retrieval import ExternalRetrievedRecordRepository


@dataclass(slots=True)
class RelatedPaperDecision:
    external_reference_key: str
    external_record_id: UUID
    external_run_id: UUID
    external_plan_id: UUID
    source_kind: str
    retrieval_scope: str
    external_id: str
    external_url: str | None
    doi: str | None
    title: str
    publication_year: int | None
    publication_date: str | None
    source_title: str | None
    authors_summary: str | None
    matched_reason_codes: list[str]
    linked_paper_id: UUID | None
    linked_paper_title: str | None
    run_finished_at: datetime | None
    result_created_at: datetime
    top_reason_codes: list[str]
    source_timestamp: datetime
    summary: str
    why_now: str


class RelatedPaperCandidateBuilder:
    """Build deterministic pulse inputs from persisted related-paper retrieval results."""

    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        now_provider=None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.now_provider = now_provider or utcnow
        self.record_repository = ExternalRetrievedRecordRepository(session)

    def build(
        self,
        *,
        user_id: UUID,
        lookback_days: int,
        max_candidates: int,
        reference: datetime | None = None,
    ) -> list[RelatedPaperDecision]:
        now = _coerce_utc(reference or self.now_provider())
        not_before = now - timedelta(days=max(1, lookback_days))
        records = self.record_repository.list_recent_completed_records(
            user_id=user_id,
            retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
            not_before=not_before,
        )
        by_reference_key: dict[str, ExternalRetrievedRecord] = {}
        for record in records:
            reference_key = canonical_external_reference_key(record)
            current = by_reference_key.get(reference_key)
            if current is None or _record_preference_key(record) > _record_preference_key(current):
                by_reference_key[reference_key] = record
        decisions = [
            self._to_decision(
                reference_key=reference_key,
                record=record,
            )
            for reference_key, record in by_reference_key.items()
        ]
        decisions.sort(key=_decision_sort_key)
        return decisions[: max(1, max_candidates)]

    def _to_decision(
        self,
        *,
        reference_key: str,
        record: ExternalRetrievedRecord,
    ) -> RelatedPaperDecision:
        linked_paper = record.plan.paper
        linked_paper_id = linked_paper.id if linked_paper is not None else record.plan.paper_id
        linked_paper_title = linked_paper.title if linked_paper is not None else None
        matched_reason_codes = _sorted_unique_strings(record.matched_reason_codes)
        top_reason_codes = _top_reason_codes(
            matched_reason_codes=matched_reason_codes,
            linked_paper_id=linked_paper_id,
            doi=record.doi,
        )
        authors_summary = _authors_summary(record.authors)
        run_finished_at = _coerce_utc(record.run.finished_at) if record.run.finished_at else None
        result_created_at = _coerce_utc(record.created_at)
        source_timestamp = run_finished_at or result_created_at
        title = _compact_text(record.title, limit=255) or "Untitled"
        summary = _build_summary(
            title=title,
            source_title=_compact_text(record.source_title, limit=255),
            publication_year=record.publication_year,
            authors_summary=authors_summary,
        )
        why_now = _build_why_now(
            linked_paper_title=linked_paper_title,
            top_reason_codes=top_reason_codes,
        )
        return RelatedPaperDecision(
            external_reference_key=reference_key,
            external_record_id=record.id,
            external_run_id=record.run_id,
            external_plan_id=record.plan_id,
            source_kind=record.source_kind.value,
            retrieval_scope=record.retrieval_scope.value,
            external_id=record.external_id,
            external_url=_compact_text(record.external_url, limit=500),
            doi=_normalize_doi(record.doi),
            title=title,
            publication_year=record.publication_year,
            publication_date=_compact_text(record.publication_date, limit=64),
            source_title=_compact_text(record.source_title, limit=255),
            authors_summary=authors_summary,
            matched_reason_codes=matched_reason_codes,
            linked_paper_id=linked_paper_id,
            linked_paper_title=linked_paper_title,
            run_finished_at=run_finished_at,
            result_created_at=result_created_at,
            top_reason_codes=top_reason_codes,
            source_timestamp=source_timestamp,
            summary=summary,
            why_now=why_now,
        )


def canonical_external_reference_key(record: ExternalRetrievedRecord) -> str:
    """Derive a canonical scholarly identity across sources and runs."""
    doi = _normalize_doi(record.doi)
    if doi:
        return f"doi:{doi}"
    external_id = _compact_text(record.external_id, limit=500)
    if external_id:
        return f"{record.source_kind.value}:{external_id.lower()}"
    normalized_title = _normalized_title_fallback(record.title)
    if normalized_title:
        return f"title:{normalized_title}"
    return f"record:{record.id}"


def _record_preference_key(record: ExternalRetrievedRecord) -> tuple[Any, ...]:
    run_finished_at = _coerce_utc(record.run.finished_at) if record.run.finished_at else None
    created_at = _coerce_utc(record.created_at)
    publication_year = record.publication_year or 0
    return (
        int((run_finished_at or created_at).timestamp()),
        int(created_at.timestamp()),
        publication_year,
        record.sort_order * -1,
        record.source_kind.value,
        _compact_text(record.title, limit=500) or "",
        str(record.id),
    )


def _decision_sort_key(decision: RelatedPaperDecision) -> tuple[Any, ...]:
    publication_sort = _publication_sort_key(decision.publication_date, decision.publication_year)
    return (
        -int(decision.linked_paper_id is not None),
        -len(decision.top_reason_codes),
        -int(decision.doi is not None),
        -int(decision.source_timestamp.timestamp()),
        publication_sort,
        decision.title.lower(),
        decision.external_reference_key,
    )


def _top_reason_codes(
    *,
    matched_reason_codes: list[str],
    linked_paper_id: UUID | None,
    doi: str | None,
) -> list[str]:
    weighted_reasons: dict[str, int] = {
        code: 20 - index for index, code in enumerate(matched_reason_codes[:5])
    }
    if linked_paper_id is not None:
        weighted_reasons["linked_paper_context"] = 25
    if doi:
        weighted_reasons["has_doi"] = 10
    return [
        code
        for code, _weight in sorted(
            weighted_reasons.items(),
            key=lambda item: (-item[1], item[0]),
        )[:3]
    ]


def _build_summary(
    *,
    title: str,
    source_title: str | None,
    publication_year: int | None,
    authors_summary: str | None,
) -> str:
    if source_title and publication_year:
        summary = f"{title} appeared in {source_title} ({publication_year})."
    elif source_title:
        summary = f"{title} appeared in {source_title}."
    elif publication_year:
        summary = f"{title} was published in {publication_year}."
    else:
        summary = title
    if authors_summary:
        summary += f" Authors: {authors_summary}."
    return summary


def _build_why_now(
    *,
    linked_paper_title: str | None,
    top_reason_codes: list[str],
) -> str:
    if linked_paper_title:
        why_now = (
            f"This completed related-paper retrieval for {linked_paper_title} surfaced a "
            "potentially relevant scholarly result."
        )
    else:
        why_now = (
            "This completed related-paper retrieval surfaced a potentially relevant "
            "scholarly result from your current watch context."
        )
    if top_reason_codes:
        why_now += f" Match reasons: {', '.join(top_reason_codes)}."
    return why_now


def _authors_summary(authors: list[dict[str, Any]] | None) -> str | None:
    if not authors:
        return None
    names = [
        _compact_text(author.get("name"), limit=255)
        for author in authors
        if isinstance(author, dict) and _compact_text(author.get("name"), limit=255)
    ]
    unique_names = _sorted_unique_strings(names)
    if not unique_names:
        return None
    return ", ".join(unique_names[:3])


def _normalize_doi(value: str | None) -> str | None:
    text = _compact_text(value, limit=255)
    if not text:
        return None
    text = text.strip().lower()
    text = re.sub(r"^https?://(dx\\.)?doi\\.org/", "", text)
    return text or None


def _normalized_title_fallback(value: str | None) -> str:
    text = _compact_text(value, limit=500)
    if not text:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _publication_sort_key(
    publication_date: str | None, publication_year: int | None
) -> tuple[Any, ...]:
    return (
        -int(publication_year or 0),
        publication_date or "",
    )


def _sorted_unique_strings(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned = {value.strip() for value in values if isinstance(value, str) and value.strip()}
    return sorted(cleaned)


def _compact_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    compacted = re.sub(r"\s+", " ", text)
    return compacted[:limit]


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
