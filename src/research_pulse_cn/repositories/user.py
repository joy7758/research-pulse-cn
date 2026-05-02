"""User repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_pulse_cn.db.models import UserProfile


class UserRepository:
    """Persistence operations for user profiles."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[UserProfile]:
        return list(
            self.session.scalars(select(UserProfile).order_by(UserProfile.created_at.desc()))
        )

    def get(self, user_id: UUID) -> UserProfile | None:
        return self.session.get(UserProfile, user_id)

    def add(self, user: UserProfile) -> UserProfile:
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user

    def delete(self, user: UserProfile) -> None:
        self.session.delete(user)
