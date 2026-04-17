"""Short-lived handoff grants bridging mini read-only reserve to editor APIs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
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
from research_pulse_cn.db.models import SubscriptionEditorHandoffGrant, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    SubscriptionEditorHandoffGrantStatus,
    SubscriptionEditorHandoffIssuedBy,
    SubscriptionSelfServiceGrantStatus,
    WeChatBindingChannelType,
)
from research_pulse_cn.domain.mini import MiniGrantContext
from research_pulse_cn.domain.subscription_self_service import (
    IssuedSubscriptionEditorHandoffGrant,
    SubscriptionEditorHandoffGrantContext,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.mini import MiniRepository
from research_pulse_cn.repositories.subscription_editor_handoff import (
    SubscriptionEditorHandoffRepository,
)
from research_pulse_cn.repositories.subscription_self_service import (
    SubscriptionSelfServiceRepository,
)
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.subscription_self_service import (
    SELF_SERVICE_EDITABLE_FIELD_IDS,
    SubscriptionSelfServiceService,
)

SUBSCRIPTION_EDITOR_ENDPOINTS = [
    "/subscription-editor/bootstrap",
    "/subscription-editor/contract",
    "/subscription-editor/settings/preview",
    "/subscription-editor/settings",
]


class SubscriptionEditorHandoffService:
    """Issue and authenticate narrow handoff grants for editor API access."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = SubscriptionEditorHandoffRepository(session)
        self.mini_repository = MiniRepository(session)
        self.self_service_repository = SubscriptionSelfServiceRepository(session)
        self.digest_repository = DigestRepository(session)
        self.user_repository = UserRepository(session)
        self.self_service_service = SubscriptionSelfServiceService(
            session,
            now_provider=self.now_provider,
        )
        self.metrics = get_metrics()

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: SubscriptionEditorHandoffGrantStatus | None = None,
        mini_grant_id: UUID | None = None,
        self_service_grant_id: UUID | None = None,
    ) -> list[SubscriptionEditorHandoffGrant]:
        grants = self.repository.list_grants(
            user_id=user_id,
            channel=channel,
            status=status,
            mini_grant_id=mini_grant_id,
            self_service_grant_id=self_service_grant_id,
        )
        self._refresh_expired_grants(grants)
        return grants

    def get_grant(self, grant_id: UUID) -> SubscriptionEditorHandoffGrant:
        grant = self.repository.get_grant(grant_id)
        if grant is None:
            raise NotFoundError(f"subscription editor handoff grant {grant_id} was not found")
        self._mark_expired_if_needed(grant)
        return grant

    def serialize_grant(self, grant: SubscriptionEditorHandoffGrant) -> dict[str, Any]:
        return {
            "id": grant.id,
            "user_id": grant.user_id,
            "channel": grant.channel,
            "binding_id": grant.binding_id,
            "mini_grant_id": grant.mini_grant_id,
            "self_service_grant_id": grant.self_service_grant_id,
            "status": grant.status,
            "display_label": grant.display_label,
            "issued_by": grant.issued_by,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def serialize_self_service_grant_summary(self, grant) -> dict[str, Any] | None:
        if grant is None:
            return None
        return {
            "id": grant.id,
            "channel": grant.channel,
            "binding_id": grant.binding_id,
            "status": grant.status,
            "display_label": grant.display_label,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "created_at": grant.created_at,
        }

    def create_handoff_from_mini(
        self,
        mini_grant: MiniGrantContext,
    ) -> tuple[SubscriptionEditorHandoffGrant, IssuedSubscriptionEditorHandoffGrant]:
        self._require_handoff_enabled()
        if mini_grant.user_id is None:
            raise ValidationFailedError("mini grant user context is required for editor handoff")

        with bind_log_context(mini_grant_id=mini_grant.grant_id, user_id=mini_grant.user_id):
            self._require_user(mini_grant.user_id)
            self._require_mini_grant(mini_grant.grant_id, user_id=mini_grant.user_id)
            self_service_grant = self._resolve_source_self_service_grant(mini_grant.user_id)
            binding = self._resolve_channel_binding(
                user_id=mini_grant.user_id,
                preferred_binding_id=self_service_grant.binding_id,
            )
            effective_expires_at = self.now_provider() + timedelta(
                minutes=self.settings.subscription_editor_handoff_ttl_minutes
            )
            raw_token = generate_refresh_token()
            handoff_grant = SubscriptionEditorHandoffGrant(
                user_id=mini_grant.user_id,
                channel=ChannelType.OFFICIAL_ACCOUNT,
                mini_grant_id=mini_grant.grant_id,
                self_service_grant_id=self_service_grant.id,
                binding_id=None if binding is None else binding.id,
                token_hash=hash_token(raw_token),
                status=SubscriptionEditorHandoffGrantStatus.ACTIVE,
                display_label="Mini editor handoff",
                issued_by=SubscriptionEditorHandoffIssuedBy.MINI_HANDOFF,
                issued_by_admin_id=None,
                expires_at=effective_expires_at,
            )
            self.repository.add_grant(handoff_grant)
            commit_session(self.session)
            persisted = self.get_grant(handoff_grant.id)
            self.metrics.increment("subscription_editor_handoff_grants_issued_total")
            return persisted, IssuedSubscriptionEditorHandoffGrant(
                grant_id=persisted.id,
                plain_text_token=raw_token,
                expires_at=persisted.expires_at,
            )

    def get_handoff_status_for_mini(self, mini_grant: MiniGrantContext) -> dict[str, Any]:
        with bind_log_context(mini_grant_id=mini_grant.grant_id, user_id=mini_grant.user_id):
            latest = self._latest_grant_for_mini(
                mini_grant_id=mini_grant.grant_id,
                user_id=mini_grant.user_id,
            )
            linked_self_service_grant = None
            linked_binding = None
            if latest is not None:
                linked_self_service_grant = self._refresh_linked_self_service_grant(latest)
                linked_binding = latest.binding
                if linked_binding is None and linked_self_service_grant is not None:
                    linked_binding = linked_self_service_grant.binding
            else:
                linked_self_service_grant = self._find_existing_self_service_grant(
                    mini_grant.user_id,
                    require_active=self.settings.subscription_editor_handoff_require_active_self_service_grant,
                )
                linked_binding = self._resolve_channel_binding(
                    user_id=mini_grant.user_id,
                    preferred_binding_id=(
                        None
                        if linked_self_service_grant is None
                        else linked_self_service_grant.binding_id
                    ),
                    require_when_enabled=False,
                )
            return {
                "handoff_grant": (None if latest is None else self.serialize_grant(latest)),
                "linked_self_service_grant": self.serialize_self_service_grant_summary(
                    linked_self_service_grant
                ),
                "linked_binding": self.self_service_service.safe_binding_summary(linked_binding),
                "supported_editor_endpoints": list(SUBSCRIPTION_EDITOR_ENDPOINTS),
                "notes": [
                    "Mini can mint only a short-lived editor handoff token in this phase.",
                    "Mini read grants still cannot call editor endpoints directly.",
                ],
            }

    def mini_editor_handoff_reserve(
        self,
        *,
        mini_grant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        latest = self._latest_grant_for_mini(mini_grant_id=mini_grant_id, user_id=user_id)
        notes: list[str] = []
        if not self.settings.subscription_editor_handoff_enabled:
            notes.append("Mini editor handoff is disabled.")
        elif self.settings.subscription_editor_handoff_require_active_self_service_grant:
            notes.append(
                "An active self-service grant is required before mini can mint an "
                "editor handoff token."
            )
        else:
            notes.append(
                "A previously issued self-service grant is required before mini can "
                "mint an editor handoff token."
            )
        if self.settings.subscription_editor_handoff_require_channel_binding:
            notes.append(
                "An official-account binding must exist before mini editor handoff is allowed."
            )
        return {
            "supported": True,
            "enabled": self.settings.subscription_editor_handoff_enabled,
            "editable_via_current_mini_grant": False,
            "handoff_grant_required": True,
            "active_handoff_status": None if latest is None else latest.status,
            "supported_editor_endpoints": list(SUBSCRIPTION_EDITOR_ENDPOINTS),
            "supported_editable_fields": list(SELF_SERVICE_EDITABLE_FIELD_IDS),
            "notes": notes,
        }

    def authenticate_grant_token(self, raw_token: str) -> SubscriptionEditorHandoffGrantContext:
        grant = self.repository.get_grant_by_token_hash(hash_token(raw_token))
        if grant is None:
            raise AuthenticationError("subscription editor handoff grant was not found")
        now = self.now_provider()
        if grant.status == SubscriptionEditorHandoffGrantStatus.REVOKED:
            raise AuthenticationError("subscription editor handoff grant has been revoked")
        if grant.status == SubscriptionEditorHandoffGrantStatus.EXPIRED:
            raise AuthenticationError("subscription editor handoff grant has expired")
        if self._mark_expired_if_needed(grant, now=now):
            raise AuthenticationError("subscription editor handoff grant has expired")
        linked_self_service_grant = self._refresh_linked_self_service_grant(grant)
        if (
            self.settings.subscription_editor_handoff_require_active_self_service_grant
            and linked_self_service_grant.status != SubscriptionSelfServiceGrantStatus.ACTIVE
        ):
            raise AuthenticationError(
                "subscription editor handoff grant requires an active self-service grant"
            )
        grant.last_used_at = now
        commit_session(self.session)
        return SubscriptionEditorHandoffGrantContext(
            grant_id=grant.id,
            user_id=grant.user_id,
            binding_id=grant.binding_id,
            mini_grant_id=grant.mini_grant_id,
            self_service_grant_id=grant.self_service_grant_id,
            self_service_grant_status=linked_self_service_grant.status,
            channel=grant.channel,
            status=grant.status,
            issued_by=grant.issued_by,
            display_label=grant.display_label,
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def revoke_grant(self, grant_id: UUID) -> SubscriptionEditorHandoffGrant:
        grant = self.get_grant(grant_id)
        if grant.status != SubscriptionEditorHandoffGrantStatus.REVOKED:
            grant.status = SubscriptionEditorHandoffGrantStatus.REVOKED
            commit_session(self.session)
            self.metrics.increment("subscription_editor_handoff_grants_revoked_total")
        return self.get_grant(grant_id)

    def get_editor_bootstrap(self, grant: SubscriptionEditorHandoffGrantContext) -> dict[str, Any]:
        with bind_log_context(
            subscription_editor_handoff_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            self.metrics.increment("subscription_editor_handoff_bootstrap_requests_total")
            stored = self.get_grant(grant.grant_id)
            user = self._require_user(grant.user_id)
            current_policy = self.self_service_service.current_official_account_policy_for_user(
                grant.user_id
            )
            latest_issue = self.self_service_service.latest_digest_issue_for_user(grant.user_id)
            binding = stored.binding
            if binding is None and stored.self_service_grant is not None:
                binding = stored.self_service_grant.binding
            return {
                "contract_version": self.self_service_service.editor_contract_payload()[
                    "contract_version"
                ],
                "handoff_grant": self.serialize_grant(stored),
                "linked_self_service_grant": self.serialize_self_service_grant_summary(
                    self._refresh_linked_self_service_grant(stored)
                ),
                "user": self.self_service_service.user_summary(user),
                "official_account_binding_summary": self.self_service_service.safe_binding_summary(
                    binding
                ),
                "current_settings_draft": self.self_service_service.settings_draft_payload(
                    current_policy,
                    grant_status=grant.self_service_grant_status,
                ),
                "latest_digest_summary": self.self_service_service.latest_digest_issue_summary(
                    latest_issue
                ),
                "authoritative_preview_supported": True,
                "supported_editor_endpoints": list(SUBSCRIPTION_EDITOR_ENDPOINTS),
                "notes": [
                    "This bootstrap is accessed through a short-lived editor handoff token.",
                    "Underlying settings preview and save logic is shared with "
                    "self-service editor reserve.",
                ],
            }

    def get_editor_contract(self) -> dict[str, Any]:
        return self.self_service_service.editor_contract_payload()

    def preview_settings(
        self,
        grant: SubscriptionEditorHandoffGrantContext,
        *,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with bind_log_context(
            subscription_editor_handoff_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            return self.self_service_service.preview_editor_settings(
                user_id=grant.user_id,
                grant_status=grant.self_service_grant_status,
                payload=payload,
            )

    def patch_settings(
        self,
        grant: SubscriptionEditorHandoffGrantContext,
        *,
        enabled=None,
        quiet_hours=None,
        timezone=None,
        allowed_weekdays=None,
        muted_until=None,
        minimum_selected_cards=None,
        skip_if_no_today_focus=None,
        update_fields: set[str] | None = None,
        include_preview: bool = False,
    ) -> dict[str, Any]:
        with bind_log_context(
            subscription_editor_handoff_grant_id=grant.grant_id,
            user_id=grant.user_id,
        ):
            result = self.self_service_service.patch_editor_settings(
                user_id=grant.user_id,
                grant_status=grant.self_service_grant_status,
                enabled=enabled,
                quiet_hours=quiet_hours,
                timezone=timezone,
                allowed_weekdays=allowed_weekdays,
                muted_until=muted_until,
                minimum_selected_cards=minimum_selected_cards,
                skip_if_no_today_focus=skip_if_no_today_focus,
                update_fields=update_fields,
                include_preview=include_preview,
            )
            self.metrics.increment("subscription_editor_handoff_settings_saved_total")
            return result

    def _require_handoff_enabled(self) -> None:
        if not self.settings.subscription_editor_handoff_enabled:
            raise ValidationFailedError("subscription editor handoff is disabled")

    def _require_user(self, user_id: UUID):
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def _require_mini_grant(self, grant_id: UUID, *, user_id: UUID):
        grant = self.mini_repository.get_grant(grant_id)
        if grant is None or grant.user_id != user_id:
            raise NotFoundError(f"mini read grant {grant_id} was not found")
        return grant

    def _resolve_source_self_service_grant(self, user_id: UUID):
        grant = self._find_existing_self_service_grant(
            user_id,
            require_active=self.settings.subscription_editor_handoff_require_active_self_service_grant,
        )
        if grant is None:
            if self.settings.subscription_editor_handoff_require_active_self_service_grant:
                raise ValidationFailedError(
                    "an active self-service grant is required before mini editor "
                    "handoff can be created"
                )
            raise ValidationFailedError(
                "a self-service grant is required before mini editor handoff can be created"
            )
        return grant

    def _find_existing_self_service_grant(
        self,
        user_id: UUID,
        *,
        require_active: bool,
    ):
        now = self.now_provider()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if require_active:
            grants = self.self_service_repository.list_active_grants(
                user_id=user_id,
                channel=ChannelType.OFFICIAL_ACCOUNT,
                as_of=now,
            )
            return grants[0] if grants else None
        grants = self.self_service_repository.list_grants(
            user_id=user_id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
        )
        return grants[0] if grants else None

    def _resolve_channel_binding(
        self,
        *,
        user_id: UUID,
        preferred_binding_id: UUID | None,
        require_when_enabled: bool = True,
    ):
        binding = None
        if preferred_binding_id is not None:
            binding = self.digest_repository.get_binding(preferred_binding_id)
            if binding is not None and binding.user_id != user_id:
                binding = None
        if binding is None:
            bindings = self.digest_repository.list_bindings(
                user_id=user_id,
                channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
            )
            binding = bindings[0] if bindings else None
        if (
            require_when_enabled
            and self.settings.subscription_editor_handoff_require_channel_binding
            and binding is None
        ):
            raise ValidationFailedError(
                "an official-account binding is required before mini editor handoff can be created"
            )
        return binding

    def _refresh_linked_self_service_grant(self, grant: SubscriptionEditorHandoffGrant):
        return self.self_service_service.get_grant(grant.self_service_grant_id)

    def _latest_grant_for_mini(
        self,
        *,
        mini_grant_id: UUID,
        user_id: UUID,
    ) -> SubscriptionEditorHandoffGrant | None:
        grants = self.list_grants(
            user_id=user_id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
            mini_grant_id=mini_grant_id,
        )
        return grants[0] if grants else None

    def _refresh_expired_grants(self, grants: list[SubscriptionEditorHandoffGrant]) -> None:
        changed = any(self._mark_expired_if_needed(grant, auto_commit=False) for grant in grants)
        if changed:
            commit_session(self.session)

    def _mark_expired_if_needed(
        self,
        grant: SubscriptionEditorHandoffGrant,
        *,
        now: datetime | None = None,
        auto_commit: bool = True,
    ) -> bool:
        current_time = self.now_provider() if now is None else now
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)
        if (
            grant.status == SubscriptionEditorHandoffGrantStatus.ACTIVE
            and grant.expires_at is not None
            and self._coerce_utc(grant.expires_at) <= self._coerce_utc(current_time)
        ):
            grant.status = SubscriptionEditorHandoffGrantStatus.EXPIRED
            if auto_commit:
                commit_session(self.session)
            return True
        return False

    def _coerce_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
