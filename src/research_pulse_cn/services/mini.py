"""Mini-program read-only reserve service and compact read models."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import AuthenticationError, AuthorizationError, NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import MiniReadGrant, PaperProfile, PulseDigestIssue, utcnow
from research_pulse_cn.domain.enums import (
    MiniReadGrantStatus,
    MiniReadGrantType,
    PaperType,
)
from research_pulse_cn.domain.mini import IssuedMiniReadGrant, MiniGrantContext
from research_pulse_cn.domain.progress import derive_progress_percentage
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.mini import MiniRepository
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)

PAPER_SORT_DESCRIPTION = [
    "priority desc",
    "last_touch_at desc",
    "updated_at desc",
    "title asc",
    "paper_id asc",
]


class MiniService:
    """Issue mini read grants and build compact mobile-friendly read views."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = MiniRepository(session)
        self.user_repository = UserRepository(session)
        self.paper_repository = PaperRepository(session)
        self.digest_repository = DigestRepository(session)
        self.metrics = get_metrics()

    def list_grants(
        self,
        *,
        user_id: UUID | None = None,
        status: MiniReadGrantStatus | None = None,
        grant_type: MiniReadGrantType | None = None,
        digest_issue_id: UUID | None = None,
        binding_id: UUID | None = None,
    ) -> list[MiniReadGrant]:
        return self.repository.list_grants(
            user_id=user_id,
            status=status,
            grant_type=grant_type,
            digest_issue_id=digest_issue_id,
            binding_id=binding_id,
        )

    def get_grant(self, grant_id: UUID) -> MiniReadGrant:
        grant = self.repository.get_grant(grant_id)
        if grant is None:
            raise NotFoundError(f"mini read grant {grant_id} was not found")
        return grant

    def serialize_grant(self, grant: MiniReadGrant) -> dict:
        return {
            **self._grant_context_payload(grant),
            "created_by_admin_id": grant.created_by_admin_id,
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def create_grant(
        self,
        *,
        user_id: UUID,
        grant_type: MiniReadGrantType,
        created_by_admin_id: UUID | None,
        binding_id: UUID | None = None,
        digest_issue_id: UUID | None = None,
        scope: dict | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[MiniReadGrant, IssuedMiniReadGrant]:
        self._require_user(user_id)
        binding = None if binding_id is None else self.digest_repository.get_binding(binding_id)
        if binding is not None and binding.user_id != user_id:
            raise NotFoundError(f"wechat binding {binding_id} was not found")
        if binding_id is not None and binding is None:
            raise NotFoundError(f"wechat binding {binding_id} was not found")

        digest_issue = None
        if digest_issue_id is not None:
            digest_issue = self.digest_repository.get_digest_issue(digest_issue_id)
        if digest_issue is not None and digest_issue.user_id != user_id:
            raise NotFoundError(f"digest issue {digest_issue_id} was not found")
        if digest_issue_id is not None and digest_issue is None:
            raise NotFoundError(f"digest issue {digest_issue_id} was not found")

        effective_scope = self._build_effective_scope(
            scope=scope or {},
            digest_issue_id=digest_issue_id,
        )
        effective_expires_at = expires_at or (
            self.now_provider() + timedelta(hours=self.settings.mini_read_grant_default_ttl_hours)
        )
        raw_token = generate_refresh_token()
        grant = MiniReadGrant(
            user_id=user_id,
            binding_id=None if binding is None else binding.id,
            digest_issue_id=None if digest_issue is None else digest_issue.id,
            grant_type=grant_type,
            token_hash=hash_token(raw_token),
            status=MiniReadGrantStatus.ACTIVE,
            scope_json=effective_scope or None,
            expires_at=effective_expires_at,
            created_by_admin_id=created_by_admin_id,
        )
        self.repository.add_grant(grant)
        commit_session(self.session)
        persisted = self.get_grant(grant.id)
        preview_landing_path = self.preview_landing_path(persisted)
        self.metrics.increment("mini_read_grants_issued_total")
        return persisted, IssuedMiniReadGrant(
            grant_id=persisted.id,
            plain_text_token=raw_token,
            expires_at=persisted.expires_at,
            preview_landing_path=preview_landing_path,
        )

    def revoke_grant(self, grant_id: UUID) -> MiniReadGrant:
        grant = self.get_grant(grant_id)
        if grant.status != MiniReadGrantStatus.REVOKED:
            grant.status = MiniReadGrantStatus.REVOKED
            commit_session(self.session)
            self.metrics.increment("mini_read_grants_revoked_total")
        return self.get_grant(grant_id)

    def authenticate_grant_token(self, raw_token: str) -> MiniGrantContext:
        grant = self.repository.get_grant_by_token_hash(hash_token(raw_token))
        if grant is None:
            raise AuthenticationError("mini read grant was not found")
        now = self.now_provider()
        if grant.status == MiniReadGrantStatus.REVOKED:
            raise AuthenticationError("mini read grant has been revoked")
        if grant.status == MiniReadGrantStatus.EXPIRED:
            raise AuthenticationError("mini read grant has expired")
        if grant.expires_at is not None and (
            self._coerce_utc(grant.expires_at) <= self._coerce_utc(now)
        ):
            grant.status = MiniReadGrantStatus.EXPIRED
            commit_session(self.session)
            raise AuthenticationError("mini read grant has expired")
        grant.last_used_at = now
        commit_session(self.session)
        return MiniGrantContext(
            grant_id=grant.id,
            user_id=grant.user_id,
            binding_id=grant.binding_id,
            digest_issue_id=grant.digest_issue_id,
            grant_type=grant.grant_type,
            status=grant.status,
            scope=dict(grant.scope_json or {}),
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def bootstrap(self, grant: MiniGrantContext) -> dict:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            user = self._require_user(grant.user_id)
            stored = self.get_grant(grant.grant_id)
            return {
                "grant": self._grant_context_payload(stored),
                "user": self._user_summary(user),
                "available_routes": self._available_routes(stored),
                "available_resources": self._available_resources(stored),
                "default_landing_path": self.preview_landing_path(stored),
            }

    def today(self, grant: MiniGrantContext) -> dict:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            stored = self.get_grant(grant.grant_id)
            issue = self._resolve_default_digest_issue(stored)
            if issue is None:
                return {
                    "state": "empty",
                    "default_landing_path": self.preview_landing_path(stored),
                    "digest_issue": None,
                    "papers": [],
                    "message": "No digest issue is available yet for this mini view.",
                }
            digest_detail = self._digest_issue_payload(issue)
            return {
                "state": "ready",
                "default_landing_path": self.preview_landing_path(stored),
                "digest_issue": {
                    "id": digest_detail["id"],
                    "issue_date": digest_detail["issue_date"],
                    "status": digest_detail["status"],
                    "title": digest_detail["title"],
                    "summary": digest_detail["summary"],
                    "highlight_count": digest_detail["highlight_count"],
                    "selected_card_count": digest_detail["selected_card_count"],
                    "deep_link_path": digest_detail["deep_link_path"],
                    "highlights": digest_detail["highlights"],
                },
                "papers": self._today_paper_refs(issue),
                "message": None,
            }

    def get_digest_issue_detail(self, grant: MiniGrantContext, digest_issue_id: UUID) -> dict:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            issue = self.digest_repository.get_digest_issue(digest_issue_id)
            if issue is None or issue.user_id != grant.user_id:
                raise NotFoundError(f"digest issue {digest_issue_id} was not found")
            self._ensure_digest_access(grant, issue.id)
            return self._digest_issue_payload(issue)

    def list_papers(
        self,
        grant: MiniGrantContext,
        *,
        limit: int | None = None,
        paper_type: PaperType | None = None,
        stage: str | None = None,
    ) -> list[dict]:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            papers = self.paper_repository.list(user_id=grant.user_id)
            allowed_paper_ids = self._allowed_paper_ids(grant)
            if allowed_paper_ids is not None:
                papers = [paper for paper in papers if paper.id in allowed_paper_ids]
            if paper_type is not None:
                papers = [paper for paper in papers if paper.type == paper_type]
            if stage is not None:
                papers = [paper for paper in papers if paper.stage == stage]
            papers = sorted(papers, key=self._paper_sort_key)
            effective_limit = self._resolve_papers_limit(limit)
            return [self._paper_summary(paper) for paper in papers[:effective_limit]]

    def get_paper_detail(self, grant: MiniGrantContext, paper_id: UUID) -> dict:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            paper = self.paper_repository.get(paper_id)
            if paper is None or paper.user_id != grant.user_id:
                raise NotFoundError(f"paper {paper_id} was not found")
            self._ensure_paper_access(grant, paper.id)
            return self._paper_detail(paper)

    def preview_landing_path(self, grant: MiniReadGrant) -> str:
        scope = dict(grant.scope_json or {})
        if grant.digest_issue_id is not None:
            return f"/mini/digest-issues/{grant.digest_issue_id}"
        paper_ids = scope.get("paper_ids")
        if (
            grant.grant_type == MiniReadGrantType.PAPER_DETAIL
            and isinstance(paper_ids, list)
            and paper_ids
        ):
            return f"/mini/papers/{paper_ids[0]}"
        return "/mini/today"

    def _grant_context_payload(self, grant: MiniReadGrant) -> dict:
        return {
            "id": grant.id,
            "user_id": grant.user_id,
            "binding_id": grant.binding_id,
            "digest_issue_id": grant.digest_issue_id,
            "grant_type": grant.grant_type,
            "status": grant.status,
            "scope": dict(grant.scope_json or {}),
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "preview_landing_path": self.preview_landing_path(grant),
            "binding": self._binding_summary(grant.binding),
        }

    def _user_summary(self, user) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "field": user.field,
        }

    def _binding_summary(self, binding) -> dict | None:
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
        }

    def _paper_summary(self, paper: PaperProfile) -> dict:
        return {
            "id": paper.id,
            "title": paper.title,
            "type": paper.type,
            "stage": paper.stage,
            "venue": paper.venue,
            "priority": paper.priority,
            "next_action": paper.next_action,
            "blocker": paper.blocker,
            "last_touch_at": paper.last_touch_at,
            "progress_percentage": derive_progress_percentage(paper.type),
        }

    def _paper_detail(self, paper: PaperProfile) -> dict:
        progress_events = sorted(
            paper.progress_events,
            key=lambda item: (item.happened_at, str(item.id)),
            reverse=True,
        )[:5]
        signal_snapshots = sorted(
            paper.signal_snapshots,
            key=lambda item: (item.fetched_at, str(item.id)),
            reverse=True,
        )[:3]
        return {
            **self._paper_summary(paper),
            "user_id": paper.user_id,
            "identifiers": dict(paper.identifiers),
            "source_links": list(paper.source_links),
            "progress_events": [
                {
                    "id": event.id,
                    "stage": event.stage,
                    "happened_at": event.happened_at,
                    "summary": event.summary,
                    "owner": event.owner,
                }
                for event in progress_events
            ],
            "signal_snapshots": [
                {
                    "id": snapshot.id,
                    "source": snapshot.source,
                    "citation_count": snapshot.citation_count,
                    "download_count": snapshot.download_count,
                    "read_count": snapshot.read_count,
                    "inclusion_status": snapshot.inclusion_status,
                    "fetched_at": snapshot.fetched_at,
                }
                for snapshot in signal_snapshots
            ],
        }

    def _digest_issue_payload(self, issue: PulseDigestIssue) -> dict:
        items = []
        for item in issue.items:
            items.append(
                {
                    "sort_order": item.sort_order,
                    "pulse_card_id": item.pulse_card_id,
                    "card_type": item.card_type.value,
                    "source_paper_id": item.source_paper_id,
                    "title": item.title,
                    "summary": item.summary,
                    "why_now": item.why_now,
                    "paper": (
                        None
                        if item.source_paper is None
                        else self._paper_summary(item.source_paper)
                    ),
                }
            )
        return {
            "id": issue.id,
            "issue_date": issue.issue_date.isoformat(),
            "status": issue.status.value,
            "title": issue.title,
            "summary": issue.summary,
            "highlight_count": issue.highlight_count,
            "selected_card_count": issue.selected_card_count,
            "deep_link_path": issue.deep_link_path,
            "highlights": items[: min(issue.highlight_count, len(items))],
            "items": items,
        }

    def _today_paper_refs(self, issue: PulseDigestIssue) -> list[dict]:
        seen: set[UUID] = set()
        papers: list[dict] = []
        for item in issue.items:
            if item.source_paper is None or item.source_paper.id in seen:
                continue
            seen.add(item.source_paper.id)
            papers.append(self._paper_summary(item.source_paper))
        return papers

    def _resolve_default_digest_issue(self, grant: MiniReadGrant) -> PulseDigestIssue | None:
        if grant.digest_issue_id is not None:
            issue = self.digest_repository.get_digest_issue(grant.digest_issue_id)
            if issue is None or issue.user_id != grant.user_id:
                return None
            return issue

        allowed_digest_ids = self._allowed_digest_issue_ids_from_scope(dict(grant.scope_json or {}))
        issues = self.digest_repository.list_digest_issues(user_id=grant.user_id)
        if allowed_digest_ids is None:
            return None if not issues else issues[0]
        for issue in issues:
            if issue.id in allowed_digest_ids:
                return issue
        return None

    def _available_routes(self, grant: MiniReadGrant) -> list[str]:
        routes = [
            "/mini/bootstrap",
            "/mini/today",
            "/mini/papers",
            "/mini/papers/{paper_id}",
        ]
        if grant.digest_issue_id is not None or self._allowed_digest_issue_ids_from_scope(
            dict(grant.scope_json or {})
        ):
            routes.append("/mini/digest-issues/{digest_issue_id}")
        return routes

    def _available_resources(self, grant: MiniReadGrant) -> dict:
        scope = dict(grant.scope_json or {})
        payload = {
            "user_id": str(grant.user_id),
            "binding_id": None if grant.binding_id is None else str(grant.binding_id),
            "digest_issue_id": (
                None if grant.digest_issue_id is None else str(grant.digest_issue_id)
            ),
            "restricted_digest_issue_ids": sorted(
                str(item) for item in (self._allowed_digest_issue_ids_from_scope(scope) or [])
            ),
            "restricted_paper_ids": sorted(
                str(item) for item in (self._allowed_paper_ids_from_scope(scope) or [])
            ),
            "future_landing_path": None,
        }
        if grant.digest_issue is not None and grant.digest_issue.deep_link_path is not None:
            payload["future_landing_path"] = grant.digest_issue.deep_link_path
        return payload

    def _ensure_digest_access(self, grant: MiniGrantContext, digest_issue_id: UUID) -> None:
        allowed_ids = self._allowed_digest_issue_ids(grant)
        if allowed_ids is not None and digest_issue_id not in allowed_ids:
            raise AuthorizationError("mini grant does not allow this digest issue")

    def _ensure_paper_access(self, grant: MiniGrantContext, paper_id: UUID) -> None:
        allowed_ids = self._allowed_paper_ids(grant)
        if allowed_ids is not None and paper_id not in allowed_ids:
            raise AuthorizationError("mini grant does not allow this paper")

    def _allowed_digest_issue_ids(self, grant: MiniGrantContext) -> set[UUID] | None:
        scope_ids = self._allowed_digest_issue_ids_from_scope(grant.scope)
        if grant.digest_issue_id is None and scope_ids is None:
            return None
        allowed: set[UUID] = set(scope_ids or set())
        if grant.digest_issue_id is not None:
            allowed.add(grant.digest_issue_id)
        return allowed

    def _allowed_paper_ids(self, grant: MiniGrantContext) -> set[UUID] | None:
        return self._allowed_paper_ids_from_scope(grant.scope)

    def _allowed_digest_issue_ids_from_scope(self, scope: dict) -> set[UUID] | None:
        raw_ids = scope.get("digest_issue_ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            return None
        return {UUID(str(item)) for item in raw_ids}

    def _allowed_paper_ids_from_scope(self, scope: dict) -> set[UUID] | None:
        raw_ids = scope.get("paper_ids")
        if not isinstance(raw_ids, list) or not raw_ids:
            return None
        return {UUID(str(item)) for item in raw_ids}

    def _build_effective_scope(self, *, scope: dict, digest_issue_id: UUID | None) -> dict:
        effective = dict(scope)
        if digest_issue_id is not None:
            digest_ids = effective.get("digest_issue_ids")
            if isinstance(digest_ids, list):
                if str(digest_issue_id) not in [str(item) for item in digest_ids]:
                    digest_ids.append(str(digest_issue_id))
            else:
                effective["digest_issue_ids"] = [str(digest_issue_id)]
        return effective

    def _require_user(self, user_id: UUID):
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def _resolve_papers_limit(self, limit: int | None) -> int:
        if limit is None:
            return self.settings.mini_papers_default_limit
        return min(max(1, limit), self.settings.mini_papers_max_limit)

    def _paper_sort_key(self, paper: PaperProfile) -> tuple:
        last_touch = paper.last_touch_at or paper.updated_at
        return (
            -paper.priority,
            -int(self._coerce_utc(last_touch).timestamp()),
            -int(self._coerce_utc(paper.updated_at).timestamp()),
            paper.title.lower(),
            str(paper.id),
        )

    def _coerce_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
