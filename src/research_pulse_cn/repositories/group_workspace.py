"""Persistence operations for group workspaces and result share grants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    GroupWorkspace,
    GroupWorkspaceMember,
    GroupWorkspacePaper,
    PaperProfile,
    PulseDigestIssue,
    PulseDigestItem,
    ResultShareGrant,
)
from research_pulse_cn.domain.enums import (
    GroupWorkspaceStatus,
    ResultShareGrantStatus,
    ResultShareKind,
)


class GroupWorkspaceRepository:
    """Load and persist group workspace records and result share grants."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _workspace_load_options(self):
        return (
            selectinload(GroupWorkspace.created_by_admin),
            selectinload(GroupWorkspace.members).selectinload(GroupWorkspaceMember.user),
            selectinload(GroupWorkspace.papers)
            .selectinload(GroupWorkspacePaper.paper)
            .selectinload(PaperProfile.user),
            selectinload(GroupWorkspace.papers)
            .selectinload(GroupWorkspacePaper.paper)
            .selectinload(PaperProfile.signal_snapshots),
            selectinload(GroupWorkspace.papers)
            .selectinload(GroupWorkspacePaper.paper)
            .selectinload(PaperProfile.progress_events),
        )

    def _result_share_load_options(self):
        return (
            selectinload(ResultShareGrant.workspace)
            .selectinload(GroupWorkspace.members)
            .selectinload(GroupWorkspaceMember.user),
            selectinload(ResultShareGrant.workspace)
            .selectinload(GroupWorkspace.papers)
            .selectinload(GroupWorkspacePaper.paper)
            .selectinload(PaperProfile.user),
            selectinload(ResultShareGrant.workspace)
            .selectinload(GroupWorkspace.papers)
            .selectinload(GroupWorkspacePaper.paper)
            .selectinload(PaperProfile.signal_snapshots),
            selectinload(ResultShareGrant.digest_issue)
            .selectinload(PulseDigestIssue.items)
            .selectinload(PulseDigestItem.source_paper),
            selectinload(ResultShareGrant.digest_issue).selectinload(PulseDigestIssue.user),
            selectinload(ResultShareGrant.paper).selectinload(PaperProfile.user),
            selectinload(ResultShareGrant.paper).selectinload(PaperProfile.signal_snapshots),
            selectinload(ResultShareGrant.paper).selectinload(PaperProfile.progress_events),
            selectinload(ResultShareGrant.issued_by_admin),
        )

    def list_workspaces(
        self,
        *,
        status: GroupWorkspaceStatus | None = None,
        user_id: UUID | None = None,
    ) -> list[GroupWorkspace]:
        statement = (
            select(GroupWorkspace)
            .options(*self._workspace_load_options())
            .order_by(GroupWorkspace.created_at.desc(), GroupWorkspace.id.desc())
        )
        if status is not None:
            statement = statement.where(GroupWorkspace.status == status)
        workspaces = list(self.session.scalars(statement))
        if user_id is not None:
            workspaces = [
                workspace
                for workspace in workspaces
                if any(member.user_id == user_id for member in workspace.members)
            ]
        return workspaces

    def get_workspace(self, workspace_id: UUID) -> GroupWorkspace | None:
        statement = (
            select(GroupWorkspace)
            .options(*self._workspace_load_options())
            .where(GroupWorkspace.id == workspace_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_workspace(self, workspace: GroupWorkspace) -> GroupWorkspace:
        self.session.add(workspace)
        return workspace

    def get_workspace_member(
        self,
        *,
        workspace_id: UUID,
        member_id: UUID,
    ) -> GroupWorkspaceMember | None:
        statement = (
            select(GroupWorkspaceMember)
            .options(selectinload(GroupWorkspaceMember.user))
            .where(
                GroupWorkspaceMember.workspace_id == workspace_id,
                GroupWorkspaceMember.id == member_id,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_workspace_member(self, member: GroupWorkspaceMember) -> GroupWorkspaceMember:
        self.session.add(member)
        return member

    def delete_workspace_member(self, member: GroupWorkspaceMember) -> None:
        self.session.delete(member)

    def get_workspace_paper(
        self,
        *,
        workspace_id: UUID,
        paper_id: UUID,
    ) -> GroupWorkspacePaper | None:
        statement = (
            select(GroupWorkspacePaper)
            .options(
                selectinload(GroupWorkspacePaper.paper).selectinload(PaperProfile.user),
                selectinload(GroupWorkspacePaper.paper).selectinload(PaperProfile.signal_snapshots),
                selectinload(GroupWorkspacePaper.added_by_admin),
            )
            .where(
                GroupWorkspacePaper.workspace_id == workspace_id,
                GroupWorkspacePaper.paper_id == paper_id,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_workspace_paper(self, workspace_paper: GroupWorkspacePaper) -> GroupWorkspacePaper:
        self.session.add(workspace_paper)
        return workspace_paper

    def delete_workspace_paper(self, workspace_paper: GroupWorkspacePaper) -> None:
        self.session.delete(workspace_paper)

    def list_result_share_grants(
        self,
        *,
        workspace_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        status: ResultShareGrantStatus | None = None,
    ) -> list[ResultShareGrant]:
        statement = (
            select(ResultShareGrant)
            .options(*self._result_share_load_options())
            .order_by(ResultShareGrant.created_at.desc(), ResultShareGrant.id.desc())
        )
        if workspace_id is not None:
            statement = statement.where(ResultShareGrant.workspace_id == workspace_id)
        if share_kind is not None:
            statement = statement.where(ResultShareGrant.share_kind == share_kind)
        if status is not None:
            statement = statement.where(ResultShareGrant.status == status)
        return list(self.session.scalars(statement))

    def get_result_share_grant(self, grant_id: UUID) -> ResultShareGrant | None:
        statement = (
            select(ResultShareGrant)
            .options(*self._result_share_load_options())
            .where(ResultShareGrant.id == grant_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_result_share_grant_by_token_hash(self, token_hash: str) -> ResultShareGrant | None:
        statement = (
            select(ResultShareGrant)
            .options(*self._result_share_load_options())
            .where(ResultShareGrant.token_hash == token_hash)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_result_share_grant(self, grant: ResultShareGrant) -> ResultShareGrant:
        self.session.add(grant)
        return grant
