"""Self-service reserve boundary for user-facing subscription controls."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import (
    AuthenticationError,
    NotFoundError,
    ValidationFailedError,
)
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import PulseDigestIssue, SubscriptionSelfServiceGrant, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    PulseDigestIssueStatus,
    SubscriptionFrequency,
    SubscriptionSelfServiceGrantStatus,
)
from research_pulse_cn.domain.subscription_self_service import (
    IssuedSubscriptionSelfServiceGrant,
    SubscriptionSelfServiceGrantContext,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.subscription_self_service import (
    SubscriptionSelfServiceRepository,
)
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.subscription_policy import (
    SubscriptionPolicyCreate,
    SubscriptionPolicyUpdate,
)
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.subscription_policy import (
    SubscriptionPolicyService,
    find_matching_delivery_policy,
    normalize_delivery_control_policy,
)

SAFE_SELF_SERVICE_POLICY_KEYS = frozenset(
    {
        "timezone",
        "allowed_weekdays",
        "muted_until",
        "minimum_selected_cards",
        "skip_if_no_today_focus",
    }
)


class SubscriptionSelfServiceService:
    """Issue narrow self-service grants and expose safe subscription controls."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = SubscriptionSelfServiceRepository(session)
        self.user_repository = UserRepository(session)
        self.digest_repository = DigestRepository(session)
        self.subscription_policy_repository = SubscriptionPolicyRepository(session)
        self.subscription_policy_service = SubscriptionPolicyService(session)
        self.digest_service = DigestService(session, now_provider=self.now_provider)
        self.metrics = get_metrics()

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: SubscriptionSelfServiceGrantStatus | None = None,
        binding_id: UUID | None = None,
    ) -> list[SubscriptionSelfServiceGrant]:
        grants = self.repository.list_grants(
            user_id=user_id,
            channel=channel,
            status=status,
            binding_id=binding_id,
        )
        self._refresh_expired_grants(grants)
        return grants

    def get_grant(self, grant_id: UUID) -> SubscriptionSelfServiceGrant:
        grant = self.repository.get_grant(grant_id)
        if grant is None:
            raise NotFoundError(f"subscription self-service grant {grant_id} was not found")
        self._mark_expired_if_needed(grant)
        return grant

    def serialize_grant(self, grant: SubscriptionSelfServiceGrant) -> dict:
        return {
            "id": grant.id,
            "user_id": grant.user_id,
            "binding_id": grant.binding_id,
            "channel": grant.channel,
            "grant_scope": dict(grant.grant_scope_json or {}),
            "status": grant.status,
            "display_label": grant.display_label,
            "issued_by_admin_id": grant.issued_by_admin_id,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def create_grant(
        self,
        *,
        user_id: UUID,
        channel: ChannelType,
        issued_by_admin_id: UUID | None,
        binding_id: UUID | None = None,
        grant_scope: dict | None = None,
        display_label: str | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[SubscriptionSelfServiceGrant, IssuedSubscriptionSelfServiceGrant]:
        self._require_channel(channel)
        self._require_user(user_id)
        binding = None if binding_id is None else self.digest_repository.get_binding(binding_id)
        if binding_id is not None and (binding is None or binding.user_id != user_id):
            raise NotFoundError(f"wechat binding {binding_id} was not found")

        raw_token = generate_refresh_token()
        grant = SubscriptionSelfServiceGrant(
            user_id=user_id,
            binding_id=None if binding is None else binding.id,
            channel=channel,
            grant_scope_json=dict(grant_scope or {}) or None,
            token_hash=hash_token(raw_token),
            status=SubscriptionSelfServiceGrantStatus.ACTIVE,
            display_label=display_label,
            issued_by_admin_id=issued_by_admin_id,
            expires_at=expires_at,
        )
        self.repository.add_grant(grant)
        commit_session(self.session)
        persisted = self.get_grant(grant.id)
        self.metrics.increment("subscription_self_service_grants_issued_total")
        return persisted, IssuedSubscriptionSelfServiceGrant(
            grant_id=persisted.id,
            plain_text_token=raw_token,
            expires_at=persisted.expires_at,
        )

    def revoke_grant(self, grant_id: UUID) -> SubscriptionSelfServiceGrant:
        grant = self.get_grant(grant_id)
        if grant.status != SubscriptionSelfServiceGrantStatus.REVOKED:
            grant.status = SubscriptionSelfServiceGrantStatus.REVOKED
            commit_session(self.session)
        return self.get_grant(grant_id)

    def authenticate_grant_token(self, raw_token: str) -> SubscriptionSelfServiceGrantContext:
        grant = self.repository.get_grant_by_token_hash(hash_token(raw_token))
        if grant is None:
            raise AuthenticationError("subscription self-service grant was not found")
        now = self.now_provider()
        if grant.status == SubscriptionSelfServiceGrantStatus.REVOKED:
            raise AuthenticationError("subscription self-service grant has been revoked")
        if grant.status == SubscriptionSelfServiceGrantStatus.EXPIRED:
            raise AuthenticationError("subscription self-service grant has expired")
        if self._mark_expired_if_needed(grant, now=now):
            raise AuthenticationError("subscription self-service grant has expired")
        grant.last_used_at = now
        commit_session(self.session)
        return SubscriptionSelfServiceGrantContext(
            grant_id=grant.id,
            user_id=grant.user_id,
            binding_id=grant.binding_id,
            channel=grant.channel,
            status=grant.status,
            grant_scope=dict(grant.grant_scope_json or {}),
            display_label=grant.display_label,
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def bootstrap(self, grant: SubscriptionSelfServiceGrantContext) -> dict:
        with bind_log_context(
            subscription_self_service_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            self.metrics.increment("subscription_self_service_bootstrap_requests_total")
            stored = self.get_grant(grant.grant_id)
            user = self._require_user(grant.user_id)
            latest_issue = self._latest_digest_issue(grant.user_id)
            return {
                "grant": self._serialize_grant_summary(stored),
                "user": self._user_summary(user),
                "binding": self._safe_binding_summary(stored.binding),
                "subscription_settings": self._settings_payload(
                    self._current_official_account_policy(grant.user_id)
                ),
                "latest_digest_issue": self._latest_digest_issue_summary(latest_issue),
            }

    def get_settings(self, grant: SubscriptionSelfServiceGrantContext) -> dict:
        with bind_log_context(
            subscription_self_service_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            policy = self._current_official_account_policy(grant.user_id)
            return self._settings_payload(policy)

    def patch_settings(
        self,
        grant: SubscriptionSelfServiceGrantContext,
        *,
        enabled: bool | None = None,
        quiet_hours: dict | None = None,
        timezone: str | None = None,
        allowed_weekdays: list[int] | None = None,
        muted_until: datetime | None = None,
        minimum_selected_cards: int | None = None,
        skip_if_no_today_focus: bool | None = None,
        update_fields: set[str] | None = None,
    ) -> dict:
        with bind_log_context(
            subscription_self_service_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            current_policy = self._current_official_account_policy(grant.user_id)
            explicit_fields = update_fields or set()
            merged_policy = dict(
                (current_policy.policy or {}) if current_policy is not None else {}
            )

            self._apply_supported_policy_field(
                merged_policy,
                field_name="timezone",
                value=timezone,
                explicit_fields=explicit_fields,
            )
            self._apply_supported_policy_field(
                merged_policy,
                field_name="allowed_weekdays",
                value=allowed_weekdays,
                explicit_fields=explicit_fields,
            )
            self._apply_supported_policy_field(
                merged_policy,
                field_name="muted_until",
                value=muted_until,
                explicit_fields=explicit_fields,
            )
            self._apply_supported_policy_field(
                merged_policy,
                field_name="minimum_selected_cards",
                value=minimum_selected_cards,
                explicit_fields=explicit_fields,
            )
            self._apply_supported_policy_field(
                merged_policy,
                field_name="skip_if_no_today_focus",
                value=skip_if_no_today_focus,
                explicit_fields=explicit_fields,
            )

            if current_policy is None:
                create_payload = SubscriptionPolicyCreate(
                    user_id=grant.user_id,
                    channel=ChannelType.OFFICIAL_ACCOUNT,
                    enabled=True if "enabled" not in explicit_fields else bool(enabled),
                    frequency=SubscriptionFrequency.DAILY,
                    quiet_hours=quiet_hours if "quiet_hours" in explicit_fields else None,
                    frequency_cap=3,
                    endpoint=None,
                    policy=merged_policy,
                )
                policy = self.subscription_policy_service.create_policy(create_payload)
            else:
                update_payload_data: dict[str, object] = {}
                if "enabled" in explicit_fields:
                    update_payload_data["enabled"] = enabled
                if "quiet_hours" in explicit_fields:
                    update_payload_data["quiet_hours"] = quiet_hours
                if self._policy_fields_touched(explicit_fields):
                    update_payload_data["policy"] = merged_policy
                update_payload = SubscriptionPolicyUpdate(**update_payload_data)
                policy = self.subscription_policy_service.update_policy(
                    current_policy.id,
                    update_payload,
                )

            self.metrics.increment("subscription_self_service_settings_updated_total")
            return self._settings_payload(policy)

    def get_delivery_control_preview(self, grant: SubscriptionSelfServiceGrantContext) -> dict:
        with bind_log_context(
            subscription_self_service_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            self.metrics.increment("subscription_self_service_delivery_previews_total")
            latest_issue = self._latest_digest_issue(grant.user_id)
            current_time = self.now_provider()
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=UTC)

            if latest_issue is not None:
                preview = self.digest_service.get_delivery_control_preview(
                    latest_issue.id,
                    channel=ChannelType.OFFICIAL_ACCOUNT,
                    now=current_time,
                )
            else:
                preview = self.digest_service.evaluate_delivery_control_for_issue(
                    self._synthetic_empty_digest_issue(user_id=grant.user_id, now=current_time),
                    channel=ChannelType.OFFICIAL_ACCOUNT,
                    now=current_time,
                )

            return {
                "decision": preview.decision,
                "reason_codes": list(preview.reason_codes),
                "normalized_control_policy": dict(preview.normalized_control_policy),
                "current_local_time": preview.current_local_time,
                "local_weekday": preview.local_weekday,
                "next_allowed_at": preview.next_allowed_at,
                "latest_digest_issue": self._latest_digest_issue_summary(latest_issue),
            }

    def _require_channel(self, channel: ChannelType) -> None:
        if channel != ChannelType.OFFICIAL_ACCOUNT:
            raise ValidationFailedError(
                "subscription self-service reserve currently supports official_account only"
            )

    def _require_user(self, user_id: UUID):
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def _refresh_expired_grants(self, grants: list[SubscriptionSelfServiceGrant]) -> None:
        changed = any(self._mark_expired_if_needed(grant, auto_commit=False) for grant in grants)
        if changed:
            commit_session(self.session)

    def _mark_expired_if_needed(
        self,
        grant: SubscriptionSelfServiceGrant,
        *,
        now: datetime | None = None,
        auto_commit: bool = True,
    ) -> bool:
        current_time = self.now_provider() if now is None else now
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        if (
            grant.status == SubscriptionSelfServiceGrantStatus.ACTIVE
            and grant.expires_at is not None
            and self._coerce_utc(grant.expires_at) <= self._coerce_utc(current_time)
        ):
            grant.status = SubscriptionSelfServiceGrantStatus.EXPIRED
            if auto_commit:
                commit_session(self.session)
            return True
        return False

    def _coerce_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _current_official_account_policy(self, user_id: UUID):
        policies = self.subscription_policy_repository.list(user_id=user_id)
        return find_matching_delivery_policy(policies, channel=ChannelType.OFFICIAL_ACCOUNT)

    def _settings_payload(self, policy) -> dict:
        normalized = normalize_delivery_control_policy(
            policy,
            default_timezone=self.settings.default_timezone,
        )
        return {
            "subscription_policy_id": None if policy is None else policy.id,
            "user_id": None if policy is None else policy.user_id,
            "channel": ChannelType.OFFICIAL_ACCOUNT,
            "enabled": False if policy is None else policy.enabled,
            "quiet_hours": normalized.quiet_hours,
            "timezone": normalized.effective_timezone,
            "allowed_weekdays": list(normalized.allowed_weekdays),
            "muted_until": normalized.muted_until,
            "minimum_selected_cards": normalized.minimum_selected_cards,
            "skip_if_no_today_focus": normalized.skip_if_no_today_focus,
            "updated_at": None if policy is None else policy.updated_at,
        }

    def _apply_supported_policy_field(
        self,
        payload: dict,
        *,
        field_name: str,
        value,
        explicit_fields: set[str],
    ) -> None:
        if field_name not in explicit_fields:
            return
        if value is None:
            payload.pop(field_name, None)
            return
        if isinstance(value, datetime):
            payload[field_name] = value.astimezone(UTC).isoformat()
            return
        payload[field_name] = value

    def _policy_fields_touched(self, explicit_fields: set[str]) -> bool:
        return any(field in explicit_fields for field in SAFE_SELF_SERVICE_POLICY_KEYS)

    def _latest_digest_issue(self, user_id: UUID):
        issues = self.digest_service.list_digest_issues(user_id=user_id)
        return issues[0] if issues else None

    def _latest_digest_issue_summary(self, issue: PulseDigestIssue | None) -> dict | None:
        if issue is None:
            return None
        return {
            "id": issue.id,
            "issue_date": issue.issue_date,
            "status": issue.status,
            "title": issue.title,
            "summary": issue.summary,
            "selected_card_count": issue.selected_card_count,
            "deep_link_path": issue.deep_link_path,
        }

    def _serialize_grant_summary(self, grant: SubscriptionSelfServiceGrant) -> dict:
        return {
            "id": grant.id,
            "channel": grant.channel,
            "binding_id": grant.binding_id,
            "grant_scope": dict(grant.grant_scope_json or {}),
            "status": grant.status,
            "display_label": grant.display_label,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "created_at": grant.created_at,
        }

    def _safe_binding_summary(self, binding) -> dict | None:
        if binding is None:
            return None
        return {
            "id": binding.id,
            "channel_type": binding.channel_type,
            "app_id": binding.app_id,
            "display_label": binding.display_label,
            "bind_state": binding.bind_state,
            "subscribed": binding.subscribed,
            "digest_enabled": binding.digest_enabled,
            "subscribed_at": binding.subscribed_at,
            "unsubscribed_at": binding.unsubscribed_at,
            "last_seen_at": binding.last_seen_at,
        }

    def _user_summary(self, user) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "field": user.field,
        }

    def _synthetic_empty_digest_issue(
        self,
        *,
        user_id: UUID,
        now: datetime,
    ) -> PulseDigestIssue:
        return PulseDigestIssue(
            user_id=user_id,
            issue_date=now.date(),
            status=PulseDigestIssueStatus.SKIPPED,
            title="No digest issue is available yet",
            summary="No digest issue is available yet for delivery preview.",
            highlight_count=0,
            selected_card_count=0,
            deep_link_path=None,
            content_payload={},
            build_metadata=None,
            published_at=None,
        )
