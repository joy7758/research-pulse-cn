"""Typed pulse pipeline objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from research_pulse_cn.domain.enums import PulseCardType


class SuppressionCode(StrEnum):
    """Known suppression codes for explainable ranking."""

    QUIET_HOURS = "quiet_hours"
    FREQUENCY_CAP = "frequency_cap"
    DEDUPE_WINDOW = "dedupe_window"
    LOW_SCORE = "low_score"
    PAUSED_PAPER = "paused_paper"


@dataclass(slots=True)
class ScoreBreakdown:
    """Machine-readable score explanation."""

    base_weight: int
    modifiers: dict[str, int] = field(default_factory=dict)
    total: int = 0

    def finalize(self) -> None:
        self.total = self.base_weight + sum(self.modifiers.values())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SuppressionReason:
    """Explain why a candidate was not selected."""

    code: SuppressionCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass(slots=True)
class PulseFact:
    """Raw deterministic fact collected from paper state."""

    id: str
    user_id: UUID
    card_type: PulseCardType
    source_paper_id: UUID | None
    source_timestamp: datetime
    paper_title: str
    summary: str
    why_now: str
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["user_id"] = str(self.user_id)
        payload["source_paper_id"] = str(self.source_paper_id) if self.source_paper_id else None
        payload["card_type"] = self.card_type.value
        payload["source_timestamp"] = self.source_timestamp.isoformat()
        return payload


@dataclass(slots=True)
class PulseCandidate:
    """Candidate card produced before scoring and suppression."""

    id: str
    fact_id: str
    user_id: UUID
    card_type: PulseCardType
    source_paper_id: UUID | None
    source_timestamp: datetime
    paper_title: str
    title_hint: str
    title: str
    summary: str
    why_now: str
    action_text: str | None = None
    deep_link: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    candidate_metadata: dict[str, Any] = field(default_factory=dict)
    score_breakdown: ScoreBreakdown | None = None
    score_total: int = 0
    suppression_reasons: list[SuppressionReason] = field(default_factory=list)

    @property
    def is_suppressed(self) -> bool:
        return bool(self.suppression_reasons)

    def add_suppression(self, reason: SuppressionReason) -> None:
        self.suppression_reasons.append(reason)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fact_id": self.fact_id,
            "user_id": str(self.user_id),
            "card_type": self.card_type.value,
            "source_paper_id": str(self.source_paper_id) if self.source_paper_id else None,
            "source_timestamp": self.source_timestamp.isoformat(),
            "paper_title": self.paper_title,
            "title_hint": self.title_hint,
            "title": self.title,
            "summary": self.summary,
            "why_now": self.why_now,
            "action_text": self.action_text,
            "deep_link": self.deep_link,
            "evidence_refs": self.evidence_refs,
            "candidate_metadata": self.candidate_metadata,
            "score_total": self.score_total,
            "score_breakdown": (
                self.score_breakdown.to_dict() if self.score_breakdown is not None else None
            ),
            "suppression_reasons": [reason.to_dict() for reason in self.suppression_reasons],
        }


@dataclass(slots=True)
class PulseScoringConfig:
    """Resolved scoring and selection knobs for one user run."""

    stale_days: int
    deadline_horizon_days: int
    dedupe_window_hours: int
    min_score: int
    max_cards_per_run: int
    today_suggestion_stale_days_threshold: int
    today_suggestion_priority_bonus: int
    today_suggestion_has_next_action_bonus: int
    today_suggestion_revision_stage_bonus: int
    today_suggestion_stale_progress_bonus: int
    today_suggestion_blocker_present_bonus: int
    yesterday_summary_min_events: int
    yesterday_summary_activity_diversity_bonus: int
    yesterday_summary_multi_paper_bonus: int
    score_weights: dict[PulseCardType, int]
    urgency_modifiers: dict[str, int]
    quiet_hours: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stale_days": self.stale_days,
            "deadline_horizon_days": self.deadline_horizon_days,
            "dedupe_window_hours": self.dedupe_window_hours,
            "min_score": self.min_score,
            "max_cards_per_run": self.max_cards_per_run,
            "today_suggestion_stale_days_threshold": self.today_suggestion_stale_days_threshold,
            "today_suggestion_priority_bonus": self.today_suggestion_priority_bonus,
            "today_suggestion_has_next_action_bonus": (self.today_suggestion_has_next_action_bonus),
            "today_suggestion_revision_stage_bonus": (self.today_suggestion_revision_stage_bonus),
            "today_suggestion_stale_progress_bonus": (self.today_suggestion_stale_progress_bonus),
            "today_suggestion_blocker_present_bonus": (self.today_suggestion_blocker_present_bonus),
            "yesterday_summary_min_events": self.yesterday_summary_min_events,
            "yesterday_summary_activity_diversity_bonus": (
                self.yesterday_summary_activity_diversity_bonus
            ),
            "yesterday_summary_multi_paper_bonus": (self.yesterday_summary_multi_paper_bonus),
            "score_weights": {
                card_type.value: weight for card_type, weight in self.score_weights.items()
            },
            "urgency_modifiers": dict(self.urgency_modifiers),
            "quiet_hours": list(self.quiet_hours),
        }


@dataclass(slots=True)
class PulsePipelineResult:
    """Explainable output of a pulse preview or run."""

    user_id: UUID
    config: PulseScoringConfig
    facts: list[PulseFact]
    candidates: list[PulseCandidate]
    selected_candidates: list[PulseCandidate]
    ordering_explanation: dict[str, Any]

    @property
    def suppressed_candidates(self) -> list[PulseCandidate]:
        return [candidate for candidate in self.candidates if candidate.is_suppressed]

    @property
    def fact_summary(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for fact in self.facts:
            counts[fact.card_type.value] = counts.get(fact.card_type.value, 0) + 1
        return {
            "total_facts": len(self.facts),
            "counts_by_type": counts,
        }
