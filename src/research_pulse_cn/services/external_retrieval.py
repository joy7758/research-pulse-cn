"""Deterministic external retrieval input planning services."""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    ExternalRetrievalPlan,
    ResearchWatchProfile,
    WorkActivityEvent,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ExternalRetrievalMode,
    ExternalRetrievalPlanStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
    WorkActivitySource,
)
from research_pulse_cn.repositories.external_retrieval import ExternalRetrievalPlanRepository
from research_pulse_cn.repositories.research_watch import ResearchWatchProfileRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.repositories.work_activity import WorkActivityRepository
from research_pulse_cn.schemas.pulse_input import (
    EffectiveRetrievalSeedsRead,
    ExternalRetrievalInputPreviewResponse,
    ExternalRetrievalPlanCompactRead,
    ExternalRetrievalPlanningCompactRead,
    ExternalRetrievalPlanPreviewRead,
    WorkActivitySummaryRead,
    WorkActivityTouchedPaperRead,
)
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)


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
    """Preview and persist deterministic external retrieval plans."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repository = ExternalRetrievalPlanRepository(session)
        self.user_repository = UserRepository(session)
        self.watch_repository = ResearchWatchProfileRepository(session)
        self.work_activity_repository = WorkActivityRepository(session)
        self.metrics = get_metrics()
        self.planner = ExternalRetrievalPlanner(self.settings)

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
                ExternalRetrievalPlanCompactRead(
                    source_kind=item.source_kind,
                    retrieval_scope=item.retrieval_scope,
                    plan_label=item.plan_label,
                    query_text=item.query_text,
                    reason_codes=item.reason_codes,
                )
                for item in preview.source_plan_previews
            ],
            notes=preview.notes,
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
        return self.repository.list(
            user_id=user_id,
            source_kind=source_kind,
            retrieval_scope=retrieval_scope,
            status=status,
            paper_id=paper_id,
        )

    def build_and_persist_plans(self, *, user_id: UUID) -> list[ExternalRetrievalPlan]:
        if self.settings.external_retrieval_mode != ExternalRetrievalMode.PLAN_ONLY:
            raise ValidationFailedError("external retrieval planning is disabled")
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

    def _upsert_plan(
        self,
        *,
        user_id: UUID,
        draft: ExternalRetrievalPlanDraft,
    ) -> ExternalRetrievalPlan:
        existing = self.repository.get_by_plan_hash(draft.plan_hash)
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
        return self.repository.add(plan)

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
        if self.settings.external_retrieval_mode != ExternalRetrievalMode.PLAN_ONLY:
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
        return [
            "This preview shows only deterministic external retrieval planning inputs.",
            f"{plan_count} source-specific plans are available for later execution.",
            "No external execution or fetched content exists in this phase.",
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
