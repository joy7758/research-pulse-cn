"""Paper and paper-adjacent repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import PaperProfile, ProgressEvent, SignalSnapshot


class PaperRepository:
    """Persistence operations for paper profiles and related child rows."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, user_id: UUID | None = None) -> list[PaperProfile]:
        statement = (
            select(PaperProfile)
            .execution_options(populate_existing=True)
            .options(
                selectinload(PaperProfile.progress_events),
                selectinload(PaperProfile.signal_snapshots),
            )
            .order_by(PaperProfile.updated_at.desc())
        )
        if user_id:
            statement = statement.where(PaperProfile.user_id == user_id)
        return list(self.session.scalars(statement))

    def get(self, paper_id: UUID) -> PaperProfile | None:
        statement = (
            select(PaperProfile)
            .execution_options(populate_existing=True)
            .options(
                selectinload(PaperProfile.progress_events),
                selectinload(PaperProfile.signal_snapshots),
            )
            .where(PaperProfile.id == paper_id)
        )
        return self.session.scalar(statement)

    def add(self, paper: PaperProfile) -> PaperProfile:
        self.session.add(paper)
        self.session.flush()
        self.session.refresh(paper)
        return paper

    def delete(self, paper: PaperProfile) -> None:
        self.session.delete(paper)

    def list_progress_events(self, paper_id: UUID) -> list[ProgressEvent]:
        statement = (
            select(ProgressEvent)
            .where(ProgressEvent.paper_id == paper_id)
            .order_by(ProgressEvent.happened_at.desc())
        )
        return list(self.session.scalars(statement))

    def add_progress_event(self, event: ProgressEvent) -> ProgressEvent:
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def list_signal_snapshots(self, paper_id: UUID) -> list[SignalSnapshot]:
        statement = (
            select(SignalSnapshot)
            .where(SignalSnapshot.paper_id == paper_id)
            .order_by(SignalSnapshot.fetched_at.desc())
        )
        return list(self.session.scalars(statement))

    def add_signal_snapshot(self, snapshot: SignalSnapshot) -> SignalSnapshot:
        self.session.add(snapshot)
        self.session.flush()
        self.session.refresh(snapshot)
        return snapshot
