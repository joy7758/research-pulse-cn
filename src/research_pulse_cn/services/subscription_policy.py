"""Subscription policy application service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.db.models import SubscriptionPolicy
from research_pulse_cn.domain.enums import (
    ACTIVE_DELIVERY_CHANNELS,
    ChannelType,
    SyncEventSource,
    SyncEventType,
    WorkActivityType,
)
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.subscription_policy import (
    SubscriptionPolicyCreate,
    SubscriptionPolicyUpdate,
)
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.sync_events import SyncEventService
from research_pulse_cn.services.work_activity import WorkActivityService


class SubscriptionPolicyService:
    """Use-case layer for subscription policies."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repository = SubscriptionPolicyRepository(session)
        self.user_repository = UserRepository(session)
        self.sync_events = SyncEventService(session)
        self.work_activity = WorkActivityService(session)

    def list_policies(self, *, user_id: UUID | None = None) -> list[SubscriptionPolicy]:
        return self.repository.list(user_id=user_id)

    def get_policy(self, policy_id: UUID) -> SubscriptionPolicy:
        policy = self.repository.get(policy_id)
        if policy is None:
            raise NotFoundError(f"subscription policy {policy_id} was not found")
        return policy

    def create_policy(
        self,
        payload: SubscriptionPolicyCreate,
        *,
        event_source: SyncEventSource = SyncEventSource.API,
    ) -> SubscriptionPolicy:
        if self.user_repository.get(payload.user_id) is None:
            raise NotFoundError(f"user {payload.user_id} was not found")
        self._ensure_supported_channel(payload.channel)
        normalized_quiet_hours, normalized_policy = normalize_subscription_policy_payload(
            channel=payload.channel,
            quiet_hours=payload.quiet_hours,
            policy=payload.policy,
            default_timezone=self.settings.default_timezone,
        )
        policy = SubscriptionPolicy(
            **payload.model_dump(exclude={"quiet_hours", "policy"}),
            quiet_hours=normalized_quiet_hours,
            policy=normalized_policy,
        )
        self.repository.add(policy)
        self.sync_events.emit_subscription_policy(
            policy,
            event_type=SyncEventType.CREATED,
            event_source=event_source,
        )
        self.work_activity.record_event(
            user_id=policy.user_id,
            paper_id=None,
            activity_type=WorkActivityType.SUBSCRIPTION_POLICY_UPDATED,
            summary=_policy_summary(policy.channel.value, created=True),
            metadata={"channel": policy.channel.value, "enabled": policy.enabled},
            happened_at=policy.updated_at,
            source=self.work_activity.source_from_event_source(event_source),
        )
        commit_session(self.session)
        return self.get_policy(policy.id)

    def update_policy(
        self,
        policy_id: UUID,
        payload: SubscriptionPolicyUpdate,
        *,
        event_source: SyncEventSource = SyncEventSource.API,
    ) -> SubscriptionPolicy:
        policy = self.get_policy(policy_id)
        if payload.channel is not None:
            self._ensure_supported_channel(payload.channel)
        update_data = payload.model_dump(exclude_unset=True)
        normalized_quiet_hours, normalized_policy = normalize_subscription_policy_payload(
            channel=update_data.get("channel", policy.channel),
            quiet_hours=(
                update_data["quiet_hours"] if "quiet_hours" in update_data else policy.quiet_hours
            ),
            policy=update_data["policy"] if "policy" in update_data else policy.policy,
            default_timezone=self.settings.default_timezone,
        )
        update_data["quiet_hours"] = normalized_quiet_hours
        update_data["policy"] = normalized_policy
        for field, value in update_data.items():
            setattr(policy, field, value)
        self.sync_events.emit_subscription_policy(
            policy,
            event_type=SyncEventType.UPDATED,
            event_source=event_source,
        )
        self.work_activity.record_event(
            user_id=policy.user_id,
            paper_id=None,
            activity_type=WorkActivityType.SUBSCRIPTION_POLICY_UPDATED,
            summary=_policy_summary(policy.channel.value, created=False),
            metadata={
                "channel": policy.channel.value,
                "enabled": policy.enabled,
                "updated_fields": sorted(payload.model_dump(exclude_unset=True)),
            },
            happened_at=policy.updated_at,
            source=self.work_activity.source_from_event_source(event_source),
        )
        commit_session(self.session)
        return self.get_policy(policy_id)

    def delete_policy(self, policy_id: UUID) -> None:
        policy = self.get_policy(policy_id)
        self.repository.delete(policy)
        commit_session(self.session)

    def _ensure_supported_channel(self, channel) -> None:
        if channel not in ACTIVE_DELIVERY_CHANNELS:
            raise ValidationFailedError(
                f"delivery channel {channel.value} is deprecated and unavailable in this phase"
            )


def _policy_summary(channel: str, *, created: bool) -> str:
    if created:
        return f"Configured subscription policy for {channel}."
    return f"Updated subscription policy for {channel}."


@dataclass(slots=True)
class NormalizedDeliveryControlPolicy:
    channel: ChannelType
    enabled: bool
    effective_timezone: str
    quiet_hours: dict[str, Any] | None
    allowed_weekdays: list[int]
    muted_until: datetime | None
    minimum_selected_cards: int | None
    skip_if_no_today_focus: bool
    subscription_policy_id: UUID | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel.value,
            "enabled": self.enabled,
            "effective_timezone": self.effective_timezone,
            "quiet_hours": self.quiet_hours,
            "allowed_weekdays": list(self.allowed_weekdays),
            "muted_until": (
                None if self.muted_until is None else self.muted_until.astimezone(UTC).isoformat()
            ),
            "minimum_selected_cards": self.minimum_selected_cards,
            "skip_if_no_today_focus": self.skip_if_no_today_focus,
        }


def normalize_subscription_policy_payload(
    *,
    channel: ChannelType,
    quiet_hours: dict[str, Any] | None,
    policy: dict[str, Any] | None,
    default_timezone: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    raw_policy = dict(policy or {})
    if "quiet_hours" in raw_policy:
        raise ValidationFailedError(
            "subscription policy quiet_hours must be stored in SubscriptionPolicy.quiet_hours, "
            "not inside policy JSON"
        )
    effective_timezone = _resolve_delivery_timezone(raw_policy, default_timezone)
    normalized_quiet_hours = _normalize_quiet_hours_payload(
        quiet_hours,
        fallback_timezone=effective_timezone,
    )
    normalized_policy = _normalize_policy_payload(raw_policy, effective_timezone=effective_timezone)
    normalized_policy.setdefault("timezone", effective_timezone)
    return normalized_quiet_hours, normalized_policy


def normalize_delivery_control_policy(
    policy: SubscriptionPolicy | None,
    *,
    default_timezone: str,
) -> NormalizedDeliveryControlPolicy:
    if policy is None:
        return NormalizedDeliveryControlPolicy(
            channel=ChannelType.OFFICIAL_ACCOUNT,
            enabled=False,
            effective_timezone=default_timezone,
            quiet_hours=None,
            allowed_weekdays=[],
            muted_until=None,
            minimum_selected_cards=None,
            skip_if_no_today_focus=False,
            subscription_policy_id=None,
        )
    normalized_quiet_hours, normalized_policy = normalize_subscription_policy_payload(
        channel=policy.channel,
        quiet_hours=policy.quiet_hours,
        policy=policy.policy,
        default_timezone=default_timezone,
    )
    return NormalizedDeliveryControlPolicy(
        channel=policy.channel,
        enabled=policy.enabled,
        effective_timezone=str(normalized_policy["timezone"]),
        quiet_hours=normalized_quiet_hours,
        allowed_weekdays=list(normalized_policy.get("allowed_weekdays") or []),
        muted_until=_parse_control_datetime(
            normalized_policy.get("muted_until"),
            fallback_timezone=str(normalized_policy["timezone"]),
        ),
        minimum_selected_cards=_coerce_optional_non_negative_int(
            normalized_policy.get("minimum_selected_cards"),
            field_name="minimum_selected_cards",
        ),
        skip_if_no_today_focus=bool(normalized_policy.get("skip_if_no_today_focus") or False),
        subscription_policy_id=policy.id,
    )


def find_matching_delivery_policy(
    policies: list[SubscriptionPolicy],
    *,
    channel: ChannelType,
) -> SubscriptionPolicy | None:
    preferred_channels = [channel]
    if channel == ChannelType.OFFICIAL_ACCOUNT:
        preferred_channels.append(ChannelType.WECHAT)
    for preferred_channel in preferred_channels:
        for policy in policies:
            if policy.channel == preferred_channel:
                return policy
    return None


def _normalize_policy_payload(
    raw_policy: dict[str, Any],
    *,
    effective_timezone: str,
) -> dict[str, Any]:
    normalized = dict(raw_policy)
    normalized["timezone"] = effective_timezone
    if "allowed_weekdays" in normalized:
        normalized["allowed_weekdays"] = _normalize_allowed_weekdays(
            normalized.get("allowed_weekdays")
        )
    if "muted_until" in normalized:
        muted_until = _parse_control_datetime(
            normalized.get("muted_until"),
            fallback_timezone=effective_timezone,
        )
        normalized["muted_until"] = (
            None if muted_until is None else muted_until.astimezone(UTC).isoformat()
        )
    if "minimum_selected_cards" in normalized:
        normalized["minimum_selected_cards"] = _coerce_optional_non_negative_int(
            normalized.get("minimum_selected_cards"),
            field_name="minimum_selected_cards",
        )
    if "skip_if_no_today_focus" in normalized:
        normalized["skip_if_no_today_focus"] = _coerce_optional_bool(
            normalized.get("skip_if_no_today_focus"),
            field_name="skip_if_no_today_focus",
        )
    return normalized


def _resolve_delivery_timezone(raw_policy: dict[str, Any], default_timezone: str) -> str:
    direct_timezone = raw_policy.get("timezone")
    schedule = raw_policy.get("schedule")
    candidate = direct_timezone
    if candidate is None and isinstance(schedule, dict):
        candidate = schedule.get("timezone")
    timezone_name = str(candidate or default_timezone)
    return _validate_timezone_name(timezone_name)


def _normalize_quiet_hours_payload(
    payload: dict[str, Any] | None,
    *,
    fallback_timezone: str,
) -> dict[str, Any] | None:
    if not payload:
        return None
    if not isinstance(payload, dict):
        raise ValidationFailedError("quiet_hours must be a JSON object when provided")
    windows_payload = payload.get("windows")
    windows = windows_payload if isinstance(windows_payload, list) else [payload]
    normalized_windows: list[dict[str, Any]] = []
    for window in windows:
        if not isinstance(window, dict):
            raise ValidationFailedError("quiet_hours windows must be JSON objects")
        start = window.get("start")
        end = window.get("end")
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValidationFailedError("quiet_hours requires start and end times in HH:MM format")
        normalized_windows.append(
            {
                "start": _validate_time_string(start, field_name="quiet_hours.start"),
                "end": _validate_time_string(end, field_name="quiet_hours.end"),
                "timezone": _validate_timezone_name(
                    str(window.get("timezone") or payload.get("timezone") or fallback_timezone)
                ),
            }
        )
    return {
        "timezone": normalized_windows[0]["timezone"],
        "windows": normalized_windows,
    }


def _normalize_allowed_weekdays(value: Any) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationFailedError("allowed_weekdays must be an array of integers from 0 to 6")
    normalized = sorted({int(day) for day in value})
    if any(day < 0 or day > 6 for day in normalized):
        raise ValidationFailedError("allowed_weekdays values must be integers from 0 to 6")
    return normalized


def _parse_control_datetime(
    value: Any,
    *,
    fallback_timezone: str,
) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationFailedError(
                "muted_until must be a valid ISO 8601 datetime string"
            ) from exc
    else:
        raise ValidationFailedError("muted_until must be a datetime string")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_safe_zoneinfo(fallback_timezone))
    return parsed.astimezone(UTC)


def _coerce_optional_non_negative_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationFailedError(f"{field_name} must be an integer when provided") from exc
    if normalized < 0:
        raise ValidationFailedError(f"{field_name} must be greater than or equal to 0")
    return normalized


def _coerce_optional_bool(value: Any, *, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValidationFailedError(f"{field_name} must be a boolean when provided")


def _validate_timezone_name(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValidationFailedError(f"unknown timezone: {value}") from exc
    return value


def _validate_time_string(value: str, *, field_name: str) -> str:
    try:
        normalized = time.fromisoformat(value)
    except ValueError as exc:
        raise ValidationFailedError(f"{field_name} must use HH:MM format") from exc
    return normalized.strftime("%H:%M")


def _safe_zoneinfo(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")
