"""Device lifecycle, token auth, and incremental sync service."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    ClientAccessToken,
    ClientDevice,
    SyncCursor,
    SyncMutation,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    ClientType,
    SyncEventSource,
    SyncMutationStatus,
    WorkActivitySource,
    WorkActivityType,
)
from research_pulse_cn.domain.sync import DeviceContext, IssuedClientDeviceToken
from research_pulse_cn.repositories.sync import SyncRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.paper import PaperProfileUpdate, ProgressEventCreate
from research_pulse_cn.schemas.subscription_policy import SubscriptionPolicyUpdate
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.paper import PaperService
from research_pulse_cn.services.subscription_policy import SubscriptionPolicyService
from research_pulse_cn.services.sync_events import SyncEventService
from research_pulse_cn.services.work_activity import WorkActivityService

logger = logging.getLogger(__name__)


class SyncService:
    """Manage client devices and the sync feed/mutation pipeline."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.repository = SyncRepository(session)
        self.user_repository = UserRepository(session)
        self.sync_event_service = SyncEventService(session)
        self.metrics = get_metrics()

    def list_devices(
        self,
        *,
        user_id: UUID | None = None,
        client_type: ClientType | None = None,
        is_active: bool | None = None,
    ) -> list[ClientDevice]:
        return self.repository.list_devices(
            user_id=user_id,
            client_type=client_type,
            is_active=is_active,
        )

    def create_device(
        self,
        *,
        user_id: UUID,
        client_type: ClientType,
        display_name: str,
        created_ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[ClientDevice, IssuedClientDeviceToken]:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")

        device = ClientDevice(
            user_id=user_id,
            client_type=client_type,
            display_name=display_name,
            is_active=True,
        )
        self.repository.add_device(device)
        self.repository.add_cursor(SyncCursor(client_device_id=device.id, last_event_sequence=0))
        issued_token = self._issue_device_token(
            client_device=device,
            created_ip=created_ip,
            user_agent=user_agent,
        )
        commit_session(self.session)
        return self.repository.get_device(device.id) or device, issued_token

    def rotate_device_token(
        self,
        client_device_id: UUID,
        *,
        created_ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[ClientDevice, IssuedClientDeviceToken]:
        device = self.get_device(client_device_id)
        if not device.is_active:
            raise ConflictError("inactive devices cannot rotate tokens")
        self._revoke_active_tokens(device.id, now=utcnow())
        issued_token = self._issue_device_token(
            client_device=device,
            created_ip=created_ip,
            user_agent=user_agent,
        )
        commit_session(self.session)
        return self.repository.get_device(device.id) or device, issued_token

    def revoke_device(self, client_device_id: UUID) -> ClientDevice:
        device = self.get_device(client_device_id)
        now = utcnow()
        device.is_active = False
        device.last_seen_at = now
        self._revoke_active_tokens(device.id, now=now)
        commit_session(self.session)
        return self.repository.get_device(device.id) or device

    def get_device(self, client_device_id: UUID) -> ClientDevice:
        device = self.repository.get_device(client_device_id)
        if device is None:
            raise NotFoundError(f"client device {client_device_id} was not found")
        return device

    def authenticate_device_token(self, raw_token: str) -> DeviceContext:
        token_row = self.repository.get_access_token_by_hash(hash_token(raw_token))
        if token_row is None:
            raise AuthenticationError("device token was not found")
        device = token_row.client_device
        if not device.is_active:
            raise AuthenticationError("client device is inactive")
        if token_row.revoked_at is not None:
            raise AuthenticationError("device token has been revoked")
        if token_row.expires_at is not None and _coerce_utc(token_row.expires_at) <= utcnow():
            raise AuthenticationError("device token has expired")

        now = utcnow()
        token_row.last_used_at = now
        device.last_seen_at = now
        commit_session(self.session)
        return DeviceContext(
            client_device_id=device.id,
            user_id=device.user_id,
            client_type=device.client_type,
            display_name=device.display_name,
            token_id=token_row.id,
            is_active=device.is_active,
        )

    def get_sync_me(self, device: DeviceContext) -> dict:
        stored_device = self.get_device(device.client_device_id)
        user = stored_device.user
        cursor = stored_device.cursor or self.repository.add_cursor(
            SyncCursor(client_device_id=stored_device.id, last_event_sequence=0)
        )
        commit_session(self.session)
        return {
            "device": {
                "id": stored_device.id,
                "user_id": stored_device.user_id,
                "client_type": stored_device.client_type,
                "display_name": stored_device.display_name,
                "is_active": stored_device.is_active,
                "last_seen_at": stored_device.last_seen_at,
                "created_at": stored_device.created_at,
                "updated_at": stored_device.updated_at,
                "last_event_sequence": cursor.last_event_sequence,
                "last_synced_at": cursor.last_synced_at,
            },
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "field": user.field,
            },
        }

    def feed(
        self,
        device: DeviceContext,
        *,
        after_sequence: int | None = None,
        limit: int | None = None,
    ) -> dict:
        with bind_log_context(client_device_id=device.client_device_id, user_id=device.user_id):
            stored_device = self.get_device(device.client_device_id)
            cursor = stored_device.cursor or self.repository.add_cursor(
                SyncCursor(client_device_id=stored_device.id, last_event_sequence=0)
            )
            effective_after = (
                cursor.last_event_sequence if after_sequence is None else after_sequence
            )
            effective_limit = self._resolve_feed_limit(limit)
            events = self.repository.list_events_after(
                user_id=device.user_id,
                after_sequence=effective_after,
                limit=effective_limit + 1,
            )
            has_more = len(events) > effective_limit
            returned_events = events[:effective_limit]
            next_after_sequence = (
                returned_events[-1].sequence if returned_events else effective_after
            )
            self.metrics.increment("sync_feed_requests_total")
            logger.info(
                "sync feed served",
                extra={
                    "returned_events": len(returned_events),
                    "after_sequence": effective_after,
                },
            )
            return {
                "events": returned_events,
                "next_after_sequence": next_after_sequence,
                "has_more": has_more,
            }

    def ack(self, device: DeviceContext, *, last_event_sequence: int) -> SyncCursor:
        stored_device = self.get_device(device.client_device_id)
        cursor = stored_device.cursor or self.repository.add_cursor(
            SyncCursor(client_device_id=stored_device.id, last_event_sequence=0)
        )
        if last_event_sequence > cursor.last_event_sequence:
            cursor.last_event_sequence = last_event_sequence
        cursor.last_synced_at = utcnow()
        commit_session(self.session)
        return cursor

    def push(self, device: DeviceContext, *, mutations: list[dict]) -> list[dict]:
        if len(mutations) > self.settings.sync_push_max_batch_size:
            raise ValidationFailedError(
                f"sync push batch exceeds max size {self.settings.sync_push_max_batch_size}"
            )

        results: list[dict] = []
        paper_service = PaperService(self.session)
        subscription_policy_service = SubscriptionPolicyService(self.session)
        work_activity_service = WorkActivityService(self.session)

        with bind_log_context(client_device_id=device.client_device_id, user_id=device.user_id):
            for payload in mutations:
                self.metrics.increment("sync_mutations_received_total")
                existing = self.repository.get_mutation(
                    client_device_id=device.client_device_id,
                    client_mutation_id=payload["client_mutation_id"],
                )
                if existing is not None:
                    results.append(
                        {
                            "client_mutation_id": payload["client_mutation_id"],
                            "status": SyncMutationStatus.DUPLICATE,
                            "error_message": existing.error_message,
                            "resulting_event_sequence": existing.resulting_event_sequence,
                        }
                    )
                    continue

                mutation = SyncMutation(
                    client_device_id=device.client_device_id,
                    client_mutation_id=payload["client_mutation_id"],
                    mutation_type=payload["mutation_type"],
                    resource_type=payload["resource_type"],
                    resource_id=payload.get("resource_id"),
                    payload=dict(payload.get("payload", {})),
                    status=SyncMutationStatus.ACCEPTED,
                )
                self.repository.add_mutation(mutation)
                commit_session(self.session)

                try:
                    resulting_event_sequence = self._apply_mutation(
                        device=device,
                        mutation=mutation,
                        paper_service=paper_service,
                        subscription_policy_service=subscription_policy_service,
                        work_activity_service=work_activity_service,
                    )
                    mutation.status = SyncMutationStatus.APPLIED
                    mutation.resulting_event_sequence = resulting_event_sequence
                    mutation.applied_at = utcnow()
                    commit_session(self.session)
                    self.metrics.increment("sync_mutations_applied_total")
                    results.append(
                        {
                            "client_mutation_id": mutation.client_mutation_id,
                            "status": mutation.status,
                            "error_message": None,
                            "resulting_event_sequence": mutation.resulting_event_sequence,
                        }
                    )
                except Exception as exc:
                    self.session.rollback()
                    stored = self.repository.get_mutation(
                        client_device_id=device.client_device_id,
                        client_mutation_id=payload["client_mutation_id"],
                    )
                    if stored is None:
                        raise
                    stored.status = SyncMutationStatus.FAILED
                    stored.error_message = str(exc)
                    commit_session(self.session)
                    self.metrics.increment("sync_mutations_failed_total")
                    results.append(
                        {
                            "client_mutation_id": stored.client_mutation_id,
                            "status": stored.status,
                            "error_message": stored.error_message,
                            "resulting_event_sequence": stored.resulting_event_sequence,
                        }
                    )
            logger.info("sync push processed", extra={"mutations": len(results)})
        return results

    def _apply_mutation(
        self,
        *,
        device: DeviceContext,
        mutation: SyncMutation,
        paper_service: PaperService,
        subscription_policy_service: SubscriptionPolicyService,
        work_activity_service: WorkActivityService,
    ) -> int | None:
        if mutation.mutation_type == "paper.patch":
            if mutation.resource_id is None:
                raise ValidationFailedError("paper.patch requires resource_id")
            paper = paper_service.get_paper(UUID(mutation.resource_id))
            if paper.user_id != device.user_id:
                raise NotFoundError(f"paper {mutation.resource_id} was not found")
            patch_payload = self._validated_paper_patch(mutation.payload)
            updated_paper = paper_service.update_paper(
                paper.id,
                patch_payload,
                event_source=SyncEventSource.SYNC_PUSH,
            )
            event = self.sync_event_service.get_latest_event_for_entity(
                user_id=device.user_id,
                entity_type="paper_profile",
                entity_id=str(updated_paper.id),
            )
            if event is None:
                raise ConflictError("sync event for paper.patch was not recorded")
            return event.sequence

        if mutation.mutation_type == "progress_event.create":
            if mutation.resource_id is None:
                raise ValidationFailedError("progress_event.create requires resource_id")
            paper = paper_service.get_paper(UUID(mutation.resource_id))
            if paper.user_id != device.user_id:
                raise NotFoundError(f"paper {mutation.resource_id} was not found")
            created_event = paper_service.add_progress_event(
                paper.id,
                ProgressEventCreate(**mutation.payload),
                event_source=SyncEventSource.SYNC_PUSH,
            )
            event = self.sync_event_service.get_latest_event_for_entity(
                user_id=device.user_id,
                entity_type="progress_event",
                entity_id=str(created_event.id),
            )
            if event is None:
                raise ConflictError("sync event for progress_event.create was not recorded")
            return event.sequence

        if mutation.mutation_type == "subscription_policy.patch":
            if mutation.resource_id is None:
                raise ValidationFailedError("subscription_policy.patch requires resource_id")
            policy = subscription_policy_service.get_policy(UUID(mutation.resource_id))
            if policy.user_id != device.user_id:
                raise NotFoundError(f"subscription policy {mutation.resource_id} was not found")
            patch_payload = self._validated_subscription_policy_patch(mutation.payload)
            updated_policy = subscription_policy_service.update_policy(
                policy.id,
                patch_payload,
                event_source=SyncEventSource.SYNC_PUSH,
            )
            event = self.sync_event_service.get_latest_event_for_entity(
                user_id=device.user_id,
                entity_type="subscription_policy",
                entity_id=str(updated_policy.id),
            )
            if event is None:
                raise ConflictError("sync event for subscription_policy.patch was not recorded")
            return event.sequence

        if mutation.mutation_type == "work_activity.record":
            payload = self._validated_work_activity_record_payload(mutation.payload)
            paper_id = payload.get("paper_id")
            work_activity_type = payload["activity_type"]
            work_activity_service.validate_desktop_activity_type(work_activity_type)
            work_activity_service.record_event(
                user_id=device.user_id,
                paper_id=UUID(paper_id) if paper_id else None,
                activity_type=work_activity_type,
                summary=payload["summary"],
                metadata=payload.get("metadata"),
                happened_at=payload["happened_at"],
                source=payload["source"],
            )
            return None

        raise ValidationFailedError(f"unsupported mutation_type {mutation.mutation_type}")

    def _issue_device_token(
        self,
        *,
        client_device: ClientDevice,
        created_ip: str | None,
        user_agent: str | None,
    ) -> IssuedClientDeviceToken:
        raw_token = generate_refresh_token()
        expires_at = utcnow() + timedelta(days=self.settings.sync_device_token_ttl_days)
        access_token = ClientAccessToken(
            client_device_id=client_device.id,
            token_hash=hash_token(raw_token),
            issued_at=utcnow(),
            expires_at=expires_at,
            created_ip=created_ip,
            user_agent=user_agent,
        )
        self.repository.add_access_token(access_token)
        return IssuedClientDeviceToken(
            client_device_id=client_device.id,
            plain_text_token=raw_token,
            expires_at=expires_at,
        )

    def _revoke_active_tokens(self, client_device_id: UUID, *, now: datetime) -> None:
        for token in self.repository.list_active_access_tokens(client_device_id, as_of=now):
            token.revoked_at = now
            token.last_used_at = now

    def _resolve_feed_limit(self, limit: int | None) -> int:
        if limit is None:
            return self.settings.sync_feed_default_limit
        return min(max(1, limit), self.settings.sync_feed_max_limit)

    def _validated_paper_patch(self, payload: dict) -> PaperProfileUpdate:
        allowed_keys = {
            "stage",
            "venue",
            "next_action",
            "blocker",
            "priority",
            "last_touch_at",
        }
        unexpected = sorted(set(payload) - allowed_keys)
        if unexpected:
            raise ValidationFailedError(
                f"paper.patch payload includes unsupported fields: {', '.join(unexpected)}"
            )
        return PaperProfileUpdate(**payload)

    def _validated_subscription_policy_patch(self, payload: dict) -> SubscriptionPolicyUpdate:
        allowed_keys = {
            "enabled",
            "quiet_hours",
            "frequency_cap",
            "policy",
        }
        unexpected = sorted(set(payload) - allowed_keys)
        if unexpected:
            raise ValidationFailedError(
                "subscription_policy.patch payload includes unsupported fields: "
                f"{', '.join(unexpected)}"
            )
        return SubscriptionPolicyUpdate(**payload)

    def _validated_work_activity_record_payload(self, payload: dict) -> dict:
        allowed_keys = {
            "paper_id",
            "activity_type",
            "summary",
            "metadata",
            "happened_at",
        }
        unexpected = sorted(set(payload) - allowed_keys)
        if unexpected:
            raise ValidationFailedError(
                f"work_activity.record payload includes unsupported fields: {', '.join(unexpected)}"
            )
        activity_type = payload.get("activity_type")
        summary = str(payload.get("summary") or "").strip()
        happened_at = payload.get("happened_at")
        if not activity_type:
            raise ValidationFailedError("work_activity.record requires activity_type")
        if not summary:
            raise ValidationFailedError("work_activity.record requires summary")
        if not happened_at:
            raise ValidationFailedError("work_activity.record requires happened_at")
        metadata = payload.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValidationFailedError("work_activity.record metadata must be an object or null")
        if payload.get("paper_id") is not None and not str(payload.get("paper_id")).strip():
            raise ValidationFailedError("work_activity.record paper_id must not be blank")
        try:
            parsed_type = WorkActivityType(str(activity_type))
        except ValueError as exc:
            raise ValidationFailedError(f"unsupported work activity type {activity_type}") from exc
        try:
            parsed_happened_at = datetime.fromisoformat(str(happened_at))
        except ValueError as exc:
            raise ValidationFailedError(
                "work_activity.record happened_at must be an ISO 8601 datetime"
            ) from exc

        return {
            "paper_id": str(payload.get("paper_id")).strip() if payload.get("paper_id") else None,
            "activity_type": parsed_type,
            "summary": summary,
            "metadata": metadata,
            "happened_at": parsed_happened_at,
            "source": WorkActivitySource.DESKTOP_LOCAL,
        }


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
