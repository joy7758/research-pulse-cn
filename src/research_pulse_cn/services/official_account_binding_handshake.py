"""Reserve handshake services for official-account binding reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import ConflictError, NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    OfficialAccountBindingHandshakeSession,
    OfficialAccountCallbackEvent,
    SubscriptionSelfServiceGrant,
    WeChatIdentityBinding,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ChannelType,
    OfficialAccountBindingHandshakeSessionStatus,
    OfficialAccountCallbackProcessingStatus,
    WeChatBindingChannelType,
    WeChatBindingState,
)
from research_pulse_cn.domain.official_account_binding_handshake import (
    IssuedOfficialAccountBindingHandshakeSession,
)
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.subscription_self_service import (
    SubscriptionSelfServiceRepository,
)
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session

SAFE_CALLBACK_EVENT_TYPES = frozenset({"subscribe"})
SAFE_CALLBACK_PROCESSING_STATUSES = frozenset(
    {
        OfficialAccountCallbackProcessingStatus.ACCEPTED,
        OfficialAccountCallbackProcessingStatus.PROCESSED,
    }
)
ACTIVE_HANDSHAKE_SESSION_STATUSES = frozenset(
    {
        OfficialAccountBindingHandshakeSessionStatus.PENDING,
        OfficialAccountBindingHandshakeSessionStatus.MATCHED,
    }
)


class OfficialAccountBindingHandshakeService:
    """Manage reserve handshake sessions and explicit callback-event claims."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.digest_repository = DigestRepository(session)
        self.user_repository = UserRepository(session)
        self.self_service_repository = SubscriptionSelfServiceRepository(session)
        self.metrics = get_metrics()

    def list_sessions(
        self,
        *,
        user_id: UUID | None = None,
        channel: ChannelType | None = None,
        status: OfficialAccountBindingHandshakeSessionStatus | None = None,
        self_service_grant_id: UUID | None = None,
        app_id: str | None = None,
    ) -> list[OfficialAccountBindingHandshakeSession]:
        sessions = self.digest_repository.list_handshake_sessions(
            user_id=user_id,
            channel=channel,
            status=status,
            self_service_grant_id=self_service_grant_id,
            app_id=app_id,
        )
        self._refresh_expired_sessions(sessions)
        return [self._auto_match_session(session) for session in sessions]

    def get_session(self, session_id: UUID) -> OfficialAccountBindingHandshakeSession:
        session = self.digest_repository.get_handshake_session(session_id)
        if session is None:
            raise NotFoundError(
                f"official-account binding handshake session {session_id} was not found"
            )
        self._mark_expired_if_needed(session)
        return self._auto_match_session(session)

    def serialize_session(self, session: OfficialAccountBindingHandshakeSession) -> dict[str, Any]:
        return {
            "id": session.id,
            "user_id": session.user_id,
            "channel": session.channel,
            "app_id": session.app_id,
            "display_label": session.display_label,
            "self_service_grant_id": session.self_service_grant_id,
            "issued_by_admin_id": session.issued_by_admin_id,
            "status": session.status,
            "matched_callback_event_id": session.matched_callback_event_id,
            "claimed_binding_id": session.claimed_binding_id,
            "expires_at": session.expires_at,
            "last_viewed_at": session.last_viewed_at,
            "matched_at": session.matched_at,
            "claimed_at": session.claimed_at,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    def create_session(
        self,
        *,
        user_id: UUID,
        app_id: str | None = None,
        display_label: str | None = None,
        self_service_grant_id: UUID | None = None,
        issued_by_admin_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[
        OfficialAccountBindingHandshakeSession,
        IssuedOfficialAccountBindingHandshakeSession,
    ]:
        user = self._require_user(user_id)
        grant = self._require_self_service_grant(self_service_grant_id, user_id=user_id)
        effective_app_id = self._resolve_app_id(app_id)
        effective_expires_at = expires_at or (
            self.now_provider()
            + timedelta(minutes=self.settings.official_account_binding_handshake_ttl_minutes)
        )
        raw_state_token = generate_refresh_token()
        handshake_session = OfficialAccountBindingHandshakeSession(
            user_id=user.id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
            app_id=effective_app_id,
            display_label=display_label,
            self_service_grant_id=None if grant is None else grant.id,
            issued_by_admin_id=issued_by_admin_id,
            state_token_hash=hash_token(raw_state_token),
            status=OfficialAccountBindingHandshakeSessionStatus.PENDING,
            expires_at=effective_expires_at,
        )
        self.digest_repository.add_handshake_session(handshake_session)
        commit_session(self.session)
        persisted = self.get_session(handshake_session.id)
        self.metrics.increment("official_account_binding_handshake_sessions_created_total")
        return persisted, IssuedOfficialAccountBindingHandshakeSession(
            session_id=persisted.id,
            plain_text_state_token=raw_state_token,
            expires_at=persisted.expires_at,
        )

    def cancel_session(
        self,
        session_id: UUID,
        *,
        user_id: UUID | None = None,
        self_service_grant_id: UUID | None = None,
    ) -> OfficialAccountBindingHandshakeSession:
        session = self.get_session(session_id)
        self._require_session_ownership(
            session,
            user_id=user_id,
            self_service_grant_id=self_service_grant_id,
        )
        if session.status == OfficialAccountBindingHandshakeSessionStatus.CLAIMED:
            raise ConflictError("claimed handshake session cannot be cancelled")
        if session.status in ACTIVE_HANDSHAKE_SESSION_STATUSES:
            session.status = OfficialAccountBindingHandshakeSessionStatus.CANCELLED
            commit_session(self.session)
        return self.get_session(session.id)

    def get_latest_session_for_user(
        self,
        *,
        user_id: UUID,
        app_id: str | None = None,
        self_service_grant_id: UUID | None = None,
        active_only: bool = False,
    ) -> OfficialAccountBindingHandshakeSession | None:
        sessions = self.list_sessions(
            user_id=user_id,
            channel=ChannelType.OFFICIAL_ACCOUNT,
            self_service_grant_id=self_service_grant_id,
            app_id=app_id,
        )
        if active_only:
            sessions = [
                session
                for session in sessions
                if session.status in ACTIVE_HANDSHAKE_SESSION_STATUSES
            ]
        return sessions[0] if sessions else None

    def list_reconciliation_candidates(
        self,
        *,
        app_id: str,
        signature_valid: bool | None = None,
        event_type: str | None = None,
        unmatched_only: bool = True,
    ) -> list[dict[str, Any]]:
        with bind_log_context(app_id=app_id):
            self.metrics.increment("official_account_binding_candidates_listed_total")
            if event_type is not None and event_type not in SAFE_CALLBACK_EVENT_TYPES:
                return []
            effective_signature_valid = signature_valid
            if effective_signature_valid is None and (
                self.settings.official_account_binding_require_signature_valid
            ):
                effective_signature_valid = True
            candidates = self._eligible_callback_candidates(
                app_id=app_id,
                signature_valid=effective_signature_valid,
                unmatched_only=unmatched_only,
            )
            return [self.serialize_candidate(candidate) for candidate in candidates]

    def serialize_candidate(self, event: OfficialAccountCallbackEvent) -> dict[str, Any]:
        notes: list[str] = []
        if not event.signature_valid:
            notes.append("Callback signature was not validated.")
        if event.linked_binding_id is not None:
            notes.append("Callback event is already linked to a binding.")
        if event.from_openid is None:
            notes.append("Callback event did not include an OpenID.")
        return {
            "callback_event_id": event.id,
            "app_id": event.app_id,
            "event_type": event.event_type,
            "event_time": event.event_time,
            "processing_status": event.processing_status,
            "signature_valid": event.signature_valid,
            "masked_openid": self._mask_openid(event.from_openid),
            "created_at": event.created_at,
            "linked_binding_id": event.linked_binding_id,
            "notes": notes,
        }

    def claim_session(
        self,
        session_id: UUID,
        *,
        callback_event_id: UUID | None = None,
    ) -> dict[str, Any]:
        session = self.get_session(session_id)
        self._validate_claimable_session(session)
        event = self._resolve_event_for_claim(session, callback_event_id=callback_event_id)
        event = self._validate_claimable_callback_event(event, app_id=session.app_id)
        current_time = self._coerce_utc(self.now_provider())

        existing_binding = self.digest_repository.get_binding_by_channel_app_openid(
            channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
            app_id=event.app_id or session.app_id,
            openid=event.from_openid or "",
        )
        if existing_binding is not None and existing_binding.user_id != session.user_id:
            self.metrics.increment("official_account_binding_claim_conflicts_total")
            raise ConflictError(
                "official-account callback event is already bound to a different user"
            )

        if existing_binding is None:
            binding = WeChatIdentityBinding(
                user_id=session.user_id,
                channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
                app_id=event.app_id or session.app_id,
                openid=event.from_openid or "",
                unionid=None,
                bind_state=WeChatBindingState.ACTIVE,
                subscribed=True,
                digest_enabled=self.settings.official_account_binding_default_digest_enabled,
                display_label=session.display_label or "Official Account Binding",
                subscribed_at=event.event_time or current_time,
                last_seen_at=event.event_time or current_time,
            )
            binding = self.digest_repository.add_binding(binding)
        else:
            binding = existing_binding
            binding.bind_state = WeChatBindingState.ACTIVE
            binding.subscribed = True
            binding.last_seen_at = event.event_time or current_time
            if binding.subscribed_at is None:
                binding.subscribed_at = event.event_time or current_time
            if session.display_label and not binding.display_label:
                binding.display_label = session.display_label

        event.linked_binding_id = binding.id
        event.processing_status = OfficialAccountCallbackProcessingStatus.PROCESSED
        event.processing_note = "claimed by official-account binding handshake reserve"
        event.processed_at = current_time

        session.matched_callback_event_id = event.id
        session.claimed_binding_id = binding.id
        session.status = OfficialAccountBindingHandshakeSessionStatus.CLAIMED
        session.matched_at = session.matched_at or current_time
        session.claimed_at = current_time
        commit_session(self.session)

        self.metrics.increment("official_account_binding_handshake_sessions_claimed_total")
        return {
            "session": self.serialize_session(self.get_session(session.id)),
            "claimed_binding": self._safe_binding_summary(binding),
            "callback_event": self.serialize_candidate(
                self.digest_repository.get_callback_event(event.id) or event
            ),
        }

    def self_service_bootstrap(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
        binding_id: UUID | None,
    ) -> dict[str, Any]:
        stored_grant = self._require_self_service_grant(grant_id, user_id=user_id)
        user = self._require_user(user_id)
        binding = None if binding_id is None else self.digest_repository.get_binding(binding_id)
        if binding is None:
            binding = self._official_account_binding(user_id)
        session = self.get_latest_session_for_user(
            user_id=user_id,
            self_service_grant_id=grant_id,
            active_only=True,
        )
        candidate_count_hint = None
        effective_app_id = self._handshake_app_id_for_bootstrap(
            grant=stored_grant,
            binding=binding,
            session=session,
        )
        if effective_app_id is not None:
            candidate_count_hint = len(
                self._eligible_callback_candidates(
                    app_id=effective_app_id,
                    unmatched_only=True,
                )
            )
        return {
            "user": self._user_summary(user),
            "binding": self._safe_binding_summary(binding),
            "active_session": (
                None if session is None else self._touch_and_serialize_session_summary(session)
            ),
            "candidate_count_hint": candidate_count_hint,
            "notes": [
                "Real WeChat OAuth completion is not enabled in this phase.",
                "An admin claim step may still be required after "
                "a matching subscribe callback arrives.",
            ],
        }

    def create_self_service_session(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
        app_id: str | None = None,
        display_label: str | None = None,
    ) -> tuple[
        OfficialAccountBindingHandshakeSession,
        IssuedOfficialAccountBindingHandshakeSession,
    ]:
        self._require_self_service_grant(grant_id, user_id=user_id)
        return self.create_session(
            user_id=user_id,
            app_id=app_id,
            display_label=display_label,
            self_service_grant_id=grant_id,
            issued_by_admin_id=None,
        )

    def get_self_service_session(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        self._require_self_service_grant(grant_id, user_id=user_id)
        session = self.get_latest_session_for_user(
            user_id=user_id,
            self_service_grant_id=grant_id,
            active_only=True,
        )
        if session is None:
            return None
        return self._touch_and_serialize_session_summary(session)

    def cancel_self_service_session(
        self,
        *,
        grant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        self._require_self_service_grant(grant_id, user_id=user_id)
        session = self.get_latest_session_for_user(
            user_id=user_id,
            self_service_grant_id=grant_id,
            active_only=True,
        )
        if session is None:
            return None
        cancelled = self.cancel_session(
            session.id,
            user_id=user_id,
            self_service_grant_id=grant_id,
        )
        return self.serialize_session(cancelled)

    def mini_binding_handoff_reserve(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, Any]:
        session = self.get_latest_session_for_user(user_id=user_id, active_only=True)
        return {
            "supported": True,
            "oauth_enabled": False,
            "active_session_status": (
                None
                if session is None or session.status not in ACTIVE_HANDSHAKE_SESSION_STATUSES
                else session.status
            ),
            "separate_self_service_grant_required": True,
            "notes": [
                "Mini remains read-only in this phase.",
                "A separate self-service grant is required to initiate "
                "or inspect handshake reserve state.",
                "Real WeChat OAuth completion is not enabled yet.",
            ],
        }

    def _touch_and_serialize_session_summary(
        self,
        session: OfficialAccountBindingHandshakeSession,
    ) -> dict[str, Any]:
        session.last_viewed_at = self._coerce_utc(self.now_provider())
        commit_session(self.session)
        return self.serialize_session(self.get_session(session.id))

    def _validate_claimable_session(
        self,
        session: OfficialAccountBindingHandshakeSession,
    ) -> None:
        self._mark_expired_if_needed(session)
        if session.status == OfficialAccountBindingHandshakeSessionStatus.CLAIMED:
            raise ConflictError("handshake session has already been claimed")
        if session.status == OfficialAccountBindingHandshakeSessionStatus.CANCELLED:
            raise ConflictError("handshake session has been cancelled")
        if session.status == OfficialAccountBindingHandshakeSessionStatus.EXPIRED:
            raise ConflictError("handshake session has expired")
        if session.status not in ACTIVE_HANDSHAKE_SESSION_STATUSES:
            raise ConflictError("handshake session is not claimable")

    def _resolve_event_for_claim(
        self,
        session: OfficialAccountBindingHandshakeSession,
        *,
        callback_event_id: UUID | None,
    ) -> OfficialAccountCallbackEvent:
        if callback_event_id is not None:
            event = self.digest_repository.get_callback_event(callback_event_id)
            if event is None:
                raise NotFoundError(
                    f"official-account callback event {callback_event_id} was not found"
                )
            return event
        if session.matched_callback_event_id is not None:
            event = self.digest_repository.get_callback_event(session.matched_callback_event_id)
            if event is not None:
                return event
        candidates = self._eligible_callback_candidates(app_id=session.app_id, unmatched_only=True)
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise NotFoundError("no eligible official-account reconciliation candidate was found")
        raise ConflictError(
            "multiple eligible reconciliation candidates require explicit selection"
        )

    def _validate_claimable_callback_event(
        self,
        event: OfficialAccountCallbackEvent,
        *,
        app_id: str,
    ) -> OfficialAccountCallbackEvent:
        if event.app_id != app_id:
            raise ConflictError("callback event app_id does not match handshake session app_id")
        if event.from_openid in (None, ""):
            raise ConflictError("callback event does not contain an OpenID")
        if event.event_type not in SAFE_CALLBACK_EVENT_TYPES:
            raise ConflictError("callback event type is not eligible for binding claim")
        if event.processing_status not in SAFE_CALLBACK_PROCESSING_STATUSES:
            raise ConflictError("callback event processing status is not eligible for claim")
        if event.linked_binding_id is not None:
            linked_binding = self.digest_repository.get_binding(event.linked_binding_id)
            if linked_binding is not None:
                return event
            raise ConflictError("callback event is already linked to another binding")
        if (
            self.settings.official_account_binding_require_signature_valid
            and not event.signature_valid
        ):
            raise ConflictError("callback event signature was not validated")
        return event

    def _eligible_callback_candidates(
        self,
        *,
        app_id: str,
        signature_valid: bool | None = None,
        unmatched_only: bool = True,
    ) -> list[OfficialAccountCallbackEvent]:
        effective_signature_valid = signature_valid
        if effective_signature_valid is None and (
            self.settings.official_account_binding_require_signature_valid
        ):
            effective_signature_valid = True
        created_after = self._coerce_utc(self.now_provider()) - timedelta(
            hours=self.settings.official_account_binding_reconciliation_lookback_hours
        )
        events = self.digest_repository.list_callback_events(
            app_id=app_id,
            event_type="subscribe",
            signature_valid=effective_signature_valid,
            unmatched_only=unmatched_only,
            created_after=created_after,
        )
        candidates: list[OfficialAccountCallbackEvent] = []
        for event in events:
            if event.from_openid in (None, ""):
                continue
            if event.processing_status not in SAFE_CALLBACK_PROCESSING_STATUSES:
                continue
            candidates.append(event)
        return candidates

    def _auto_match_session(
        self,
        session: OfficialAccountBindingHandshakeSession,
    ) -> OfficialAccountBindingHandshakeSession:
        if self._mark_expired_if_needed(session):
            return session
        if session.status not in ACTIVE_HANDSHAKE_SESSION_STATUSES:
            return session
        if session.matched_callback_event_id is not None:
            matched = self.digest_repository.get_callback_event(session.matched_callback_event_id)
            if matched is not None:
                return session
            session.matched_callback_event_id = None
            session.matched_at = None
            session.status = OfficialAccountBindingHandshakeSessionStatus.PENDING
            commit_session(self.session)
        candidates = self._eligible_callback_candidates(app_id=session.app_id, unmatched_only=True)
        if len(candidates) != 1:
            return session
        matched_event = candidates[0]
        session.matched_callback_event_id = matched_event.id
        session.matched_at = self._coerce_utc(self.now_provider())
        session.status = OfficialAccountBindingHandshakeSessionStatus.MATCHED
        commit_session(self.session)
        return self.digest_repository.get_handshake_session(session.id) or session

    def _refresh_expired_sessions(
        self,
        sessions: list[OfficialAccountBindingHandshakeSession],
    ) -> None:
        changed = any(
            self._mark_expired_if_needed(session, auto_commit=False) for session in sessions
        )
        if changed:
            commit_session(self.session)

    def _mark_expired_if_needed(
        self,
        session: OfficialAccountBindingHandshakeSession,
        *,
        auto_commit: bool = True,
    ) -> bool:
        if (
            session.status in ACTIVE_HANDSHAKE_SESSION_STATUSES
            and session.expires_at is not None
            and self._coerce_utc(session.expires_at) <= self._coerce_utc(self.now_provider())
        ):
            session.status = OfficialAccountBindingHandshakeSessionStatus.EXPIRED
            if auto_commit:
                commit_session(self.session)
            return True
        return False

    def _require_user(self, user_id: UUID):
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def _require_self_service_grant(
        self,
        grant_id: UUID | None,
        *,
        user_id: UUID,
    ) -> SubscriptionSelfServiceGrant | None:
        if grant_id is None:
            return None
        grant = self.self_service_repository.get_grant(grant_id)
        if grant is None or grant.user_id != user_id:
            raise NotFoundError(f"subscription self-service grant {grant_id} was not found")
        if grant.channel != ChannelType.OFFICIAL_ACCOUNT:
            raise ConflictError("self-service grant is not scoped to official_account")
        return grant

    def _require_session_ownership(
        self,
        session: OfficialAccountBindingHandshakeSession,
        *,
        user_id: UUID | None,
        self_service_grant_id: UUID | None,
    ) -> None:
        if user_id is not None and session.user_id != user_id:
            raise NotFoundError(
                f"official-account binding handshake session {session.id} was not found"
            )
        if (
            self_service_grant_id is not None
            and session.self_service_grant_id != self_service_grant_id
        ):
            raise NotFoundError(
                f"official-account binding handshake session {session.id} was not found"
            )

    def _resolve_app_id(self, app_id: str | None) -> str:
        effective_app_id = (app_id or self.settings.wechat_official_app_id or "").strip()
        if not effective_app_id:
            raise ValidationFailedError("official-account app_id is required for handshake session")
        return effective_app_id

    def _coerce_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _mask_openid(self, openid: str | None) -> str | None:
        if openid in (None, ""):
            return None
        value = str(openid)
        if len(value) <= 6:
            return "*" * len(value)
        return f"{value[:3]}***{value[-2:]}"

    def _official_account_binding(self, user_id: UUID) -> WeChatIdentityBinding | None:
        bindings = self.digest_repository.list_bindings(
            user_id=user_id,
            channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
        )
        return bindings[0] if bindings else None

    def _safe_binding_summary(self, binding: WeChatIdentityBinding | None) -> dict[str, Any] | None:
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

    def _user_summary(self, user) -> dict[str, Any]:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "field": user.field,
        }

    def _handshake_app_id_for_bootstrap(
        self,
        *,
        grant: SubscriptionSelfServiceGrant | None,
        binding: WeChatIdentityBinding | None,
        session: OfficialAccountBindingHandshakeSession | None,
    ) -> str | None:
        if session is not None:
            return session.app_id
        if binding is not None:
            return binding.app_id
        if grant is not None and grant.binding is not None:
            return grant.binding.app_id
        if self.settings.wechat_official_app_id:
            return self.settings.wechat_official_app_id
        return None
