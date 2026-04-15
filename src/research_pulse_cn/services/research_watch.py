"""Services for compact research watch profiles."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import ResearchWatchProfile
from research_pulse_cn.domain.enums import ResearchWatchProfileSourceMode
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.research_watch import ResearchWatchProfileRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.pulse_input import (
    EffectiveWatchSeedsRead,
    ResearchWatchProfileCreate,
    ResearchWatchProfileUpdate,
)
from research_pulse_cn.services.common import commit_session

logger = logging.getLogger(__name__)


class ResearchWatchProfileService:
    """Create and resolve watch profiles for future pulse retrieval."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ResearchWatchProfileRepository(session)
        self.user_repository = UserRepository(session)
        self.paper_repository = PaperRepository(session)
        self.metrics = get_metrics()

    def list_profiles(self, *, user_id: UUID | None = None) -> list[ResearchWatchProfile]:
        return self.repository.list(user_id=user_id)

    def get_profile(self, profile_id: UUID) -> ResearchWatchProfile:
        profile = self.repository.get(profile_id)
        if profile is None:
            raise NotFoundError(f"research watch profile {profile_id} was not found")
        return profile

    def create_profile(self, payload: ResearchWatchProfileCreate) -> ResearchWatchProfile:
        self._validate_profile_owner(payload.user_id, payload.paper_id)
        label = payload.label.strip()
        if not label:
            raise ValidationFailedError("research watch profile label must not be empty")
        profile = ResearchWatchProfile(
            user_id=payload.user_id,
            paper_id=payload.paper_id,
            label=label,
            enabled=payload.enabled,
            source_mode=ResearchWatchProfileSourceMode.MANUAL,
            topics=_clean_terms(payload.topics),
            keywords=_clean_terms(payload.keywords),
            venues=_clean_terms(payload.venues),
            authors_of_interest=_optional_terms(payload.authors_of_interest),
        )
        self.repository.add(profile)
        commit_session(self.session)
        self.metrics.increment("research_watch_profiles_total")
        with bind_log_context(user_id=payload.user_id):
            logger.info(
                "created research watch profile",
                extra={"paper_id": str(payload.paper_id) if payload.paper_id else None},
            )
        return self.get_profile(profile.id)

    def update_profile(
        self,
        profile_id: UUID,
        payload: ResearchWatchProfileUpdate,
    ) -> ResearchWatchProfile:
        profile = self.get_profile(profile_id)
        if payload.label is not None:
            label = payload.label.strip()
            if not label:
                raise ValidationFailedError("research watch profile label must not be empty")
            profile.label = label
        if payload.enabled is not None:
            profile.enabled = payload.enabled
        if payload.topics is not None:
            profile.topics = _clean_terms(payload.topics)
        if payload.keywords is not None:
            profile.keywords = _clean_terms(payload.keywords)
        if payload.venues is not None:
            profile.venues = _clean_terms(payload.venues)
        if payload.authors_of_interest is not None:
            profile.authors_of_interest = _optional_terms(payload.authors_of_interest)
        commit_session(self.session)
        return self.get_profile(profile.id)

    def delete_profile(self, profile_id: UUID) -> None:
        profile = self.get_profile(profile_id)
        self.repository.delete(profile)
        commit_session(self.session)

    def bootstrap_from_paper(self, paper_id: UUID) -> ResearchWatchProfile:
        paper = self.paper_repository.get(paper_id)
        if paper is None:
            raise NotFoundError(f"paper {paper_id} was not found")
        authors = paper.identifiers.get("authors") if isinstance(paper.identifiers, dict) else None
        authors_of_interest = _optional_terms(authors) if isinstance(authors, list) else None
        profile = ResearchWatchProfile(
            user_id=paper.user_id,
            paper_id=paper.id,
            label=paper.title.strip(),
            enabled=True,
            source_mode=ResearchWatchProfileSourceMode.PAPER_BOOTSTRAP,
            topics=[],
            keywords=_clean_terms([paper.title]),
            venues=_clean_terms([paper.venue] if paper.venue else []),
            authors_of_interest=authors_of_interest,
        )
        self.repository.add(profile)
        commit_session(self.session)
        self.metrics.increment("research_watch_profiles_total")
        with bind_log_context(user_id=paper.user_id):
            logger.info(
                "bootstrapped research watch profile",
                extra={"paper_id": str(paper.id)},
            )
        return self.get_profile(profile.id)

    def effective_watch_seeds(self, *, user_id: UUID) -> EffectiveWatchSeedsRead:
        profiles = self.repository.list(user_id=user_id, enabled_only=True)
        return self.effective_watch_seeds_from_profiles(profiles)

    def effective_watch_seeds_from_profiles(
        self,
        profiles: list[ResearchWatchProfile],
    ) -> EffectiveWatchSeedsRead:
        return EffectiveWatchSeedsRead(
            topics=_sorted_terms(term for profile in profiles for term in profile.topics),
            keywords=_sorted_terms(term for profile in profiles for term in profile.keywords),
            venues=_sorted_terms(term for profile in profiles for term in profile.venues),
            authors_of_interest=_sorted_terms(
                term for profile in profiles for term in (profile.authors_of_interest or [])
            ),
        )

    def _validate_profile_owner(self, user_id: UUID, paper_id: UUID | None) -> None:
        if self.user_repository.get(user_id) is None:
            raise NotFoundError(f"user {user_id} was not found")
        if paper_id is None:
            return
        paper = self.paper_repository.get(paper_id)
        if paper is None or paper.user_id != user_id:
            raise NotFoundError(f"paper {paper_id} was not found")


def _clean_terms(values: list[str]) -> list[str]:
    return _sorted_terms(values)


def _optional_terms(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    cleaned = _sorted_terms(values)
    return cleaned or None


def _sorted_terms(values) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        if value is None:
            continue
        cleaned = str(value).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        seen.setdefault(key, cleaned)
    return [seen[key] for key in sorted(seen)]
