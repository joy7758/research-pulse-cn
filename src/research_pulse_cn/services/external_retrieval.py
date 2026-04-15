"""Deterministic external retrieval planning and execution services."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html import unescape
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID
from xml.etree import ElementTree

import httpx
from sqlalchemy.orm import Session

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import MetricsRegistry, get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    ExternalRetrievalPlan,
    ExternalRetrievalRun,
    ExternalRetrievedRecord,
    ResearchWatchProfile,
    WorkActivityEvent,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ExternalRetrievalMode,
    ExternalRetrievalPlanStatus,
    ExternalRetrievalRunStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
    WorkActivitySource,
)
from research_pulse_cn.repositories.external_retrieval import (
    ExternalRetrievalPlanRepository,
    ExternalRetrievalRunRepository,
    ExternalRetrievedRecordRepository,
)
from research_pulse_cn.repositories.research_watch import ResearchWatchProfileRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.repositories.work_activity import WorkActivityRepository
from research_pulse_cn.schemas.pulse_input import (
    EffectiveRetrievalSeedsRead,
    ExternalRetrievalExecuteResponse,
    ExternalRetrievalExecutionSummaryRead,
    ExternalRetrievalInputPreviewResponse,
    ExternalRetrievalPlanCompactRead,
    ExternalRetrievalPlanningCompactRead,
    ExternalRetrievalPlanPreviewRead,
    ExternalRetrievalProviderSourceStatusRead,
    ExternalRetrievalProviderStatusRead,
    ExternalRetrievalRunCompactRead,
    ExternalRetrievalRunDetailRead,
    WorkActivitySummaryRead,
    WorkActivityTouchedPaperRead,
)
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CROSSREF_WORKS_URL = "https://api.crossref.org/works"
ARXIV_QUERY_URL = "https://export.arxiv.org/api/query"
ARXIV_ATOM_NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def create_external_retrieval_http_client(settings: Settings) -> httpx.Client:
    """Create an HTTP client with conservative timeout defaults."""
    timeout = httpx.Timeout(
        connect=settings.external_retrieval_http_connect_timeout_seconds,
        read=settings.external_retrieval_http_read_timeout_seconds,
        write=settings.external_retrieval_http_read_timeout_seconds,
        pool=settings.external_retrieval_http_read_timeout_seconds,
    )
    return httpx.Client(timeout=timeout)


@dataclass(slots=True)
class EffectiveRetrievalSeeds:
    topics: list[str]
    keywords: list[str]
    venues: list[str]
    authors_of_interest: list[str]
    touched_paper_titles: list[str]

    def to_read(self) -> EffectiveRetrievalSeedsRead:
        return EffectiveRetrievalSeedsRead(
            topics=self.topics,
            keywords=self.keywords,
            venues=self.venues,
            authors_of_interest=self.authors_of_interest,
            touched_paper_titles=self.touched_paper_titles,
        )

    def to_effective_inputs(self) -> dict[str, Any]:
        return {
            "topics": list(self.topics),
            "keywords": list(self.keywords),
            "venues": list(self.venues),
            "authors_of_interest": list(self.authors_of_interest),
            "touched_paper_titles": list(self.touched_paper_titles),
        }


@dataclass(slots=True)
class ExternalRetrievalPlanDraft:
    source_kind: ExternalRetrievalSourceKind
    retrieval_scope: ExternalRetrievalScope
    watch_profile_id: UUID | None
    paper_id: UUID | None
    plan_label: str
    query_text: str
    query_payload: dict[str, Any]
    effective_inputs: dict[str, Any]
    reason_codes: list[str]
    plan_hash: str

    def to_preview_read(self) -> ExternalRetrievalPlanPreviewRead:
        return ExternalRetrievalPlanPreviewRead(
            source_kind=self.source_kind,
            retrieval_scope=self.retrieval_scope,
            watch_profile_id=self.watch_profile_id,
            paper_id=self.paper_id,
            plan_label=self.plan_label,
            query_text=self.query_text,
            query_payload=self.query_payload,
            effective_inputs=self.effective_inputs,
            reason_codes=self.reason_codes,
            plan_hash=self.plan_hash,
        )

    def to_compact_read(self) -> ExternalRetrievalPlanCompactRead:
        return ExternalRetrievalPlanCompactRead(
            source_kind=self.source_kind,
            retrieval_scope=self.retrieval_scope,
            plan_label=self.plan_label,
            query_text=self.query_text,
            reason_codes=self.reason_codes,
        )


@dataclass(slots=True)
class RetrievalPlanningContext:
    user_id: UUID
    seeds: EffectiveRetrievalSeeds
    enabled_sources: list[ExternalRetrievalSourceKind]
    watch_profile_id: UUID | None
    paper_id: UUID | None
    max_keywords_per_plan: int
    max_topics_per_plan: int


@dataclass(slots=True)
class NormalizedRetrievedRecordDraft:
    external_id: str
    external_url: str | None
    doi: str | None
    title: str
    abstract_snippet: str | None
    publication_year: int | None
    publication_date: str | None
    source_title: str | None
    authors: list[dict[str, Any]] | None
    matched_reason_codes: list[str] | None
    raw_payload: dict[str, Any]
    sort_order: int


@dataclass(slots=True)
class ExternalRetrievalExecutionResult:
    request_url: str | None
    request_payload: dict[str, Any] | None
    response_summary: dict[str, Any] | None
    raw_result_count: int
    records: list[NormalizedRetrievedRecordDraft]


@dataclass(slots=True)
class ExternalRetrievalExecutionOutcome:
    run: ExternalRetrievalRun
    results: list[ExternalRetrievedRecord]
    deduped: bool
    notes: list[str]

    def to_response(self, *, mode: ExternalRetrievalMode) -> ExternalRetrievalExecuteResponse:
        return ExternalRetrievalExecuteResponse(
            mode=mode,
            deduped=self.deduped,
            run=self.run,
            results=self.results,
            notes=self.notes,
        )


class SourcePlanBuilder(ABC):
    """Source-specific planning boundary for future retrieval execution."""

    source_kind: ExternalRetrievalSourceKind

    @abstractmethod
    def build_plans(self, context: RetrievalPlanningContext) -> list[ExternalRetrievalPlanDraft]:
        """Build deterministic plans for a single source."""

    def _draft(
        self,
        *,
        context: RetrievalPlanningContext,
        retrieval_scope: ExternalRetrievalScope,
        plan_label: str,
        query_text: str,
        query_payload: dict[str, Any],
        reason_codes: list[str],
    ) -> ExternalRetrievalPlanDraft:
        normalized_payload = _normalize_json(query_payload)
        effective_inputs = {
            **context.seeds.to_effective_inputs(),
            "enabled_sources": [item.value for item in context.enabled_sources],
            "source_kind": self.source_kind.value,
            "retrieval_scope": retrieval_scope.value,
        }
        plan_hash = _stable_hash(
            {
                "user_id": str(context.user_id),
                "source_kind": self.source_kind.value,
                "retrieval_scope": retrieval_scope.value,
                "watch_profile_id": str(context.watch_profile_id)
                if context.watch_profile_id
                else None,
                "paper_id": str(context.paper_id) if context.paper_id else None,
                "query_text": query_text,
                "query_payload": normalized_payload,
                "effective_inputs": effective_inputs,
            }
        )
        return ExternalRetrievalPlanDraft(
            source_kind=self.source_kind,
            retrieval_scope=retrieval_scope,
            watch_profile_id=context.watch_profile_id,
            paper_id=context.paper_id,
            plan_label=plan_label,
            query_text=query_text,
            query_payload=normalized_payload,
            effective_inputs=effective_inputs,
            reason_codes=_sorted_terms(reason_codes),
            plan_hash=plan_hash,
        )


class OpenAlexPlanBuilder(SourcePlanBuilder):
    source_kind = ExternalRetrievalSourceKind.OPENALEX

    def build_plans(self, context: RetrievalPlanningContext) -> list[ExternalRetrievalPlanDraft]:
        plans: list[ExternalRetrievalPlanDraft] = []
        keywords = _limited_terms(
            [*context.seeds.keywords, *context.seeds.touched_paper_titles],
            context.max_keywords_per_plan,
        )
        topics = _limited_terms(context.seeds.topics, context.max_topics_per_plan)
        authors = _limited_terms(context.seeds.authors_of_interest, context.max_keywords_per_plan)
        venues = _limited_terms(context.seeds.venues, context.max_keywords_per_plan)
        touched_titles = _limited_terms(
            context.seeds.touched_paper_titles,
            context.max_keywords_per_plan,
        )

        if keywords or topics or touched_titles:
            query_payload = {
                "keywords": keywords,
                "topics": topics,
                "touched_paper_titles": touched_titles,
            }
            reason_codes = _reason_codes(
                keywords=bool(keywords),
                topics=bool(topics),
                touched_titles=bool(touched_titles),
            )
            plans.append(
                self._draft(
                    context=context,
                    retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
                    plan_label="OpenAlex related papers",
                    query_text=_build_query_text(
                        "keyword/topic watch",
                        keywords=keywords,
                        topics=topics,
                        touched_paper_titles=touched_titles,
                    ),
                    query_payload=query_payload,
                    reason_codes=reason_codes,
                )
            )
        if venues:
            plans.append(
                self._draft(
                    context=context,
                    retrieval_scope=ExternalRetrievalScope.VENUE_UPDATE,
                    plan_label=f"OpenAlex venue updates: {venues[0]}",
                    query_text=_build_query_text("venue watch", venues=venues),
                    query_payload={"venues": venues},
                    reason_codes=_reason_codes(venues=True),
                )
            )
        if authors:
            plans.append(
                self._draft(
                    context=context,
                    retrieval_scope=ExternalRetrievalScope.AUTHOR_WATCH,
                    plan_label=f"OpenAlex author watch: {authors[0]}",
                    query_text=_build_query_text("author watch", authors_of_interest=authors),
                    query_payload={"authors_of_interest": authors},
                    reason_codes=_reason_codes(authors=True),
                )
            )
        return plans


class CrossrefPlanBuilder(SourcePlanBuilder):
    source_kind = ExternalRetrievalSourceKind.CROSSREF

    def build_plans(self, context: RetrievalPlanningContext) -> list[ExternalRetrievalPlanDraft]:
        plans: list[ExternalRetrievalPlanDraft] = []
        keywords = _limited_terms(
            [*context.seeds.keywords, *context.seeds.touched_paper_titles],
            context.max_keywords_per_plan,
        )
        venues = _limited_terms(context.seeds.venues, context.max_keywords_per_plan)
        touched_titles = _limited_terms(
            context.seeds.touched_paper_titles,
            context.max_keywords_per_plan,
        )
        if keywords or touched_titles:
            plans.append(
                self._draft(
                    context=context,
                    retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
                    plan_label="Crossref related papers",
                    query_text=_build_query_text(
                        "title/keyword watch",
                        keywords=keywords,
                        touched_paper_titles=touched_titles,
                    ),
                    query_payload={
                        "keywords": keywords,
                        "touched_paper_titles": touched_titles,
                        "venues": venues,
                    },
                    reason_codes=_reason_codes(
                        keywords=bool(keywords),
                        touched_titles=bool(touched_titles),
                    ),
                )
            )
        if venues:
            plans.append(
                self._draft(
                    context=context,
                    retrieval_scope=ExternalRetrievalScope.VENUE_UPDATE,
                    plan_label=f"Crossref venue updates: {venues[0]}",
                    query_text=_build_query_text(
                        "venue/title watch",
                        venues=venues,
                        keywords=keywords,
                    ),
                    query_payload={"venues": venues, "keywords": keywords},
                    reason_codes=_reason_codes(venues=True, keywords=bool(keywords)),
                )
            )
        return plans


class ArxivPlanBuilder(SourcePlanBuilder):
    source_kind = ExternalRetrievalSourceKind.ARXIV

    def build_plans(self, context: RetrievalPlanningContext) -> list[ExternalRetrievalPlanDraft]:
        keywords = _limited_terms(context.seeds.keywords, context.max_keywords_per_plan)
        topics = _limited_terms(context.seeds.topics, context.max_topics_per_plan)
        if not keywords and not topics:
            return []
        return [
            self._draft(
                context=context,
                retrieval_scope=ExternalRetrievalScope.RELATED_PAPER,
                plan_label="arXiv related papers",
                query_text=_build_query_text(
                    "topic/keyword watch",
                    keywords=keywords,
                    topics=topics,
                ),
                query_payload={"keywords": keywords, "topics": topics},
                reason_codes=_reason_codes(keywords=bool(keywords), topics=bool(topics)),
            )
        ]


class ExternalRetrievalExecutor(ABC):
    """Official-source execution boundary for a single retrieval provider."""

    source_kind: ExternalRetrievalSourceKind

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def execute(
        self,
        *,
        plan: ExternalRetrievalPlan,
        http_client: httpx.Client,
    ) -> ExternalRetrievalExecutionResult:
        """Fetch and normalize source results for one plan."""

    def _max_results(self) -> int:
        return max(1, self.settings.external_retrieval_max_results_per_plan)


class OpenAlexExecutor(ExternalRetrievalExecutor):
    source_kind = ExternalRetrievalSourceKind.OPENALEX

    def execute(
        self,
        *,
        plan: ExternalRetrievalPlan,
        http_client: httpx.Client,
    ) -> ExternalRetrievalExecutionResult:
        search_terms = _joined_terms(
            _payload_terms(plan.query_payload, "keywords"),
            _payload_terms(plan.query_payload, "topics"),
            _payload_terms(plan.query_payload, "touched_paper_titles"),
            _payload_terms(plan.query_payload, "venues"),
            _payload_terms(plan.query_payload, "authors_of_interest"),
        )
        if not search_terms:
            search_terms = _compact_text(plan.query_text, limit=300) or "scholarly retrieval"
        params: dict[str, Any] = {
            "search": search_terms,
            "per-page": self._max_results(),
        }
        if self.settings.external_retrieval_openalex_api_key:
            params["api_key"] = self.settings.external_retrieval_openalex_api_key
        response = http_client.get(OPENALEX_WORKS_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        items = list(payload.get("results") or [])
        records = [
            self._normalize_item(item=item, sort_order=index, reason_codes=plan.reason_codes)
            for index, item in enumerate(items, start=1)
        ]
        return ExternalRetrievalExecutionResult(
            request_url=_sanitize_url(str(response.request.url), redacted_keys={"api_key"}),
            request_payload={
                "params": _sanitize_mapping(params, redacted_keys={"api_key"}),
            },
            response_summary={
                "status_code": response.status_code,
                "raw_result_count": len(items),
                "meta_count": payload.get("meta", {}).get("count"),
            },
            raw_result_count=len(items),
            records=records,
        )

    def _normalize_item(
        self,
        *,
        item: dict[str, Any],
        sort_order: int,
        reason_codes: list[str],
    ) -> NormalizedRetrievedRecordDraft:
        openalex_id = str(item.get("id") or item.get("doi") or item.get("display_name") or "")
        title = _compact_text(item.get("display_name"), limit=500) or openalex_id
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        authorships = list(item.get("authorships") or [])
        abstract = _compact_text(
            _openalex_abstract_from_inverted_index(item.get("abstract_inverted_index")),
            limit=700,
        )
        authors = [
            {
                "name": _compact_text(
                    (authoring.get("author") or {}).get("display_name"), limit=255
                ),
                "position": authoring.get("author_position"),
            }
            for authoring in authorships
            if _compact_text((authoring.get("author") or {}).get("display_name"), limit=255)
        ] or None
        return NormalizedRetrievedRecordDraft(
            external_id=openalex_id,
            external_url=_compact_text(
                primary_location.get("landing_page_url") or item.get("id"),
                limit=1000,
            ),
            doi=_normalize_doi(item.get("doi")),
            title=title,
            abstract_snippet=abstract,
            publication_year=_coerce_int(item.get("publication_year")),
            publication_date=_compact_text(item.get("publication_date"), limit=64),
            source_title=_compact_text(source.get("display_name"), limit=500),
            authors=authors,
            matched_reason_codes=list(reason_codes) or None,
            raw_payload=_normalize_json(item),
            sort_order=sort_order,
        )


class CrossrefExecutor(ExternalRetrievalExecutor):
    source_kind = ExternalRetrievalSourceKind.CROSSREF

    def execute(
        self,
        *,
        plan: ExternalRetrievalPlan,
        http_client: httpx.Client,
    ) -> ExternalRetrievalExecutionResult:
        bibliographic_query = _joined_terms(
            _payload_terms(plan.query_payload, "keywords"),
            _payload_terms(plan.query_payload, "touched_paper_titles"),
            _payload_terms(plan.query_payload, "venues"),
        )
        if not bibliographic_query:
            bibliographic_query = _compact_text(plan.query_text, limit=300) or "scholarly retrieval"
        params: dict[str, Any] = {
            "query.bibliographic": bibliographic_query,
            "rows": self._max_results(),
        }
        if self.settings.external_retrieval_crossref_mailto:
            params["mailto"] = self.settings.external_retrieval_crossref_mailto
        headers = self._build_headers()
        response = http_client.get(CROSSREF_WORKS_URL, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        message = payload.get("message") or {}
        items = list(message.get("items") or [])
        records = [
            self._normalize_item(item=item, sort_order=index, reason_codes=plan.reason_codes)
            for index, item in enumerate(items, start=1)
        ]
        return ExternalRetrievalExecutionResult(
            request_url=_sanitize_url(str(response.request.url), redacted_keys={"mailto"}),
            request_payload={
                "params": _sanitize_mapping(params, redacted_keys={"mailto"}),
                "headers": {"has_user_agent": bool(headers.get("User-Agent"))},
            },
            response_summary={
                "status_code": response.status_code,
                "raw_result_count": len(items),
                "message_status": payload.get("status"),
            },
            raw_result_count=len(items),
            records=records,
        )

    def _build_headers(self) -> dict[str, str]:
        if not self.settings.external_retrieval_crossref_user_agent_app_name:
            return {}
        app_name = self.settings.external_retrieval_crossref_user_agent_app_name.strip()
        if not app_name:
            return {}
        mailto = (self.settings.external_retrieval_crossref_mailto or "").strip()
        if mailto:
            return {"User-Agent": f"{app_name} (mailto:{mailto})"}
        return {"User-Agent": app_name}

    def _normalize_item(
        self,
        *,
        item: dict[str, Any],
        sort_order: int,
        reason_codes: list[str],
    ) -> NormalizedRetrievedRecordDraft:
        title = _compact_text(_first_string(item.get("title")), limit=500) or "Untitled"
        abstract = _compact_text(_strip_markup(item.get("abstract")), limit=700)
        publication_date = _crossref_publication_date(item)
        publication_year = _publication_year_from_date(publication_date)
        authors = [
            {
                "name": _compact_text(
                    " ".join(part for part in [author.get("given"), author.get("family")] if part),
                    limit=255,
                )
                or _compact_text(author.get("name"), limit=255),
            }
            for author in list(item.get("author") or [])
            if _compact_text(
                " ".join(part for part in [author.get("given"), author.get("family")] if part),
                limit=255,
            )
            or _compact_text(author.get("name"), limit=255)
        ] or None
        external_id = _compact_text(item.get("DOI") or item.get("URL") or title, limit=500) or title
        return NormalizedRetrievedRecordDraft(
            external_id=external_id,
            external_url=_compact_text(item.get("URL"), limit=1000),
            doi=_normalize_doi(item.get("DOI")),
            title=title,
            abstract_snippet=abstract,
            publication_year=publication_year,
            publication_date=publication_date,
            source_title=_compact_text(_first_string(item.get("container-title")), limit=500),
            authors=authors,
            matched_reason_codes=list(reason_codes) or None,
            raw_payload=_normalize_json(item),
            sort_order=sort_order,
        )


class ArxivExecutor(ExternalRetrievalExecutor):
    source_kind = ExternalRetrievalSourceKind.ARXIV

    def execute(
        self,
        *,
        plan: ExternalRetrievalPlan,
        http_client: httpx.Client,
    ) -> ExternalRetrievalExecutionResult:
        search_query = self._build_search_query(plan)
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": self._max_results(),
        }
        response = http_client.get(ARXIV_QUERY_URL, params=params)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        entries = root.findall("atom:entry", ARXIV_ATOM_NAMESPACE)
        records = [
            self._normalize_entry(entry=entry, sort_order=index, reason_codes=plan.reason_codes)
            for index, entry in enumerate(entries, start=1)
        ]
        return ExternalRetrievalExecutionResult(
            request_url=_sanitize_url(str(response.request.url)),
            request_payload={"params": params},
            response_summary={
                "status_code": response.status_code,
                "raw_result_count": len(entries),
            },
            raw_result_count=len(entries),
            records=records,
        )

    def _build_search_query(self, plan: ExternalRetrievalPlan) -> str:
        terms = _payload_terms(plan.query_payload, "keywords") + _payload_terms(
            plan.query_payload,
            "topics",
        )
        normalized_terms = _limited_terms(terms, self._max_results())
        if not normalized_terms:
            query_text = _compact_text(plan.query_text, limit=200) or "scholarly retrieval"
            normalized_terms = [query_text]
        return " OR ".join(f'all:"{_escape_arxiv_term(term)}"' for term in normalized_terms)

    def _normalize_entry(
        self,
        *,
        entry: ElementTree.Element,
        sort_order: int,
        reason_codes: list[str],
    ) -> NormalizedRetrievedRecordDraft:
        entry_id = _xml_text(entry.find("atom:id", ARXIV_ATOM_NAMESPACE))
        title = _compact_text(_xml_text(entry.find("atom:title", ARXIV_ATOM_NAMESPACE)), limit=500)
        summary = _compact_text(
            _xml_text(entry.find("atom:summary", ARXIV_ATOM_NAMESPACE)), limit=700
        )
        published = _compact_text(
            _xml_text(entry.find("atom:published", ARXIV_ATOM_NAMESPACE)), limit=64
        )
        doi = _normalize_doi(_xml_text(entry.find("arxiv:doi", ARXIV_ATOM_NAMESPACE)))
        source_title = _compact_text(
            _xml_text(entry.find("arxiv:journal_ref", ARXIV_ATOM_NAMESPACE)) or "arXiv",
            limit=500,
        )
        authors = [
            {
                "name": _compact_text(
                    _xml_text(author.find("atom:name", ARXIV_ATOM_NAMESPACE)), limit=255
                )
            }
            for author in entry.findall("atom:author", ARXIV_ATOM_NAMESPACE)
            if _compact_text(_xml_text(author.find("atom:name", ARXIV_ATOM_NAMESPACE)), limit=255)
        ] or None
        payload = {
            "id": entry_id,
            "title": title,
            "summary": summary,
            "published": published,
            "updated": _xml_text(entry.find("atom:updated", ARXIV_ATOM_NAMESPACE)),
            "doi": doi,
            "journal_ref": _xml_text(entry.find("arxiv:journal_ref", ARXIV_ATOM_NAMESPACE)),
            "primary_category": (
                entry.find("arxiv:primary_category", ARXIV_ATOM_NAMESPACE).attrib.get("term")
                if entry.find("arxiv:primary_category", ARXIV_ATOM_NAMESPACE) is not None
                else None
            ),
            "authors": authors,
        }
        return NormalizedRetrievedRecordDraft(
            external_id=entry_id or title or f"arxiv-{sort_order}",
            external_url=entry_id,
            doi=doi,
            title=title or "Untitled",
            abstract_snippet=summary,
            publication_year=_publication_year_from_date(published),
            publication_date=published,
            source_title=source_title,
            authors=authors,
            matched_reason_codes=list(reason_codes) or None,
            raw_payload=_normalize_json(payload),
            sort_order=sort_order,
        )


class ExternalRetrievalPlanner:
    """Coordinate deterministic plan generation across enabled sources."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.builders: dict[ExternalRetrievalSourceKind, SourcePlanBuilder] = {
            ExternalRetrievalSourceKind.OPENALEX: OpenAlexPlanBuilder(),
            ExternalRetrievalSourceKind.CROSSREF: CrossrefPlanBuilder(),
            ExternalRetrievalSourceKind.ARXIV: ArxivPlanBuilder(),
        }

    def build_plans(
        self,
        *,
        user_id: UUID,
        seeds: EffectiveRetrievalSeeds,
        enabled_sources: list[ExternalRetrievalSourceKind],
        watch_profile_id: UUID | None,
        paper_id: UUID | None,
    ) -> list[ExternalRetrievalPlanDraft]:
        context = RetrievalPlanningContext(
            user_id=user_id,
            seeds=seeds,
            enabled_sources=enabled_sources,
            watch_profile_id=watch_profile_id,
            paper_id=paper_id,
            max_keywords_per_plan=max(1, self.settings.external_retrieval_max_keywords_per_plan),
            max_topics_per_plan=max(1, self.settings.external_retrieval_max_topics_per_plan),
        )
        plans: list[ExternalRetrievalPlanDraft] = []
        for source_kind in enabled_sources:
            builder = self.builders.get(source_kind)
            if builder is None:
                continue
            plans.extend(builder.build_plans(context))
        plans.sort(
            key=lambda item: (
                enabled_sources.index(item.source_kind),
                item.retrieval_scope.value,
                item.plan_label.lower(),
                item.plan_hash,
            )
        )
        return plans[: max(0, self.settings.external_retrieval_max_plans_per_user)]


class ExternalRetrievalService:
    """Preview, plan, execute, and inspect deterministic external retrieval flows."""

    def __init__(
        self,
        session: Session,
        *,
        settings: Settings | None = None,
        metrics: MetricsRegistry | None = None,
        http_client_factory=None,
        now_provider=None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.metrics = metrics or get_metrics()
        self.http_client_factory = http_client_factory or create_external_retrieval_http_client
        self.now_provider = now_provider or utcnow
        self.plan_repository = ExternalRetrievalPlanRepository(session)
        self.run_repository = ExternalRetrievalRunRepository(session)
        self.record_repository = ExternalRetrievedRecordRepository(session)
        self.user_repository = UserRepository(session)
        self.watch_repository = ResearchWatchProfileRepository(session)
        self.work_activity_repository = WorkActivityRepository(session)
        self.planner = ExternalRetrievalPlanner(self.settings)
        self.executors: dict[ExternalRetrievalSourceKind, ExternalRetrievalExecutor] = {
            ExternalRetrievalSourceKind.OPENALEX: OpenAlexExecutor(self.settings),
            ExternalRetrievalSourceKind.CROSSREF: CrossrefExecutor(self.settings),
            ExternalRetrievalSourceKind.ARXIV: ArxivExecutor(self.settings),
        }

    def preview_input(self, *, user_id: UUID) -> ExternalRetrievalInputPreviewResponse:
        enabled_profiles, recent_summary, seeds, enabled_sources, plan_previews = (
            self._prepare_preview_data(user_id=user_id)
        )
        self.metrics.increment("external_retrieval_input_previews_total")
        notes = self._preview_notes(plan_count=len(plan_previews))
        with bind_log_context(user_id=user_id):
            logger.info("previewed external retrieval inputs")
        return ExternalRetrievalInputPreviewResponse(
            user_id=user_id,
            mode=self.settings.external_retrieval_mode,
            enabled_sources=enabled_sources,
            enabled_watch_profiles=enabled_profiles,
            effective_retrieval_seeds=seeds.to_read(),
            recent_activity_context_summary=recent_summary,
            source_plan_previews=[draft.to_preview_read() for draft in plan_previews],
            notes=notes,
        )

    def compact_preview(self, *, user_id: UUID) -> ExternalRetrievalPlanningCompactRead:
        preview = self.preview_input(user_id=user_id)
        return ExternalRetrievalPlanningCompactRead(
            mode=preview.mode,
            enabled_sources=preview.enabled_sources,
            preview_plan_count=len(preview.source_plan_previews),
            source_plan_previews=[
                draft.to_compact_read() for draft in self._drafts_from_preview(preview)
            ],
            notes=preview.notes,
        )

    def provider_status(self) -> ExternalRetrievalProviderStatusRead:
        enabled_sources = self.settings.external_retrieval_enabled_source_kinds
        safe_config_presence = {
            "has_openalex_api_key": bool(self.settings.external_retrieval_openalex_api_key),
            "has_crossref_mailto": bool(self.settings.external_retrieval_crossref_mailto),
            "has_crossref_user_agent_app_name": bool(
                self.settings.external_retrieval_crossref_user_agent_app_name
            ),
        }
        source_statuses: list[ExternalRetrievalProviderSourceStatusRead] = []
        for source_kind in ExternalRetrievalSourceKind:
            enabled = source_kind in enabled_sources
            ready, notes = self._source_status(source_kind=source_kind, enabled=enabled)
            source_statuses.append(
                ExternalRetrievalProviderSourceStatusRead(
                    source_kind=source_kind,
                    enabled=enabled,
                    ready=ready,
                    notes=notes,
                )
            )
        readiness_checks = {
            "mode_allows_execute": self.settings.external_retrieval_mode
            == ExternalRetrievalMode.EXECUTE,
            "enabled_sources_present": bool(enabled_sources),
            "openalex_ready": self._source_status(
                source_kind=ExternalRetrievalSourceKind.OPENALEX,
                enabled=ExternalRetrievalSourceKind.OPENALEX in enabled_sources,
            )[0],
            "crossref_ready": self._source_status(
                source_kind=ExternalRetrievalSourceKind.CROSSREF,
                enabled=ExternalRetrievalSourceKind.CROSSREF in enabled_sources,
            )[0],
            "arxiv_ready": self._source_status(
                source_kind=ExternalRetrievalSourceKind.ARXIV,
                enabled=ExternalRetrievalSourceKind.ARXIV in enabled_sources,
            )[0],
        }
        readiness_failures: list[str] = []
        if not readiness_checks["mode_allows_execute"]:
            readiness_failures.append("external retrieval mode is not set to execute")
        if not readiness_checks["enabled_sources_present"]:
            readiness_failures.append("no external retrieval sources are enabled")
        readiness = not readiness_failures
        return ExternalRetrievalProviderStatusRead(
            mode=self.settings.external_retrieval_mode,
            enabled_sources=enabled_sources,
            readiness=readiness,
            readiness_checks=readiness_checks,
            readiness_failures=readiness_failures,
            safe_config_presence=safe_config_presence,
            http_connect_timeout_seconds=self.settings.external_retrieval_http_connect_timeout_seconds,
            http_read_timeout_seconds=self.settings.external_retrieval_http_read_timeout_seconds,
            max_results_per_plan=self.settings.external_retrieval_max_results_per_plan,
            execution_dedupe_minutes=self.settings.external_retrieval_execution_dedupe_minutes,
            source_statuses=source_statuses,
        )

    def list_plans(
        self,
        *,
        user_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
        status: ExternalRetrievalPlanStatus | None = None,
        paper_id: UUID | None = None,
    ) -> list[ExternalRetrievalPlan]:
        return self.plan_repository.list(
            user_id=user_id,
            source_kind=source_kind,
            retrieval_scope=retrieval_scope,
            status=status,
            paper_id=paper_id,
        )

    def build_and_persist_plans(self, *, user_id: UUID) -> list[ExternalRetrievalPlan]:
        self._require_planning_enabled()
        _profiles, _summary, _seeds, _enabled_sources, drafts = self._prepare_preview_data(
            user_id=user_id
        )
        persisted: list[ExternalRetrievalPlan] = []
        for draft in drafts:
            persisted.append(self._upsert_plan(user_id=user_id, draft=draft))
        commit_session(self.session)
        self.metrics.increment("external_retrieval_plans_built_total", len(drafts))
        self.metrics.increment("external_retrieval_plans_persisted_total", len(persisted))
        with bind_log_context(user_id=user_id):
            logger.info("built external retrieval plans", extra={"plan_count": len(persisted)})
        return sorted(
            persisted,
            key=lambda item: (
                item.source_kind.value,
                item.retrieval_scope.value,
                item.plan_label.lower(),
                item.plan_hash,
            ),
        )

    def list_runs(
        self,
        *,
        user_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
        status: ExternalRetrievalRunStatus | None = None,
        plan_id: UUID | None = None,
    ) -> list[ExternalRetrievalRun]:
        return self.run_repository.list(
            user_id=user_id,
            source_kind=source_kind,
            retrieval_scope=retrieval_scope,
            status=status,
            plan_id=plan_id,
        )

    def get_run_detail(self, run_id: UUID) -> ExternalRetrievalRunDetailRead:
        run = self.run_repository.get(run_id)
        if run is None:
            raise NotFoundError(f"external retrieval run {run_id} was not found")
        return ExternalRetrievalRunDetailRead(run=run, results=list(run.results))

    def list_results(
        self,
        *,
        user_id: UUID | None = None,
        run_id: UUID | None = None,
        plan_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
    ) -> list[ExternalRetrievedRecord]:
        return self.record_repository.list(
            user_id=user_id,
            run_id=run_id,
            plan_id=plan_id,
            source_kind=source_kind,
            retrieval_scope=retrieval_scope,
        )

    def execute_plan(
        self,
        *,
        plan_id: UUID,
        force: bool = False,
    ) -> ExternalRetrievalExecutionOutcome:
        self._require_execution_enabled()
        plan = self.plan_repository.get(plan_id)
        if plan is None:
            raise NotFoundError(f"external retrieval plan {plan_id} was not found")
        enabled_sources = self.settings.external_retrieval_enabled_source_kinds
        if plan.source_kind not in enabled_sources:
            raise ValidationFailedError(
                f"external retrieval source {plan.source_kind.value} is not enabled"
            )
        ready, readiness_notes = self._source_status(source_kind=plan.source_kind, enabled=True)
        if not ready:
            raise ValidationFailedError(
                f"external retrieval source {plan.source_kind.value} is not ready"
            )
        dedupe_window = timedelta(
            minutes=max(0, self.settings.external_retrieval_execution_dedupe_minutes)
        )
        if not force and dedupe_window > timedelta(0):
            existing_run = self.run_repository.latest_successful_for_plan_since(
                plan_id=plan.id,
                not_before=self.now_provider() - dedupe_window,
            )
            if existing_run is not None:
                with bind_log_context(
                    user_id=plan.user_id, plan_id=plan.id, run_id=existing_run.id
                ):
                    logger.info("reused external retrieval run from dedupe window")
                return ExternalRetrievalExecutionOutcome(
                    run=existing_run,
                    results=list(existing_run.results),
                    deduped=True,
                    notes=[
                        ("Returned an existing successful run inside the execution dedupe window.")
                    ],
                )

        run = ExternalRetrievalRun(
            plan_id=plan.id,
            user_id=plan.user_id,
            source_kind=plan.source_kind,
            retrieval_scope=plan.retrieval_scope,
            status=ExternalRetrievalRunStatus.RUNNING,
            started_at=self.now_provider(),
        )
        self.run_repository.add(run)
        commit_session(self.session)
        self.metrics.increment("external_retrieval_runs_started_total")

        executor = self.executors.get(plan.source_kind)
        if executor is None:
            run.status = ExternalRetrievalRunStatus.SKIPPED
            run.last_error = f"no executor is available for {plan.source_kind.value}"
            run.finished_at = self.now_provider()
            commit_session(self.session)
            return ExternalRetrievalExecutionOutcome(
                run=run,
                results=[],
                deduped=False,
                notes=[run.last_error],
            )

        try:
            with self.http_client_factory(self.settings) as http_client:
                execution_result = executor.execute(plan=plan, http_client=http_client)
            run.request_url = execution_result.request_url
            run.request_payload = execution_result.request_payload
            run.response_summary = execution_result.response_summary
            run.raw_result_count = execution_result.raw_result_count
            persisted_results = self._persist_execution_results(
                run=run, plan=plan, result=execution_result
            )
            run.normalized_result_count = len(persisted_results)
            run.status = ExternalRetrievalRunStatus.COMPLETED
            run.finished_at = self.now_provider()
            commit_session(self.session)
            self.metrics.increment("external_retrieval_runs_completed_total")
            self.metrics.increment(
                "external_retrieval_results_normalized_total", len(persisted_results)
            )
            with bind_log_context(user_id=plan.user_id, plan_id=plan.id, run_id=run.id):
                logger.info(
                    "completed external retrieval execution",
                    extra={
                        "source_kind": plan.source_kind.value,
                        "retrieval_scope": plan.retrieval_scope.value,
                        "result_count": len(persisted_results),
                    },
                )
            return ExternalRetrievalExecutionOutcome(
                run=run,
                results=persisted_results,
                deduped=False,
                notes=["Executed the retrieval plan and persisted normalized records."],
            )
        except httpx.HTTPError as exc:
            run.status = ExternalRetrievalRunStatus.FAILED
            run.last_error = _compact_text(str(exc), limit=500)
            run.finished_at = self.now_provider()
            commit_session(self.session)
            self.metrics.increment("external_retrieval_runs_failed_total")
            raise ValidationFailedError(
                "external retrieval execution failed for "
                f"{plan.source_kind.value}: {run.last_error}"
            ) from exc
        except ElementTree.ParseError as exc:
            run.status = ExternalRetrievalRunStatus.FAILED
            run.last_error = _compact_text(str(exc), limit=500)
            run.finished_at = self.now_provider()
            commit_session(self.session)
            self.metrics.increment("external_retrieval_runs_failed_total")
            raise ValidationFailedError(
                "external retrieval XML parsing failed for "
                f"{plan.source_kind.value}: {run.last_error}"
            ) from exc

    def compact_execution_summary(self, *, user_id: UUID) -> ExternalRetrievalExecutionSummaryRead:
        runs = self.run_repository.list(user_id=user_id)[:3]
        latest_completed_at = next(
            (run.finished_at for run in runs if run.status == ExternalRetrievalRunStatus.COMPLETED),
            None,
        )
        completed_count = sum(
            1 for run in runs if run.status == ExternalRetrievalRunStatus.COMPLETED
        )
        failed_count = sum(1 for run in runs if run.status == ExternalRetrievalRunStatus.FAILED)
        notes = [
            "This summary only reflects persisted external retrieval execution runs.",
            "Fetched records are available through the external retrieval results API.",
        ]
        return ExternalRetrievalExecutionSummaryRead(
            latest_runs=[
                ExternalRetrievalRunCompactRead(
                    id=run.id,
                    plan_id=run.plan_id,
                    source_kind=run.source_kind,
                    retrieval_scope=run.retrieval_scope,
                    status=run.status,
                    normalized_result_count=run.normalized_result_count,
                    finished_at=run.finished_at,
                )
                for run in runs
            ],
            completed_run_count=completed_count,
            failed_run_count=failed_count,
            latest_completed_at=latest_completed_at,
            notes=notes,
        )

    def _persist_execution_results(
        self,
        *,
        run: ExternalRetrievalRun,
        plan: ExternalRetrievalPlan,
        result: ExternalRetrievalExecutionResult,
    ) -> list[ExternalRetrievedRecord]:
        rows = [
            ExternalRetrievedRecord(
                run_id=run.id,
                plan_id=plan.id,
                user_id=plan.user_id,
                source_kind=plan.source_kind,
                retrieval_scope=plan.retrieval_scope,
                external_id=draft.external_id,
                external_url=draft.external_url,
                doi=draft.doi,
                title=draft.title,
                abstract_snippet=draft.abstract_snippet,
                publication_year=draft.publication_year,
                publication_date=draft.publication_date,
                source_title=draft.source_title,
                authors=draft.authors,
                matched_reason_codes=draft.matched_reason_codes,
                raw_payload=draft.raw_payload,
                sort_order=draft.sort_order,
            )
            for draft in result.records
        ]
        return self.record_repository.add_many(rows)

    def _upsert_plan(
        self,
        *,
        user_id: UUID,
        draft: ExternalRetrievalPlanDraft,
    ) -> ExternalRetrievalPlan:
        existing = self.plan_repository.get_by_plan_hash(draft.plan_hash)
        if existing is not None:
            existing.plan_label = draft.plan_label
            existing.query_text = draft.query_text
            existing.query_payload = draft.query_payload
            existing.effective_inputs = draft.effective_inputs
            existing.reason_codes = draft.reason_codes
            existing.status = ExternalRetrievalPlanStatus.PLANNED
            return existing
        plan = ExternalRetrievalPlan(
            user_id=user_id,
            source_kind=draft.source_kind,
            retrieval_scope=draft.retrieval_scope,
            watch_profile_id=draft.watch_profile_id,
            paper_id=draft.paper_id,
            plan_label=draft.plan_label,
            query_text=draft.query_text,
            query_payload=draft.query_payload,
            effective_inputs=draft.effective_inputs,
            reason_codes=draft.reason_codes,
            plan_hash=draft.plan_hash,
            status=ExternalRetrievalPlanStatus.PLANNED,
        )
        return self.plan_repository.add(plan)

    def _require_planning_enabled(self) -> None:
        if self.settings.external_retrieval_mode == ExternalRetrievalMode.DISABLED:
            raise ValidationFailedError("external retrieval planning is disabled")

    def _require_execution_enabled(self) -> None:
        if self.settings.external_retrieval_mode == ExternalRetrievalMode.DISABLED:
            raise ValidationFailedError("external retrieval execution is disabled")
        if self.settings.external_retrieval_mode != ExternalRetrievalMode.EXECUTE:
            raise ValidationFailedError("external retrieval execution requires execute mode")

    def _ensure_user_exists(self, user_id: UUID) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")

    def _recent_activity_context_summary(self, *, user_id: UUID) -> WorkActivitySummaryRead:
        ended_at = utcnow()
        started_at = ended_at - timedelta(
            days=max(1, self.settings.external_retrieval_lookback_days_for_activity_context)
        )
        events = [
            event
            for event in self.work_activity_repository.list_window_for_user(
                user_id=user_id,
                started_at=started_at,
                ended_at=ended_at,
            )
            if event.source != WorkActivitySource.SYSTEM
        ]
        return _build_activity_summary(events=events, started_at=started_at, ended_at=ended_at)

    def _build_effective_seeds(
        self,
        enabled_profiles: list[ResearchWatchProfile],
        recent_summary: WorkActivitySummaryRead,
    ) -> EffectiveRetrievalSeeds:
        topics = _sorted_terms(term for profile in enabled_profiles for term in profile.topics)
        keywords = _sorted_terms(term for profile in enabled_profiles for term in profile.keywords)
        venues = _sorted_terms(term for profile in enabled_profiles for term in profile.venues)
        authors = _sorted_terms(
            term for profile in enabled_profiles for term in (profile.authors_of_interest or [])
        )
        touched_titles = _sorted_terms(item.title for item in recent_summary.touched_papers)
        return EffectiveRetrievalSeeds(
            topics=topics,
            keywords=keywords,
            venues=venues,
            authors_of_interest=authors,
            touched_paper_titles=touched_titles,
        )

    def _build_plan_previews(
        self,
        *,
        user_id: UUID,
        seeds: EffectiveRetrievalSeeds,
        enabled_profiles: list[ResearchWatchProfile],
        enabled_sources: list[ExternalRetrievalSourceKind],
    ) -> list[ExternalRetrievalPlanDraft]:
        if self.settings.external_retrieval_mode == ExternalRetrievalMode.DISABLED:
            return []
        watch_profile_id = enabled_profiles[0].id if len(enabled_profiles) == 1 else None
        paper_id = enabled_profiles[0].paper_id if len(enabled_profiles) == 1 else None
        return self.planner.build_plans(
            user_id=user_id,
            seeds=seeds,
            enabled_sources=enabled_sources,
            watch_profile_id=watch_profile_id,
            paper_id=paper_id,
        )

    def _preview_notes(self, *, plan_count: int) -> list[str]:
        if self.settings.external_retrieval_mode == ExternalRetrievalMode.DISABLED:
            return [
                "External retrieval planning is currently disabled.",
                "No external execution or fetched content exists in this phase.",
            ]
        if self.settings.external_retrieval_mode == ExternalRetrievalMode.PLAN_ONLY:
            return [
                "This preview shows only deterministic external retrieval planning inputs.",
                f"{plan_count} source-specific plans are available for later execution.",
                "No external execution or fetched content exists in this phase.",
            ]
        return [
            "This preview shows deterministic external retrieval planning inputs before execution.",
            f"{plan_count} source-specific plans are ready for execution in execute mode.",
            "Fetched records are kept separate from pulse card generation in this phase.",
        ]

    def _prepare_preview_data(
        self,
        *,
        user_id: UUID,
    ) -> tuple[
        list[ResearchWatchProfile],
        WorkActivitySummaryRead,
        EffectiveRetrievalSeeds,
        list[ExternalRetrievalSourceKind],
        list[ExternalRetrievalPlanDraft],
    ]:
        self._ensure_user_exists(user_id)
        enabled_profiles = self.watch_repository.list(user_id=user_id, enabled_only=True)
        recent_summary = self._recent_activity_context_summary(user_id=user_id)
        seeds = self._build_effective_seeds(enabled_profiles, recent_summary)
        enabled_sources = self.settings.external_retrieval_enabled_source_kinds
        plan_previews = self._build_plan_previews(
            user_id=user_id,
            seeds=seeds,
            enabled_profiles=enabled_profiles,
            enabled_sources=enabled_sources,
        )
        return enabled_profiles, recent_summary, seeds, enabled_sources, plan_previews

    def _source_status(
        self,
        *,
        source_kind: ExternalRetrievalSourceKind,
        enabled: bool,
    ) -> tuple[bool, list[str]]:
        if not enabled:
            return False, ["source is not enabled"]
        if source_kind == ExternalRetrievalSourceKind.OPENALEX:
            return True, [
                (
                    "OpenAlex execution is ready; api_key is optional and will "
                    "be used when configured."
                )
            ]
        if source_kind == ExternalRetrievalSourceKind.CROSSREF:
            notes = ["Crossref execution is ready through the official REST API."]
            if (
                self.settings.external_retrieval_crossref_mailto
                or self.settings.external_retrieval_crossref_user_agent_app_name
            ):
                notes.append("Polite identification will be attached when configured.")
            else:
                notes.append("Polite identification is not configured and remains optional.")
            return True, notes
        if source_kind == ExternalRetrievalSourceKind.ARXIV:
            return True, ["arXiv execution is ready through the official Atom API endpoint."]
        return False, ["no source handler is configured"]

    def _drafts_from_preview(
        self,
        preview: ExternalRetrievalInputPreviewResponse,
    ) -> list[ExternalRetrievalPlanDraft]:
        drafts: list[ExternalRetrievalPlanDraft] = []
        for item in preview.source_plan_previews:
            drafts.append(
                ExternalRetrievalPlanDraft(
                    source_kind=item.source_kind,
                    retrieval_scope=item.retrieval_scope,
                    watch_profile_id=item.watch_profile_id,
                    paper_id=item.paper_id,
                    plan_label=item.plan_label,
                    query_text=item.query_text,
                    query_payload=item.query_payload,
                    effective_inputs=item.effective_inputs,
                    reason_codes=item.reason_codes,
                    plan_hash=item.plan_hash,
                )
            )
        return drafts


def _build_activity_summary(
    *,
    events: list[WorkActivityEvent],
    started_at: datetime,
    ended_at: datetime,
) -> WorkActivitySummaryRead:
    type_counts = Counter(event.activity_type.value for event in events)
    paper_counts = Counter(event.paper_id for event in events if event.paper_id is not None)
    paper_titles = {
        paper_id: title
        for paper_id, title in sorted(
            (
                (
                    event.paper_id,
                    event.paper.title if event.paper is not None else str(event.paper_id),
                )
                for event in events
                if event.paper_id is not None
            ),
            key=lambda item: str(item[0]),
        )
    }
    touched_papers = [
        WorkActivityTouchedPaperRead(
            paper_id=paper_id,
            title=paper_titles.get(paper_id, str(paper_id)),
            activity_count=count,
        )
        for paper_id, count in sorted(
            paper_counts.items(),
            key=lambda item: (-item[1], paper_titles.get(item[0], str(item[0])).lower()),
        )
    ]
    return WorkActivitySummaryRead(
        window_started_at=_coerce_utc(started_at),
        window_ended_at=_coerce_utc(ended_at),
        total_events=len(events),
        activity_type_counts=dict(sorted(type_counts.items())),
        touched_papers=touched_papers,
    )


def _build_query_text(prefix: str, **parts: list[str]) -> str:
    fragments = [prefix]
    for key in (
        "keywords",
        "topics",
        "touched_paper_titles",
        "venues",
        "authors_of_interest",
    ):
        values = parts.get(key) or []
        if not values:
            continue
        label = key.replace("_", " ")
        fragments.append(f"{label}: {', '.join(values)}")
    return " | ".join(fragments)


def _reason_codes(
    *,
    keywords: bool = False,
    topics: bool = False,
    venues: bool = False,
    authors: bool = False,
    touched_titles: bool = False,
) -> list[str]:
    codes: list[str] = []
    if keywords:
        codes.append("watch_keywords_present")
    if topics:
        codes.append("watch_topics_present")
    if venues:
        codes.append("watch_venues_present")
    if authors:
        codes.append("watch_authors_present")
    if touched_titles:
        codes.append("recent_touched_paper_context")
    return codes


def _limited_terms(values: list[str], limit: int) -> list[str]:
    return _sorted_terms(values)[: max(0, limit)]


def _sorted_terms(values) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        if value is None:
            continue
        cleaned = str(value).strip()
        if not cleaned:
            continue
        seen.setdefault(cleaned.casefold(), cleaned)
    return [seen[key] for key in sorted(seen)]


def _normalize_json(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def _stable_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _joined_terms(*groups: list[str]) -> str:
    return " ".join(_sorted_terms(term for group in groups for term in group))


def _payload_terms(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list):
        return []
    return _sorted_terms(value)


def _sanitize_url(raw_url: str, redacted_keys: set[str] | None = None) -> str:
    redacted_keys = redacted_keys or set()
    parts = urlsplit(raw_url)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in redacted_keys
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(filtered_query), parts.fragment)
    )


def _sanitize_mapping(
    payload: dict[str, Any],
    *,
    redacted_keys: set[str] | None = None,
) -> dict[str, Any]:
    redacted_keys = redacted_keys or set()
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key in redacted_keys:
            continue
        cleaned[key] = value
    return cleaned


def _compact_text(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _first_string(value: Any) -> str | None:
    if isinstance(value, list) and value:
        return _compact_text(value[0], limit=500)
    return _compact_text(value, limit=500)


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_doi(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = _compact_text(value, limit=255)
    if cleaned is None:
        return None
    cleaned = cleaned.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return cleaned or None


def _strip_markup(value: Any) -> str | None:
    text = _compact_text(value, limit=5000)
    if text is None:
        return None
    without_tags = re.sub(r"<[^>]+>", " ", unescape(text))
    return _compact_text(without_tags, limit=5000)


def _openalex_abstract_from_inverted_index(value: Any) -> str | None:
    if not isinstance(value, dict) or not value:
        return None
    positioned_terms: list[tuple[int, str]] = []
    for term, positions in value.items():
        if not isinstance(positions, list):
            continue
        for position in positions:
            try:
                positioned_terms.append((int(position), str(term)))
            except (TypeError, ValueError):
                continue
    if not positioned_terms:
        return None
    ordered_terms = [term for _position, term in sorted(positioned_terms)]
    return " ".join(ordered_terms)


def _crossref_publication_date(item: dict[str, Any]) -> str | None:
    for key in ("published-print", "published-online", "issued", "created"):
        payload = item.get(key) or {}
        parts = payload.get("date-parts") or []
        if not parts or not isinstance(parts[0], list) or not parts[0]:
            continue
        date_parts = [str(part) for part in parts[0][:3]]
        return "-".join(date_parts)
    return None


def _publication_year_from_date(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(str(value).split("-", maxsplit=1)[0])
    except (TypeError, ValueError):
        return None


def _xml_text(node: ElementTree.Element | None) -> str | None:
    if node is None or node.text is None:
        return None
    return re.sub(r"\s+", " ", node.text).strip() or None


def _escape_arxiv_term(term: str) -> str:
    return term.replace('"', "").strip()
