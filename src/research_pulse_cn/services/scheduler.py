"""Daily scheduler service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import ConflictError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.db.models import PulseJob, SubscriptionPolicy
from research_pulse_cn.db.models import utcnow as db_utcnow
from research_pulse_cn.domain.enums import (
    PulseJobScheduledReason,
    PulseJobStatus,
    SubscriptionFrequency,
)
from research_pulse_cn.repositories.pulse import PulseRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.services.common import commit_session


@dataclass(slots=True)
class SchedulerResolvedPolicy:
    """Resolved daily scheduling settings for one subscription policy."""

    timezone_name: str
    send_hour_local: int
    send_minute_local: int


class SchedulerService:
    """Schedule due daily pulse jobs without duplicating local dates."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider=None,
    ) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or db_utcnow
        self.policy_repository = SubscriptionPolicyRepository(session)
        self.pulse_repository = PulseRepository(session)
        self.metrics = get_metrics()

    def tick(self) -> dict[str, Any]:
        now = self.now_provider()
        self.metrics.increment("scheduler_ticks_total")
        created_jobs: list[PulseJob] = []
        existing = 0
        skipped_not_due = 0
        daily_policies_seen = 0

        for policy in self.policy_repository.list(enabled_only=True):
            if policy.frequency != SubscriptionFrequency.DAILY:
                continue
            daily_policies_seen += 1
            if not policy.enabled:
                continue

            resolved = self._resolve_policy(policy)
            schedule = self._schedule_for_policy(policy, resolved, now)
            if not schedule["is_due"]:
                skipped_not_due += 1
                continue

            schedule_key = str(schedule["schedule_key"])
            existing_job = self.pulse_repository.get_by_schedule_key(schedule_key)
            if existing_job is not None:
                existing += 1
                continue

            job = PulseJob(
                user_id=policy.user_id,
                subscription_policy_id=policy.id,
                scheduled_for=schedule["scheduled_for_utc"],
                scheduled_reason=PulseJobScheduledReason.DAILY_SCHEDULE,
                schedule_key=schedule_key,
                status=PulseJobStatus.PENDING,
            )
            try:
                self.pulse_repository.add_job(job)
                commit_session(self.session)
            except ConflictError:
                existing += 1
                continue

            created_jobs.append(self.pulse_repository.get_job(job.id) or job)

        if created_jobs:
            self.metrics.increment("scheduler_jobs_created_total", len(created_jobs))

        return {
            "status": "ok",
            "ticked_at": now,
            "daily_policies_seen": daily_policies_seen,
            "jobs_created": len(created_jobs),
            "jobs_existing": existing,
            "jobs_skipped_not_due": skipped_not_due,
            "created_jobs": created_jobs,
            "note": (
                "Only enabled daily policies are auto-scheduled in v1. "
                "Event policies remain manual for a later phase."
            ),
        }

    def _resolve_policy(self, policy: SubscriptionPolicy) -> SchedulerResolvedPolicy:
        raw_policy = dict(policy.policy or {})
        schedule = raw_policy.get("schedule")
        if not isinstance(schedule, dict):
            schedule = raw_policy
        timezone_name = str(schedule.get("timezone", self.settings.default_timezone))
        send_hour_local = int(
            schedule.get("send_hour_local", self.settings.pulse_default_send_hour_local)
        )
        send_minute_local = int(
            schedule.get("send_minute_local", self.settings.pulse_default_send_minute_local)
        )
        return SchedulerResolvedPolicy(
            timezone_name=timezone_name,
            send_hour_local=send_hour_local,
            send_minute_local=send_minute_local,
        )

    def _schedule_for_policy(
        self,
        policy: SubscriptionPolicy,
        resolved: SchedulerResolvedPolicy,
        now: datetime,
    ) -> dict[str, Any]:
        zone = _safe_zoneinfo(resolved.timezone_name)
        local_now = now.astimezone(zone)
        local_date = local_now.date()
        local_send_at = datetime.combine(
            local_date,
            time(hour=resolved.send_hour_local, minute=resolved.send_minute_local),
            tzinfo=zone,
        )
        scheduled_for_utc = local_send_at.astimezone(UTC)
        return {
            "policy_id": policy.id,
            "user_id": policy.user_id,
            "local_date": local_date,
            "scheduled_for_utc": scheduled_for_utc,
            "schedule_key": _build_schedule_key(policy.id, local_date),
            "is_due": local_now >= local_send_at,
        }


def _safe_zoneinfo(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _build_schedule_key(subscription_policy_id: UUID, local_date: date) -> str:
    return f"daily:{subscription_policy_id}:{local_date.isoformat()}"
