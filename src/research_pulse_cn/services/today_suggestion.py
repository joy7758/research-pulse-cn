"""Deterministic today-suggestion builder for internal pulse facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.db.models import PaperProfile, utcnow
from research_pulse_cn.domain.enums import PaperType
from research_pulse_cn.repositories.paper import PaperRepository


class TodaySuggestionKind(StrEnum):
    EXECUTE_NEXT_ACTION = "execute_next_action"
    RESOLVE_BLOCKER = "resolve_blocker"
    DEFINE_NEXT_ACTION = "define_next_action"


@dataclass(slots=True)
class TodaySuggestionDecision:
    paper_id: UUID
    paper_title: str
    paper_type: str
    stage: str
    priority: int
    suggestion_kind: str
    title: str
    summary: str
    why_now: str
    action_text: str
    next_action: str | None
    blocker: str | None
    last_touch_at: datetime | None
    days_since_last_touch: int | None
    latest_progress_event_at: datetime | None
    latest_signal_snapshot_at: datetime | None
    effective_timezone: str
    considered_paper_count: int
    top_reason_codes: list[str]
    action_context: str
    selection_score: int


@dataclass(slots=True)
class _PaperSuggestionEvaluation:
    paper: PaperProfile
    suggestion_kind: TodaySuggestionKind
    reason_codes: list[str]
    selection_score: int
    last_touch_at: datetime | None
    days_since_last_touch: int | None
    latest_progress_event_at: datetime | None
    latest_signal_snapshot_at: datetime | None
    next_action: str | None
    blocker: str | None
    published_context_ok: bool


class TodaySuggestionBuilder:
    """Choose one deterministic best next step from internal paper state."""

    ACTIVE_PAPER_TYPES = {
        PaperType.IN_PREP,
        PaperType.UNDER_REVIEW,
        PaperType.REVISION,
    }

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
        self.paper_repository = PaperRepository(session)

    def build(
        self,
        *,
        user_id: UUID,
        timezone_name: str,
        stale_days_threshold: int,
        reference: datetime | None = None,
    ) -> TodaySuggestionDecision | None:
        now = _coerce_utc(reference or self.now_provider())
        evaluations = [
            evaluation
            for paper in self.paper_repository.list(user_id=user_id)
            if (evaluation := self._evaluate_paper(paper, now, stale_days_threshold)) is not None
        ]
        if not evaluations:
            return None
        best = sorted(evaluations, key=self._selection_sort_key)[0]
        return self._to_decision(
            evaluation=best,
            timezone_name=timezone_name,
            considered_paper_count=len(evaluations),
        )

    def _evaluate_paper(
        self,
        paper: PaperProfile,
        now: datetime,
        stale_days_threshold: int,
    ) -> _PaperSuggestionEvaluation | None:
        next_action = _clean_text(paper.next_action)
        blocker = _clean_text(paper.blocker)
        last_touch_at = _coerce_utc(paper.last_touch_at or paper.created_at)
        days_since_last_touch = max(0, (now - last_touch_at).days)
        latest_progress_event_at = _latest_datetime(
            event.happened_at for event in paper.progress_events
        )
        latest_signal_snapshot_at = _latest_datetime(
            snapshot.fetched_at for snapshot in paper.signal_snapshots
        )

        published_context_ok = False
        if paper.type == PaperType.PAUSED:
            return None
        if paper.type in self.ACTIVE_PAPER_TYPES:
            eligible = True
        elif paper.type == PaperType.PUBLISHED:
            published_context_ok = (
                next_action is not None
                and latest_signal_snapshot_at is not None
                and max(0, (now - latest_signal_snapshot_at).days) <= stale_days_threshold
            )
            eligible = published_context_ok
        else:
            eligible = False
        if not eligible:
            return None

        suggestion_kind = self._resolve_suggestion_kind(next_action=next_action, blocker=blocker)
        reason_weights: dict[str, int] = {}
        selection_score = paper.priority * 10
        if suggestion_kind == TodaySuggestionKind.RESOLVE_BLOCKER:
            selection_score += 24
            reason_weights["blocker_present"] = 70
        elif suggestion_kind == TodaySuggestionKind.EXECUTE_NEXT_ACTION:
            selection_score += 16
            reason_weights["explicit_next_action"] = 55
        else:
            selection_score += 8
            reason_weights["no_next_action_defined"] = 35

        if paper.priority >= 4:
            reason_weights["high_priority"] = 60 + paper.priority
        if paper.type == PaperType.REVISION:
            selection_score += 12
            reason_weights["revision_stage"] = 58
        if days_since_last_touch >= stale_days_threshold:
            selection_score += 8
            reason_weights["stale_progress"] = 45 + min(days_since_last_touch, 30)
        if paper.type == PaperType.PUBLISHED and published_context_ok:
            selection_score -= 6

        reason_codes = [
            code
            for code, _weight in sorted(
                reason_weights.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
        return _PaperSuggestionEvaluation(
            paper=paper,
            suggestion_kind=suggestion_kind,
            reason_codes=reason_codes,
            selection_score=selection_score,
            last_touch_at=last_touch_at,
            days_since_last_touch=days_since_last_touch,
            latest_progress_event_at=latest_progress_event_at,
            latest_signal_snapshot_at=latest_signal_snapshot_at,
            next_action=next_action,
            blocker=blocker,
            published_context_ok=published_context_ok,
        )

    def _resolve_suggestion_kind(
        self,
        *,
        next_action: str | None,
        blocker: str | None,
    ) -> TodaySuggestionKind:
        if blocker:
            return TodaySuggestionKind.RESOLVE_BLOCKER
        if next_action:
            return TodaySuggestionKind.EXECUTE_NEXT_ACTION
        return TodaySuggestionKind.DEFINE_NEXT_ACTION

    def _selection_sort_key(
        self,
        evaluation: _PaperSuggestionEvaluation,
    ) -> tuple[object, ...]:
        kind_rank = {
            TodaySuggestionKind.RESOLVE_BLOCKER: 0,
            TodaySuggestionKind.EXECUTE_NEXT_ACTION: 1,
            TodaySuggestionKind.DEFINE_NEXT_ACTION: 2,
        }
        return (
            -evaluation.selection_score,
            kind_rank[evaluation.suggestion_kind],
            -evaluation.paper.priority,
            -(evaluation.days_since_last_touch or 0),
            evaluation.paper.title.lower(),
            str(evaluation.paper.id),
        )

    def _to_decision(
        self,
        *,
        evaluation: _PaperSuggestionEvaluation,
        timezone_name: str,
        considered_paper_count: int,
    ) -> TodaySuggestionDecision:
        paper = evaluation.paper
        suggestion_kind = evaluation.suggestion_kind
        if suggestion_kind == TodaySuggestionKind.RESOLVE_BLOCKER:
            title = f"Resolve blocker for {paper.title}"
            summary = f"Current blocker: {evaluation.blocker}"
            why_now = (
                f"{paper.title} is still active, and clearing this blocker is the fastest "
                "way to unblock meaningful progress today."
            )
            action_text = f"Resolve blocker: {evaluation.blocker}"
            action_context = evaluation.blocker or ""
        elif suggestion_kind == TodaySuggestionKind.EXECUTE_NEXT_ACTION:
            title = f"Execute next action for {paper.title}"
            summary = evaluation.next_action or "Review the current next action."
            why_now = (
                f"{paper.title} already has a concrete next step and currently offers "
                "the clearest internal move for today."
            )
            action_text = evaluation.next_action or "Review the current next action."
            action_context = evaluation.next_action or ""
        else:
            title = f"Define next action for {paper.title}"
            summary = f"{paper.title} is active but does not yet have a concrete next step."
            why_now = (
                f"{paper.title} is still active, and defining one explicit next action will "
                "create a clearer execution path for today."
            )
            action_text = "Write one concrete next action for this paper."
            action_context = ""
        return TodaySuggestionDecision(
            paper_id=paper.id,
            paper_title=paper.title,
            paper_type=paper.type.value,
            stage=paper.stage,
            priority=paper.priority,
            suggestion_kind=suggestion_kind.value,
            title=title,
            summary=summary,
            why_now=why_now,
            action_text=action_text,
            next_action=evaluation.next_action,
            blocker=evaluation.blocker,
            last_touch_at=evaluation.last_touch_at,
            days_since_last_touch=evaluation.days_since_last_touch,
            latest_progress_event_at=evaluation.latest_progress_event_at,
            latest_signal_snapshot_at=evaluation.latest_signal_snapshot_at,
            effective_timezone=timezone_name,
            considered_paper_count=considered_paper_count,
            top_reason_codes=evaluation.reason_codes[:3],
            action_context=action_context,
            selection_score=evaluation.selection_score,
        )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _latest_datetime(values) -> datetime | None:
    normalized = [_coerce_utc(value) for value in values if value is not None]
    if not normalized:
        return None
    return max(normalized)
