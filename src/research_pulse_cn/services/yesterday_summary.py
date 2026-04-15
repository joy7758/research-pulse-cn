"""Deterministic yesterday-summary builder for pulse input facts."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import Settings, get_settings
from research_pulse_cn.core.errors import ValidationFailedError
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import WorkActivityEvent, utcnow
from research_pulse_cn.domain.enums import SubscriptionFrequency, WorkActivitySource
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.work_activity import WorkActivityRepository
from research_pulse_cn.schemas.pulse_input import WorkActivityTouchedPaperRead

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class YesterdaySummarySnapshot:
    summary_date: date
    timezone_name: str
    window_started_at: datetime
    window_ended_at: datetime
    total_events: int
    activity_type_counts: dict[str, int]
    touched_papers: list[WorkActivityTouchedPaperRead]
    distinct_activity_type_count: int
    top_activity_types: list[str]
    text_summary: str


class YesterdaySummaryBuilder:
    """Build a deterministic previous-local-day recap from work activity."""

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
        self.work_activity_repository = WorkActivityRepository(session)
        self.policy_repository = SubscriptionPolicyRepository(session)

    def build(
        self,
        *,
        user_id: UUID,
        timezone_name: str | None = None,
        target_local_date: date | None = None,
        reference: datetime | None = None,
    ) -> YesterdaySummarySnapshot:
        resolved_timezone = self.resolve_timezone_name(
            user_id=user_id,
            explicit_timezone=timezone_name,
        )
        zone = ZoneInfo(resolved_timezone)
        reference_now = _coerce_utc(reference or self.now_provider())
        if target_local_date is None:
            target_local_date = reference_now.astimezone(zone).date() - timedelta(days=1)
        local_started_at = datetime.combine(target_local_date, time.min, tzinfo=zone)
        local_ended_at = local_started_at + timedelta(days=1)
        started_at = local_started_at.astimezone(UTC)
        ended_at = local_ended_at.astimezone(UTC)
        raw_events = self.work_activity_repository.list_window_for_user(
            user_id=user_id,
            started_at=started_at,
            ended_at=ended_at,
        )
        events = [event for event in raw_events if event.source != WorkActivitySource.SYSTEM]
        snapshot = self._build_snapshot(
            target_local_date=target_local_date,
            timezone_name=resolved_timezone,
            started_at=started_at,
            ended_at=ended_at,
            events=events,
        )
        with bind_log_context(user_id=user_id):
            logger.info(
                "built yesterday summary snapshot",
                extra={
                    "summary_date": snapshot.summary_date.isoformat(),
                    "total_events": snapshot.total_events,
                    "timezone": snapshot.timezone_name,
                },
            )
        return snapshot

    def resolve_timezone_name(
        self,
        *,
        user_id: UUID,
        explicit_timezone: str | None = None,
    ) -> str:
        if explicit_timezone:
            cleaned = explicit_timezone.strip()
            if not cleaned:
                raise ValidationFailedError("timezone must not be empty")
            if not _is_valid_timezone(cleaned):
                raise ValidationFailedError(f"timezone {cleaned} is invalid")
            return cleaned

        policies = sorted(
            self.policy_repository.list(user_id=user_id, enabled_only=True),
            key=lambda policy: (policy.created_at, str(policy.id)),
        )
        for policy in policies:
            if policy.frequency != SubscriptionFrequency.DAILY:
                continue
            raw_policy = dict(policy.policy or {})
            schedule = raw_policy.get("schedule")
            if not isinstance(schedule, dict):
                schedule = raw_policy
            timezone_name = schedule.get("timezone")
            if not isinstance(timezone_name, str):
                continue
            cleaned = timezone_name.strip()
            if cleaned and _is_valid_timezone(cleaned):
                return cleaned
        if _is_valid_timezone(self.settings.default_timezone):
            return self.settings.default_timezone
        return "UTC"

    def _build_snapshot(
        self,
        *,
        target_local_date: date,
        timezone_name: str,
        started_at: datetime,
        ended_at: datetime,
        events: list[WorkActivityEvent],
    ) -> YesterdaySummarySnapshot:
        activity_type_counts = Counter(event.activity_type.value for event in events)
        paper_counts = Counter(event.paper_id for event in events if event.paper_id is not None)
        paper_titles = self.work_activity_repository.paper_titles(set(paper_counts))
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
        top_activity_types = [
            activity_type
            for activity_type, _count in sorted(
                activity_type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        ]
        return YesterdaySummarySnapshot(
            summary_date=target_local_date,
            timezone_name=timezone_name,
            window_started_at=started_at,
            window_ended_at=ended_at,
            total_events=len(events),
            activity_type_counts=dict(sorted(activity_type_counts.items())),
            touched_papers=touched_papers,
            distinct_activity_type_count=len(activity_type_counts),
            top_activity_types=top_activity_types,
            text_summary=_build_text_summary(
                target_local_date=target_local_date,
                total_events=len(events),
                distinct_activity_type_count=len(activity_type_counts),
                touched_papers=touched_papers,
                top_activity_types=top_activity_types,
            ),
        )


def _build_text_summary(
    *,
    target_local_date: date,
    total_events: int,
    distinct_activity_type_count: int,
    touched_papers: list[WorkActivityTouchedPaperRead],
    top_activity_types: list[str],
) -> str:
    if total_events == 0:
        return f"No qualifying work activity was recorded for {target_local_date.isoformat()}."
    segments = [f"Yesterday recorded {total_events} activities"]
    if touched_papers:
        segments.append(f"across {len(touched_papers)} papers")
    segments.append(f"covering {distinct_activity_type_count} activity types")
    summary = " ".join(segments) + "."
    if top_activity_types:
        summary += f" Top activity types: {', '.join(top_activity_types)}."
    return summary


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _is_valid_timezone(timezone_name: str) -> bool:
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return False
    return True
