"""Persistence operations for research watch profiles."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import ResearchWatchProfile


class ResearchWatchProfileRepository:
    """Persistence operations for research watch profiles."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        user_id: UUID | None = None,
        enabled_only: bool = False,
    ) -> list[ResearchWatchProfile]:
        statement = (
            select(ResearchWatchProfile)
            .options(selectinload(ResearchWatchProfile.paper))
            .order_by(
                ResearchWatchProfile.updated_at.desc(),
                ResearchWatchProfile.created_at.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(ResearchWatchProfile.user_id == user_id)
        if enabled_only:
            statement = statement.where(ResearchWatchProfile.enabled.is_(True))
        return list(self.session.scalars(statement))

    def get(self, profile_id: UUID) -> ResearchWatchProfile | None:
        statement = (
            select(ResearchWatchProfile)
            .options(selectinload(ResearchWatchProfile.paper))
            .where(ResearchWatchProfile.id == profile_id)
        )
        return self.session.scalar(statement)

    def add(self, profile: ResearchWatchProfile) -> ResearchWatchProfile:
        self.session.add(profile)
        self.session.flush()
        self.session.refresh(profile)
        return profile

    def delete(self, profile: ResearchWatchProfile) -> None:
        self.session.delete(profile)
