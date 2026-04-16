"""Read-only admin workbench service for users, papers, and watch profiles."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.db.models import (
    GroupWorkspaceMember,
    PaperProfile,
    PulseDigestIssue,
    ResearchWatchProfile,
    SignalSnapshot,
    UserProfile,
)
from research_pulse_cn.domain.enums import PaperType
from research_pulse_cn.domain.progress import derive_progress_percentage


class UserWorkbenchService:
    """Aggregate safe read models for internal support and ops workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_users(
        self,
        *,
        q: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        statement = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.papers).selectinload(PaperProfile.signal_snapshots),
                selectinload(UserProfile.papers).selectinload(PaperProfile.research_watch_profiles),
                selectinload(UserProfile.research_watch_profiles).selectinload(
                    ResearchWatchProfile.paper
                ),
                selectinload(UserProfile.group_workspace_memberships).selectinload(
                    GroupWorkspaceMember.workspace
                ),
                selectinload(UserProfile.digest_issues),
            )
            .order_by(UserProfile.updated_at.desc(), UserProfile.created_at.desc())
        )
        users = list(self.session.scalars(statement))
        filtered = self._filter_users(users, q=q)
        return [self._user_summary(user) for user in filtered[:limit]]

    def get_user_detail(self, user_id: UUID) -> dict:
        statement = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.papers).selectinload(PaperProfile.signal_snapshots),
                selectinload(UserProfile.papers).selectinload(PaperProfile.research_watch_profiles),
                selectinload(UserProfile.research_watch_profiles).selectinload(
                    ResearchWatchProfile.paper
                ),
                selectinload(UserProfile.group_workspace_memberships).selectinload(
                    GroupWorkspaceMember.workspace
                ),
                selectinload(UserProfile.digest_issues),
            )
            .where(UserProfile.id == user_id)
        )
        user = self.session.scalar(statement)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return {
            "user": self._user_summary(user),
            "papers": [self._paper_summary(paper) for paper in user.papers],
            "watch_profiles": [
                self._watch_profile(profile)
                for profile in sorted(
                    user.research_watch_profiles,
                    key=lambda item: (item.updated_at, item.created_at),
                    reverse=True,
                )
            ],
            "workspace_memberships": [
                self._workspace_membership_summary(membership)
                for membership in user.group_workspace_memberships
                if membership.workspace is not None
            ],
        }

    def list_papers(
        self,
        *,
        q: str | None = None,
        user_id: UUID | None = None,
        stage: str | None = None,
        paper_type: PaperType | None = None,
        limit: int = 50,
    ) -> list[dict]:
        statement = (
            select(PaperProfile)
            .options(
                selectinload(PaperProfile.user),
                selectinload(PaperProfile.signal_snapshots),
                selectinload(PaperProfile.research_watch_profiles),
            )
            .order_by(PaperProfile.updated_at.desc(), PaperProfile.created_at.desc())
        )
        if user_id is not None:
            statement = statement.where(PaperProfile.user_id == user_id)
        if stage:
            statement = statement.where(PaperProfile.stage == stage)
        if paper_type:
            statement = statement.where(PaperProfile.type == paper_type)
        papers = list(self.session.scalars(statement))
        filtered = self._filter_papers(papers, q=q)
        return [self._paper_summary(paper) for paper in filtered[:limit]]

    def get_paper_detail(self, paper_id: UUID) -> dict:
        statement = (
            select(PaperProfile)
            .options(
                selectinload(PaperProfile.user),
                selectinload(PaperProfile.signal_snapshots),
                selectinload(PaperProfile.research_watch_profiles).selectinload(
                    ResearchWatchProfile.user
                ),
                selectinload(PaperProfile.research_watch_profiles).selectinload(
                    ResearchWatchProfile.paper
                ),
            )
            .where(PaperProfile.id == paper_id)
        )
        paper = self.session.scalar(statement)
        if paper is None:
            raise NotFoundError(f"paper {paper_id} was not found")
        owner = paper.user
        return {
            "paper": self._paper_summary(paper),
            "owner": {
                "id": owner.id,
                "name": owner.name,
                "email": owner.email,
                "field": owner.field,
            },
            "linked_watch_profiles": [
                self._watch_profile(profile)
                for profile in sorted(
                    paper.research_watch_profiles,
                    key=lambda item: (item.updated_at, item.created_at),
                    reverse=True,
                )
            ],
        }

    def list_watch_profiles(
        self,
        *,
        user_id: UUID | None = None,
        paper_id: UUID | None = None,
        enabled: bool | None = None,
        q: str | None = None,
    ) -> list[dict]:
        statement = (
            select(ResearchWatchProfile)
            .options(
                selectinload(ResearchWatchProfile.user),
                selectinload(ResearchWatchProfile.paper),
            )
            .order_by(
                ResearchWatchProfile.updated_at.desc(),
                ResearchWatchProfile.created_at.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(ResearchWatchProfile.user_id == user_id)
        if paper_id is not None:
            statement = statement.where(ResearchWatchProfile.paper_id == paper_id)
        if enabled is not None:
            statement = statement.where(ResearchWatchProfile.enabled.is_(enabled))
        profiles = list(self.session.scalars(statement))
        filtered = self._filter_watch_profiles(profiles, q=q)
        return [self._watch_profile(profile) for profile in filtered]

    def _user_summary(self, user: UserProfile) -> dict:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "field": user.field,
            "paper_count": len(user.papers),
            "watch_profile_count": len(user.research_watch_profiles),
            "workspace_count": len(user.group_workspace_memberships),
            "latest_digest_issue_summary": self._latest_digest_summary(user.digest_issues),
        }

    def _paper_summary(self, paper: PaperProfile) -> dict:
        latest_signal = self._latest_signal_summary(paper.signal_snapshots)
        linked_watch_profiles = sorted(
            paper.research_watch_profiles,
            key=lambda item: (item.updated_at, item.created_at),
            reverse=True,
        )
        owner = paper.user
        return {
            "id": paper.id,
            "user_id": paper.user_id,
            "user_name": owner.name if owner is not None else None,
            "user_email": owner.email if owner is not None else None,
            "title": paper.title,
            "type": paper.type,
            "stage": paper.stage,
            "venue": paper.venue,
            "priority": paper.priority,
            "next_action": paper.next_action,
            "blocker": paper.blocker,
            "last_touch_at": paper.last_touch_at,
            "progress_percentage": derive_progress_percentage(paper.type),
            "latest_signal_summary": latest_signal,
            "linked_watch_profiles": [
                {
                    "id": profile.id,
                    "label": profile.label,
                    "enabled": profile.enabled,
                    "source_mode": profile.source_mode,
                }
                for profile in linked_watch_profiles
            ],
        }

    def _watch_profile(self, profile: ResearchWatchProfile) -> dict:
        user = profile.user
        paper = profile.paper
        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "paper_id": profile.paper_id,
            "label": profile.label,
            "enabled": profile.enabled,
            "source_mode": profile.source_mode,
            "topics": profile.topics,
            "keywords": profile.keywords,
            "venues": profile.venues,
            "authors_of_interest": profile.authors_of_interest,
            "user_name": user.name if user is not None else None,
            "user_email": user.email if user is not None else None,
            "paper_title": paper.title if paper is not None else None,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }

    def _workspace_membership_summary(self, membership: GroupWorkspaceMember) -> dict:
        workspace = membership.workspace
        return {
            "workspace_id": workspace.id,
            "slug": workspace.slug,
            "name": workspace.name,
            "status": workspace.status,
            "role": membership.role,
            "joined_at": membership.joined_at,
        }

    def _latest_digest_summary(self, issues: list[PulseDigestIssue]) -> dict | None:
        if not issues:
            return None
        latest = max(issues, key=lambda issue: (issue.issue_date, issue.created_at))
        return {
            "id": latest.id,
            "user_id": latest.user_id,
            "issue_date": latest.issue_date,
            "status": latest.status,
            "title": latest.title,
            "summary": latest.summary,
            "selected_card_count": latest.selected_card_count,
            "published_at": latest.published_at,
            "deep_link_path": latest.deep_link_path,
        }

    def _latest_signal_summary(self, signal_snapshots: list[SignalSnapshot]) -> dict | None:
        if not signal_snapshots:
            return None
        latest = max(signal_snapshots, key=lambda snapshot: snapshot.fetched_at)
        return {
            "source": latest.source,
            "citation_count": latest.citation_count,
            "download_count": latest.download_count,
            "read_count": latest.read_count,
            "inclusion_status": latest.inclusion_status,
            "fetched_at": latest.fetched_at,
        }

    def _filter_users(self, users: list[UserProfile], *, q: str | None) -> list[UserProfile]:
        normalized = (q or "").strip().lower()
        if not normalized:
            return users
        return [
            user
            for user in users
            if self._matches_query(
                normalized,
                user.name,
                user.email,
                user.field,
            )
        ]

    def _filter_papers(self, papers: list[PaperProfile], *, q: str | None) -> list[PaperProfile]:
        normalized = (q or "").strip().lower()
        if not normalized:
            return papers
        return [
            paper
            for paper in papers
            if self._matches_query(
                normalized,
                paper.title,
                paper.stage,
                paper.venue,
                paper.next_action,
                paper.blocker,
                paper.user.name if paper.user is not None else None,
                paper.user.email if paper.user is not None else None,
            )
        ]

    def _filter_watch_profiles(
        self,
        profiles: list[ResearchWatchProfile],
        *,
        q: str | None,
    ) -> list[ResearchWatchProfile]:
        normalized = (q or "").strip().lower()
        if not normalized:
            return profiles
        return [
            profile
            for profile in profiles
            if self._matches_query(
                normalized,
                profile.label,
                profile.user.name if profile.user is not None else None,
                profile.user.email if profile.user is not None else None,
                profile.paper.title if profile.paper is not None else None,
                *profile.topics,
                *profile.keywords,
                *profile.venues,
                *(profile.authors_of_interest or []),
            )
        ]

    def _matches_query(self, normalized_query: str, *values: str | None) -> bool:
        for value in values:
            if value and normalized_query in value.lower():
                return True
        return False
