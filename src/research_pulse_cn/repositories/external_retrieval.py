"""Persistence operations for external retrieval planning."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import ExternalRetrievalPlan
from research_pulse_cn.domain.enums import (
    ExternalRetrievalPlanStatus,
    ExternalRetrievalScope,
    ExternalRetrievalSourceKind,
)


class ExternalRetrievalPlanRepository:
    """Persistence operations for source-specific retrieval plans."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, plan: ExternalRetrievalPlan) -> ExternalRetrievalPlan:
        self.session.add(plan)
        self.session.flush()
        self.session.refresh(plan)
        return plan

    def get(self, plan_id: UUID) -> ExternalRetrievalPlan | None:
        statement = (
            select(ExternalRetrievalPlan)
            .options(
                selectinload(ExternalRetrievalPlan.paper),
                selectinload(ExternalRetrievalPlan.watch_profile),
            )
            .where(ExternalRetrievalPlan.id == plan_id)
        )
        return self.session.scalar(statement)

    def get_by_plan_hash(self, plan_hash: str) -> ExternalRetrievalPlan | None:
        statement = (
            select(ExternalRetrievalPlan)
            .options(
                selectinload(ExternalRetrievalPlan.paper),
                selectinload(ExternalRetrievalPlan.watch_profile),
            )
            .where(ExternalRetrievalPlan.plan_hash == plan_hash)
        )
        return self.session.scalar(statement)

    def list(
        self,
        *,
        user_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
        status: ExternalRetrievalPlanStatus | None = None,
        paper_id: UUID | None = None,
    ) -> list[ExternalRetrievalPlan]:
        statement = (
            select(ExternalRetrievalPlan)
            .options(
                selectinload(ExternalRetrievalPlan.paper),
                selectinload(ExternalRetrievalPlan.watch_profile),
            )
            .order_by(
                ExternalRetrievalPlan.updated_at.desc(),
                ExternalRetrievalPlan.created_at.desc(),
                ExternalRetrievalPlan.plan_label.asc(),
            )
        )
        if user_id is not None:
            statement = statement.where(ExternalRetrievalPlan.user_id == user_id)
        if source_kind is not None:
            statement = statement.where(ExternalRetrievalPlan.source_kind == source_kind)
        if retrieval_scope is not None:
            statement = statement.where(ExternalRetrievalPlan.retrieval_scope == retrieval_scope)
        if status is not None:
            statement = statement.where(ExternalRetrievalPlan.status == status)
        if paper_id is not None:
            statement = statement.where(ExternalRetrievalPlan.paper_id == paper_id)
        return list(self.session.scalars(statement))
