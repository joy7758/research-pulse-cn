"""Paper application service."""

from datetime import UTC
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.core.errors import NotFoundError
from research_pulse_cn.db.models import PaperProfile, ProgressEvent, SignalSnapshot
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.schemas.paper import (
    PaperProfileCreate,
    PaperProfileUpdate,
    ProgressEventCreate,
    SignalSnapshotCreate,
)
from research_pulse_cn.services.common import commit_session


class PaperService:
    """Use-case layer for paper profiles and child entities."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.paper_repository = PaperRepository(session)
        self.user_repository = UserRepository(session)

    def list_papers(self, *, user_id: UUID | None = None) -> list[PaperProfile]:
        return self.paper_repository.list(user_id=user_id)

    def get_paper(self, paper_id: UUID) -> PaperProfile:
        paper = self.paper_repository.get(paper_id)
        if paper is None:
            raise NotFoundError(f"paper {paper_id} was not found")
        return paper

    def create_paper(self, payload: PaperProfileCreate) -> PaperProfile:
        if self.user_repository.get(payload.user_id) is None:
            raise NotFoundError(f"user {payload.user_id} was not found")
        paper = PaperProfile(**payload.model_dump())
        self.paper_repository.add(paper)
        commit_session(self.session)
        return self.get_paper(paper.id)

    def update_paper(self, paper_id: UUID, payload: PaperProfileUpdate) -> PaperProfile:
        paper = self.get_paper(paper_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(paper, field, value)
        commit_session(self.session)
        return self.get_paper(paper_id)

    def delete_paper(self, paper_id: UUID) -> None:
        paper = self.get_paper(paper_id)
        self.paper_repository.delete(paper)
        commit_session(self.session)

    def list_progress_events(self, paper_id: UUID) -> list[ProgressEvent]:
        self.get_paper(paper_id)
        return self.paper_repository.list_progress_events(paper_id)

    def add_progress_event(self, paper_id: UUID, payload: ProgressEventCreate) -> ProgressEvent:
        paper = self.get_paper(paper_id)
        event = ProgressEvent(paper_id=paper.id, **payload.model_dump())
        paper.stage = payload.stage
        paper.last_touch_at = payload.happened_at.astimezone(UTC)
        self.paper_repository.add_progress_event(event)
        commit_session(self.session)
        return event

    def list_signal_snapshots(self, paper_id: UUID) -> list[SignalSnapshot]:
        self.get_paper(paper_id)
        return self.paper_repository.list_signal_snapshots(paper_id)

    def add_signal_snapshot(self, paper_id: UUID, payload: SignalSnapshotCreate) -> SignalSnapshot:
        paper = self.get_paper(paper_id)
        snapshot = SignalSnapshot(paper_id=paper.id, **payload.model_dump())
        self.paper_repository.add_signal_snapshot(snapshot)
        commit_session(self.session)
        return snapshot
