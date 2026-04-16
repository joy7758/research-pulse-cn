"""Mini-program read-only reserve service and compact read models."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import AuthenticationError, AuthorizationError, NotFoundError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import MiniReadGrant, PaperProfile, PulseDigestIssue, utcnow
from research_pulse_cn.domain.enums import (
    ChannelType,
    MiniReadGrantStatus,
    MiniReadGrantType,
    PaperType,
    WeChatBindingChannelType,
)
from research_pulse_cn.domain.mini import IssuedMiniReadGrant, MiniGrantContext
from research_pulse_cn.domain.progress import derive_progress_percentage
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.mini import MiniRepository
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session
from research_pulse_cn.services.digest import DigestService
from research_pulse_cn.services.official_account_binding_handshake import (
    OfficialAccountBindingHandshakeService,
)
from research_pulse_cn.services.subscription_editor_handoff import (
    SubscriptionEditorHandoffService,
)
from research_pulse_cn.services.subscription_policy import (
    find_matching_delivery_policy,
    normalize_delivery_control_policy,
)

logger = logging.getLogger(__name__)

PAPER_SORT_DESCRIPTION = [
    "priority desc",
    "last_touch_at desc",
    "updated_at desc",
    "title asc",
    "paper_id asc",
]

MINI_TODAY_SECTION_ORDER = [
    "today_focus",
    "yesterday_recap",
    "signal_updates",
    "related_papers",
    "other_updates",
]

MINI_SECTION_TITLE_BY_KIND = {
    "today_focus": "Today Focus",
    "yesterday_recap": "Yesterday Recap",
    "signal_updates": "Signal Updates",
    "related_papers": "Related Papers",
    "other_updates": "Other Updates",
}

MINI_SELF_SERVICE_EDITABLE_FIELDS = [
    "enabled",
    "quiet_hours",
    "timezone",
    "allowed_weekdays",
    "muted_until",
    "minimum_selected_cards",
    "skip_if_no_today_focus",
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
        self.subscription_policy_repository = SubscriptionPolicyRepository(session)
        self.digest_service = DigestService(session, now_provider=self.now_provider)
        self.binding_handshake_service = OfficialAccountBindingHandshakeService(
            session,
            now_provider=self.now_provider,
        )
        self.editor_handoff_service = SubscriptionEditorHandoffService(
            session,
            now_provider=self.now_provider,
        )
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
            subscription_reserve = self._subscription_reserve_payload(stored)
            return {
                "grant": self._grant_context_payload(stored),
                "user": self._user_summary(user),
                "available_routes": self._available_routes(stored),
                "available_resources": self._available_resources(stored),
                "default_landing_path": self.preview_landing_path(stored),
                "subscription_reserve_summary": {
                    "has_official_account_binding": (
                        subscription_reserve["official_account_binding"] is not None
                    ),
                    "has_official_account_subscription_settings": (
                        subscription_reserve["subscription_settings"]["subscription_policy_id"]
                        is not None
                    ),
                    "delivery_preview_state": subscription_reserve["delivery_control_preview"][
                        "state"
                    ],
                    "latest_digest_issue_id": (
                        None
                        if subscription_reserve["latest_digest_issue"] is None
                        else subscription_reserve["latest_digest_issue"]["id"]
                    ),
                    "self_service_reserve": subscription_reserve["self_service_reserve"],
                    "self_service_entry": subscription_reserve["self_service_entry"],
                },
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
                "digest_issue": self._digest_issue_summary_from_detail(digest_detail),
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

    def subscription_reserve(self, grant: MiniGrantContext) -> dict:
        with bind_log_context(mini_grant_id=grant.grant_id, user_id=grant.user_id):
            self.metrics.increment("mini_read_requests_total")
            stored = self.get_grant(grant.grant_id)
            return self._subscription_reserve_payload(stored)

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
            "subscribed_at": binding.subscribed_at,
            "unsubscribed_at": binding.unsubscribed_at,
            "last_seen_at": binding.last_seen_at,
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
        content_payload = dict(issue.content_payload or {})
        raw_items = list(content_payload.get("items") or [])
        items = self._normalize_digest_items(
            raw_items if raw_items else self._digest_items_from_issue(issue),
            issue=issue,
        )
        structured_sections = list(content_payload.get("sections") or [])
        is_structured = bool(structured_sections)
        section_order = self._normalize_section_order(
            content_payload.get("section_order"),
            is_structured=is_structured,
        )
        sections = (
            self._normalize_sections(structured_sections, issue=issue)
            if is_structured
            else self._build_fallback_sections(items)
        )
        focus_card = (
            self._normalize_digest_item(content_payload.get("focus_card"), issue=issue)
            if is_structured
            else self._derive_focus_card_from_sections(sections)
        )
        quick_stats = (
            self._normalize_quick_stats(content_payload.get("quick_stats"))
            if is_structured
            else self._build_quick_stats(items)
        )
        publication_preview = self._normalize_publication_preview(
            content_payload.get("publication_preview"),
            issue=issue,
        )
        highlights = self._normalize_digest_items(
            list(content_payload.get("highlights") or []),
            issue=issue,
        )
        if not highlights:
            highlights = items[: min(issue.highlight_count, len(items))]
        return {
            "id": issue.id,
            "issue_date": issue.issue_date.isoformat(),
            "status": issue.status.value,
            "title": issue.title,
            "summary": issue.summary,
            "highlight_count": issue.highlight_count,
            "selected_card_count": issue.selected_card_count,
            "deep_link_path": issue.deep_link_path,
            "highlights": highlights,
            "items": items,
            "is_structured": is_structured,
            "fallback_mode": "structured" if is_structured else "highlights_only",
            "section_order": section_order,
            "sections": sections,
            "quick_stats": quick_stats,
            "focus_card": focus_card,
            "publication_preview": publication_preview,
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
            "/mini/subscription-reserve",
            "/mini/subscription-reserve/editor-handoff",
            "/mini/subscription-reserve/editor-handoff-status",
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

    def _digest_items_from_issue(self, issue: PulseDigestIssue) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
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
                    "action_text": None,
                    "deep_link": None,
                    "paper": (
                        None
                        if item.source_paper is None
                        else self._paper_summary(item.source_paper)
                    ),
                }
            )
        return items

    def _digest_issue_summary_from_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in detail.items() if key != "items"}

    def _normalize_digest_item(
        self,
        raw_item: dict[str, Any] | None,
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_item, dict):
            return None
        paper = raw_item.get("paper")
        if paper is None:
            paper = self._resolve_paper_summary_for_digest_item(raw_item, issue=issue)
        return {
            "sort_order": int(raw_item.get("sort_order", 0)),
            "pulse_card_id": raw_item.get("pulse_card_id"),
            "card_type": str(raw_item.get("card_type", "")),
            "source_paper_id": raw_item.get("source_paper_id"),
            "title": str(raw_item.get("title", "")),
            "summary": str(raw_item.get("summary", "")),
            "why_now": raw_item.get("why_now"),
            "action_text": raw_item.get("action_text"),
            "deep_link": raw_item.get("deep_link"),
            "paper": paper,
        }

    def _normalize_digest_items(
        self,
        raw_items: Sequence[dict[str, Any]],
        *,
        issue: PulseDigestIssue,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for raw_item in raw_items:
            normalized = self._normalize_digest_item(raw_item, issue=issue)
            if normalized is not None:
                items.append(normalized)
        return sorted(
            items,
            key=lambda item: (
                int(item.get("sort_order", 0)),
                str(item.get("pulse_card_id", "")),
            ),
        )

    def _normalize_sections(
        self,
        raw_sections: Sequence[dict[str, Any]],
        *,
        issue: PulseDigestIssue,
    ) -> list[dict[str, Any]]:
        normalized_sections: list[dict[str, Any]] = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            kind = str(raw_section.get("kind") or "other_updates")
            items = self._normalize_digest_items(list(raw_section.get("items") or []), issue=issue)
            if not items:
                continue
            normalized_sections.append(
                {
                    "kind": kind,
                    "title": str(raw_section.get("title") or self._section_title(kind)),
                    "item_count": int(raw_section.get("item_count") or len(items)),
                    "items": items,
                }
            )
        return self._order_sections(normalized_sections)

    def _normalize_section_order(
        self,
        raw_section_order: Sequence[str] | None,
        *,
        is_structured: bool,
    ) -> list[str]:
        if not is_structured:
            return list(MINI_TODAY_SECTION_ORDER)
        ordered: list[str] = []
        for kind in list(raw_section_order or []):
            kind_str = str(kind)
            if kind_str not in ordered:
                ordered.append(kind_str)
        for kind in MINI_TODAY_SECTION_ORDER:
            if kind not in ordered:
                ordered.append(kind)
        return ordered

    def _normalize_quick_stats(
        self,
        raw_quick_stats: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_quick_stats, dict):
            return None
        return {
            "selected_card_count": int(raw_quick_stats.get("selected_card_count") or 0),
            "related_paper_count": int(raw_quick_stats.get("related_paper_count") or 0),
            "signal_update_count": int(raw_quick_stats.get("signal_update_count") or 0),
            "touched_paper_count": int(raw_quick_stats.get("touched_paper_count") or 0),
        }

    def _normalize_publication_preview(
        self,
        raw_preview: dict[str, Any] | None,
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_preview, dict):
            return None
        return {
            "digest_title": raw_preview.get("digest_title"),
            "digest_subtitle": raw_preview.get("digest_subtitle"),
            "digest_highlights": self._normalize_digest_items(
                list(raw_preview.get("digest_highlights") or []),
                issue=issue,
            ),
            "primary_cta_text": raw_preview.get("primary_cta_text"),
            "primary_cta_path": raw_preview.get("primary_cta_path"),
            "mini_program_path": raw_preview.get("mini_program_path"),
            "article_url": raw_preview.get("article_url"),
        }

    def _build_fallback_sections(self, items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = {kind: [] for kind in MINI_TODAY_SECTION_ORDER}
        for item in items:
            buckets[self._fallback_section_kind(str(item.get("card_type") or ""))].append(item)
        sections: list[dict[str, Any]] = []
        for kind in MINI_TODAY_SECTION_ORDER:
            bucket = buckets[kind]
            if not bucket:
                continue
            sections.append(
                {
                    "kind": kind,
                    "title": self._section_title(kind),
                    "item_count": len(bucket),
                    "items": list(bucket),
                }
            )
        return sections

    def _build_quick_stats(self, items: Sequence[dict[str, Any]]) -> dict[str, Any]:
        touched_paper_ids = {
            str(item["source_paper_id"])
            for item in items
            if item.get("source_paper_id") is not None
        }
        return {
            "selected_card_count": len(items),
            "related_paper_count": sum(
                1 for item in items if item.get("card_type") == "related_paper"
            ),
            "signal_update_count": sum(
                1 for item in items if item.get("card_type") == "signal_change"
            ),
            "touched_paper_count": len(touched_paper_ids),
        }

    def _derive_focus_card_from_sections(
        self,
        sections: Sequence[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for section in sections:
            items = list(section.get("items") or [])
            if items:
                return items[0]
        return None

    def _fallback_section_kind(self, card_type: str) -> str:
        if card_type in {
            "today_suggestion",
            "next_action",
            "stalled_progress",
            "deadline_risk",
        }:
            return "today_focus"
        if card_type == "yesterday_summary":
            return "yesterday_recap"
        if card_type == "signal_change":
            return "signal_updates"
        if card_type == "related_paper":
            return "related_papers"
        return "other_updates"

    def _section_title(self, kind: str) -> str:
        return MINI_SECTION_TITLE_BY_KIND.get(kind, kind.replace("_", " ").title())

    def _order_sections(self, sections: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        order_index = {kind: index for index, kind in enumerate(MINI_TODAY_SECTION_ORDER)}
        return sorted(
            sections,
            key=lambda section: (
                order_index.get(str(section.get("kind")), len(order_index)),
                str(section.get("title", "")),
                str(section.get("kind", "")),
            ),
        )

    def _resolve_paper_summary_for_digest_item(
        self,
        raw_item: dict[str, Any],
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        pulse_card_id = raw_item.get("pulse_card_id")
        source_paper_id = raw_item.get("source_paper_id")
        for item in issue.items:
            if pulse_card_id is not None and str(item.pulse_card_id) == str(pulse_card_id):
                return None if item.source_paper is None else self._paper_summary(item.source_paper)
            if source_paper_id is not None and str(item.source_paper_id) == str(source_paper_id):
                return None if item.source_paper is None else self._paper_summary(item.source_paper)
        return None

    def _subscription_reserve_payload(self, grant: MiniReadGrant) -> dict[str, Any]:
        user = self._require_user(grant.user_id)
        latest_issue = self._resolve_default_digest_issue(grant) or self._latest_digest_issue(
            grant.user_id
        )
        official_account_binding = self._official_account_binding(grant.user_id)
        subscription_settings = self._subscription_settings_payload(grant.user_id)
        delivery_preview = self._delivery_control_preview_payload(
            grant.user_id,
            issue=latest_issue,
        )
        self_service_entry = {
            "supported": True,
            "oauth_enabled": self.settings.official_account_oauth_enabled,
            "editable_via_current_mini_grant": False,
            "separate_self_service_grant_required": True,
            "editor_contract_available": True,
            "editor_preview_available": True,
            "supported_editable_fields": list(MINI_SELF_SERVICE_EDITABLE_FIELDS),
            "notes": [
                "Mini remains read-only in this phase.",
                (
                    "A separate self-service grant is required for editor bootstrap, "
                    "contract, and preview-before-save."
                ),
                (
                    "Official-account OAuth completion is available through self-service reserve."
                    if self.settings.official_account_oauth_enabled
                    else "Real WeChat OAuth handoff is not enabled yet."
                ),
            ],
        }
        return {
            "grant": self._grant_context_payload(grant),
            "user": self._user_summary(user),
            "official_account_binding": self._binding_summary(official_account_binding),
            "subscription_settings": subscription_settings,
            "delivery_control_preview": delivery_preview,
            "latest_digest_issue": (
                None
                if latest_issue is None
                else self._digest_issue_summary_from_detail(
                    self._digest_issue_payload(latest_issue)
                )
            ),
            "self_service_reserve": self_service_entry,
            "self_service_entry": self_service_entry,
            "binding_handoff_reserve": self.binding_handshake_service.mini_binding_handoff_reserve(
                user_id=grant.user_id
            ),
            "editor_handoff_reserve": self.editor_handoff_service.mini_editor_handoff_reserve(
                mini_grant_id=grant.id,
                user_id=grant.user_id,
            ),
            "workspace_invite_reserve": {
                "supported": True,
                "editable_via_current_mini_grant": False,
                "separate_self_service_grant_required": True,
                "claim_supported_via_self_service": True,
                "notes": [
                    "Mini remains read-only in this phase.",
                    "Workspace invite claims require a separate self-service grant.",
                ],
            },
        }

    def _official_account_binding(self, user_id: UUID):
        bindings = self.digest_repository.list_bindings(
            user_id=user_id,
            channel_type=WeChatBindingChannelType.OFFICIAL_ACCOUNT,
        )
        return bindings[0] if bindings else None

    def _subscription_settings_payload(self, user_id: UUID) -> dict[str, Any]:
        policy = self._current_official_account_policy(user_id)
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

    def _delivery_control_preview_payload(
        self,
        user_id: UUID,
        *,
        issue: PulseDigestIssue | None,
    ) -> dict[str, Any]:
        policy = self._current_official_account_policy(user_id)
        current_time = self.now_provider()
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=UTC)

        if issue is not None:
            preview = self.digest_service.get_delivery_control_preview(
                issue.id,
                channel=ChannelType.OFFICIAL_ACCOUNT,
                now=current_time,
            )
            return {
                "state": "ready",
                "decision": preview.decision,
                "reason_codes": list(preview.reason_codes),
                "normalized_control_policy": dict(preview.normalized_control_policy),
                "current_local_time": preview.current_local_time,
                "local_weekday": preview.local_weekday,
                "next_allowed_at": preview.next_allowed_at,
                "notes": [],
            }

        normalized = normalize_delivery_control_policy(
            policy,
            default_timezone=self.settings.default_timezone,
        )
        zone = self._safe_zone(normalized.effective_timezone)
        local_now = current_time.astimezone(zone)
        return {
            "state": "empty",
            "decision": None,
            "reason_codes": [],
            "normalized_control_policy": normalized.as_dict(),
            "current_local_time": local_now,
            "local_weekday": local_now.weekday(),
            "next_allowed_at": None,
            "notes": [
                "No digest issue is available yet for an authoritative delivery-control evaluation."
            ],
        }

    def _latest_digest_issue(self, user_id: UUID) -> PulseDigestIssue | None:
        issues = self.digest_service.list_digest_issues(user_id=user_id)
        return issues[0] if issues else None

    def _current_official_account_policy(self, user_id: UUID):
        policies = self.subscription_policy_repository.list(user_id=user_id)
        return find_matching_delivery_policy(policies, channel=ChannelType.OFFICIAL_ACCOUNT)

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

    def _safe_zone(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")
