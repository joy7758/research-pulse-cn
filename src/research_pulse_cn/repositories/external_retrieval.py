"""Persistence operations for external retrieval planning and execution."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    ExternalRetrievalPlan,
    ExternalRetrievalRun,
    ExternalRetrievedRecord,
)
from research_pulse_cn.domain.enums import (
    ExternalRetrievalPlanStatus,
    ExternalRetrievalRunStatus,
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


class ExternalRetrievalRunRepository:
    """Persistence operations for retrieval execution runs."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run: ExternalRetrievalRun) -> ExternalRetrievalRun:
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def get(self, run_id: UUID) -> ExternalRetrievalRun | None:
        statement = (
            select(ExternalRetrievalRun)
            .options(
                selectinload(ExternalRetrievalRun.plan),
                selectinload(ExternalRetrievalRun.results),
            )
            .where(ExternalRetrievalRun.id == run_id)
        )
        return self.session.scalar(statement)

    def list(
        self,
        *,
        user_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
        status: ExternalRetrievalRunStatus | None = None,
        plan_id: UUID | None = None,
    ) -> list[ExternalRetrievalRun]:
        statement = (
            select(ExternalRetrievalRun)
            .options(selectinload(ExternalRetrievalRun.plan))
            .order_by(
                ExternalRetrievalRun.updated_at.desc(),
                ExternalRetrievalRun.created_at.desc(),
            )
        )
        if user_id is not None:
            statement = statement.where(ExternalRetrievalRun.user_id == user_id)
        if source_kind is not None:
            statement = statement.where(ExternalRetrievalRun.source_kind == source_kind)
        if retrieval_scope is not None:
            statement = statement.where(ExternalRetrievalRun.retrieval_scope == retrieval_scope)
        if status is not None:
            statement = statement.where(ExternalRetrievalRun.status == status)
        if plan_id is not None:
            statement = statement.where(ExternalRetrievalRun.plan_id == plan_id)
        return list(self.session.scalars(statement))

    def latest_successful_for_plan_since(
        self,
        *,
        plan_id: UUID,
        not_before: datetime,
    ) -> ExternalRetrievalRun | None:
        statement = (
            select(ExternalRetrievalRun)
            .options(
                selectinload(ExternalRetrievalRun.plan),
                selectinload(ExternalRetrievalRun.results),
            )
            .where(
                ExternalRetrievalRun.plan_id == plan_id,
                ExternalRetrievalRun.status == ExternalRetrievalRunStatus.COMPLETED,
                ExternalRetrievalRun.finished_at.is_not(None),
                ExternalRetrievalRun.finished_at >= not_before,
            )
            .order_by(
                ExternalRetrievalRun.finished_at.desc(), ExternalRetrievalRun.created_at.desc()
            )
        )
        return self.session.scalar(statement)


class ExternalRetrievedRecordRepository:
    """Persistence operations for normalized retrieval results."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_many(
        self,
        records: list[ExternalRetrievedRecord],
    ) -> list[ExternalRetrievedRecord]:
        self.session.add_all(records)
        self.session.flush()
        for record in records:
            self.session.refresh(record)
        return records

    def list(
        self,
        *,
        user_id: UUID | None = None,
        run_id: UUID | None = None,
        plan_id: UUID | None = None,
        source_kind: ExternalRetrievalSourceKind | None = None,
        retrieval_scope: ExternalRetrievalScope | None = None,
    ) -> list[ExternalRetrievedRecord]:
        statement = select(ExternalRetrievedRecord).order_by(
            ExternalRetrievedRecord.created_at.desc(),
            ExternalRetrievedRecord.sort_order.asc(),
        )
        if user_id is not None:
            statement = statement.where(ExternalRetrievedRecord.user_id == user_id)
        if run_id is not None:
            statement = statement.where(ExternalRetrievedRecord.run_id == run_id)
        if plan_id is not None:
            statement = statement.where(ExternalRetrievedRecord.plan_id == plan_id)
        if source_kind is not None:
            statement = statement.where(ExternalRetrievedRecord.source_kind == source_kind)
        if retrieval_scope is not None:
            statement = statement.where(ExternalRetrievedRecord.retrieval_scope == retrieval_scope)
        return list(self.session.scalars(statement))

    def list_recent_completed_records(
        self,
        *,
        user_id: UUID,
        retrieval_scope: ExternalRetrievalScope,
        not_before: datetime,
    ) -> list[ExternalRetrievedRecord]:
        statement = (
            select(ExternalRetrievedRecord)
            .join(ExternalRetrievedRecord.run)
            .options(
                selectinload(ExternalRetrievedRecord.run).selectinload(ExternalRetrievalRun.plan),
                selectinload(ExternalRetrievedRecord.plan).selectinload(
                    ExternalRetrievalPlan.paper
                ),
            )
            .where(
                ExternalRetrievedRecord.user_id == user_id,
                ExternalRetrievedRecord.retrieval_scope == retrieval_scope,
                ExternalRetrievalRun.status == ExternalRetrievalRunStatus.COMPLETED,
                or_(
                    ExternalRetrievedRecord.created_at >= not_before,
                    ExternalRetrievalRun.finished_at >= not_before,
                ),
            )
            .order_by(
                ExternalRetrievalRun.finished_at.desc(),
                ExternalRetrievedRecord.created_at.desc(),
                ExternalRetrievedRecord.sort_order.asc(),
            )
        )
        return list(self.session.scalars(statement))
