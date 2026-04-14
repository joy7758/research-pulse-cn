"""Subscription policy repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from research_pulse_cn.db.models import SubscriptionPolicy


class SubscriptionPolicyRepository:
    """Persistence operations for subscription policies."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self, *, user_id: UUID | None = None, enabled_only: bool = False
    ) -> list[SubscriptionPolicy]:
        statement = select(SubscriptionPolicy).order_by(SubscriptionPolicy.created_at.desc())
        if user_id:
            statement = statement.where(SubscriptionPolicy.user_id == user_id)
        if enabled_only:
            statement = statement.where(SubscriptionPolicy.enabled.is_(True))
        return list(self.session.scalars(statement))

    def get(self, policy_id: UUID) -> SubscriptionPolicy | None:
        return self.session.get(SubscriptionPolicy, policy_id)

    def add(self, policy: SubscriptionPolicy) -> SubscriptionPolicy:
        self.session.add(policy)
        self.session.flush()
        self.session.refresh(policy)
        return policy

    def delete(self, policy: SubscriptionPolicy) -> None:
        self.session.delete(policy)
