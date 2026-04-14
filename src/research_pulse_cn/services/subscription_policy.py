"""Subscription policy application service."""

from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.db.models import SubscriptionPolicy
from research_pulse_cn.repositories.subscription_policy import SubscriptionPolicyRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.subscription_policy import (
    SubscriptionPolicyCreate,
    SubscriptionPolicyUpdate,
)
from research_pulse_cn.services.common import commit_session


class SubscriptionPolicyService:
    """Use-case layer for subscription policies."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SubscriptionPolicyRepository(session)
        self.user_repository = UserRepository(session)

    def list_policies(self, *, user_id: UUID | None = None) -> list[SubscriptionPolicy]:
        return self.repository.list(user_id=user_id)

    def get_policy(self, policy_id: UUID) -> SubscriptionPolicy:
        policy = self.repository.get(policy_id)
        if policy is None:
            raise NotFoundError(f"subscription policy {policy_id} was not found")
        return policy

    def create_policy(self, payload: SubscriptionPolicyCreate) -> SubscriptionPolicy:
        if self.user_repository.get(payload.user_id) is None:
            raise NotFoundError(f"user {payload.user_id} was not found")
        policy = SubscriptionPolicy(**payload.model_dump())
        self.repository.add(policy)
        commit_session(self.session)
        return self.get_policy(policy.id)

    def update_policy(
        self, policy_id: UUID, payload: SubscriptionPolicyUpdate
    ) -> SubscriptionPolicy:
        policy = self.get_policy(policy_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(policy, field, value)
        commit_session(self.session)
        return self.get_policy(policy_id)

    def delete_policy(self, policy_id: UUID) -> None:
        policy = self.get_policy(policy_id)
        self.repository.delete(policy)
        commit_session(self.session)
