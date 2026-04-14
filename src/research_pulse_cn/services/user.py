"""User application service."""

from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.db.models import UserProfile
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.user import UserProfileCreate, UserProfileUpdate
from research_pulse_cn.services.common import commit_session


class UserService:
    """Use-case layer for user profiles."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UserRepository(session)

    def list_users(self) -> list[UserProfile]:
        return self.repository.list()

    def get_user(self, user_id: UUID) -> UserProfile:
        user = self.repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        return user

    def create_user(self, payload: UserProfileCreate) -> UserProfile:
        user = UserProfile(**payload.model_dump())
        self.repository.add(user)
        commit_session(self.session)
        self.session.refresh(user)
        return user

    def update_user(self, user_id: UUID, payload: UserProfileUpdate) -> UserProfile:
        user = self.get_user(user_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        commit_session(self.session)
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: UUID) -> None:
        user = self.get_user(user_id)
        self.repository.delete(user)
        commit_session(self.session)
