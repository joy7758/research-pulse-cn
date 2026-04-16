"""Persistence operations for group workspaces and result share grants."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from research_pulse_cn.db.models import (
    GroupWorkspace,
    GroupWorkspaceInviteClaim,
    GroupWorkspaceInviteGrant,
    GroupWorkspaceMember,
    GroupWorkspacePaper,
    GroupWorkspaceResultCollectRecord,
    PaperProfile,
    PulseDigestIssue,
    PulseDigestItem,
    ResultShareGrant,
)
from research_pulse_cn.domain.enums import (
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
    GroupWorkspaceResultCollectStatus,
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

    def _invite_grant_load_options(self):
        return (
            selectinload(GroupWorkspaceInviteGrant.workspace),
            selectinload(GroupWorkspaceInviteGrant.issued_by_admin),
        )

    def _invite_claim_load_options(self):
        return (
            selectinload(GroupWorkspaceInviteClaim.invite_grant).options(
                *self._invite_grant_load_options()
            ),
            selectinload(GroupWorkspaceInviteClaim.workspace),
            selectinload(GroupWorkspaceInviteClaim.user),
            selectinload(GroupWorkspaceInviteClaim.membership),
        )

    def _result_collect_record_load_options(self):
        return (
            selectinload(GroupWorkspaceResultCollectRecord.workspace),
            selectinload(GroupWorkspaceResultCollectRecord.user),
            selectinload(GroupWorkspaceResultCollectRecord.result_share_grant).options(
                *self._result_share_load_options()
            ),
            selectinload(GroupWorkspaceResultCollectRecord.digest_issue),
            selectinload(GroupWorkspaceResultCollectRecord.source_paper).selectinload(
                PaperProfile.user
            ),
            selectinload(GroupWorkspaceResultCollectRecord.collected_paper).selectinload(
                PaperProfile.user
            ),
            selectinload(GroupWorkspaceResultCollectRecord.collected_paper).selectinload(
                PaperProfile.signal_snapshots
            ),
            selectinload(GroupWorkspaceResultCollectRecord.collected_paper).selectinload(
                PaperProfile.progress_events
            ),
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

    def get_workspace_member_for_user(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> GroupWorkspaceMember | None:
        statement = (
            select(GroupWorkspaceMember)
            .options(
                selectinload(GroupWorkspaceMember.user),
                selectinload(GroupWorkspaceMember.workspace),
            )
            .where(
                GroupWorkspaceMember.workspace_id == workspace_id,
                GroupWorkspaceMember.user_id == user_id,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_workspace_memberships_for_user(self, *, user_id: UUID) -> list[GroupWorkspaceMember]:
        statement = (
            select(GroupWorkspaceMember)
            .options(selectinload(GroupWorkspaceMember.workspace))
            .where(GroupWorkspaceMember.user_id == user_id)
            .order_by(GroupWorkspaceMember.joined_at.desc(), GroupWorkspaceMember.id.desc())
        )
        return list(self.session.scalars(statement))

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

    def list_invite_grants(
        self,
        *,
        workspace_id: UUID | None = None,
        status: GroupWorkspaceInviteGrantStatus | None = None,
        role_to_assign: GroupWorkspaceInviteRole | None = None,
    ) -> list[GroupWorkspaceInviteGrant]:
        statement = (
            select(GroupWorkspaceInviteGrant)
            .options(*self._invite_grant_load_options())
            .order_by(
                GroupWorkspaceInviteGrant.created_at.desc(),
                GroupWorkspaceInviteGrant.id.desc(),
            )
        )
        if workspace_id is not None:
            statement = statement.where(GroupWorkspaceInviteGrant.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(GroupWorkspaceInviteGrant.status == status)
        if role_to_assign is not None:
            statement = statement.where(GroupWorkspaceInviteGrant.role_to_assign == role_to_assign)
        return list(self.session.scalars(statement))

    def get_invite_grant(self, grant_id: UUID) -> GroupWorkspaceInviteGrant | None:
        statement = (
            select(GroupWorkspaceInviteGrant)
            .options(*self._invite_grant_load_options())
            .where(GroupWorkspaceInviteGrant.id == grant_id)
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_invite_grant_by_token_hash(self, token_hash: str) -> GroupWorkspaceInviteGrant | None:
        statement = (
            select(GroupWorkspaceInviteGrant)
            .options(*self._invite_grant_load_options())
            .where(GroupWorkspaceInviteGrant.token_hash == token_hash)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_invite_grant(self, grant: GroupWorkspaceInviteGrant) -> GroupWorkspaceInviteGrant:
        self.session.add(grant)
        return grant

    def list_invite_claims(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        claim_status: GroupWorkspaceInviteClaimStatus | None = None,
    ) -> list[GroupWorkspaceInviteClaim]:
        statement = (
            select(GroupWorkspaceInviteClaim)
            .options(*self._invite_claim_load_options())
            .order_by(
                GroupWorkspaceInviteClaim.created_at.desc(),
                GroupWorkspaceInviteClaim.id.desc(),
            )
        )
        if workspace_id is not None:
            statement = statement.where(GroupWorkspaceInviteClaim.workspace_id == workspace_id)
        if user_id is not None:
            statement = statement.where(GroupWorkspaceInviteClaim.user_id == user_id)
        if claim_status is not None:
            statement = statement.where(GroupWorkspaceInviteClaim.claim_status == claim_status)
        return list(self.session.scalars(statement))

    def get_invite_claim(
        self,
        *,
        invite_grant_id: UUID,
        user_id: UUID,
    ) -> GroupWorkspaceInviteClaim | None:
        statement = (
            select(GroupWorkspaceInviteClaim)
            .options(*self._invite_claim_load_options())
            .where(
                GroupWorkspaceInviteClaim.invite_grant_id == invite_grant_id,
                GroupWorkspaceInviteClaim.user_id == user_id,
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_invite_claim(self, claim: GroupWorkspaceInviteClaim) -> GroupWorkspaceInviteClaim:
        self.session.add(claim)
        return claim

    def list_result_collect_records(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        result_share_grant_id: UUID | None = None,
        status: GroupWorkspaceResultCollectStatus | None = None,
        collected_paper_id: UUID | None = None,
    ) -> list[GroupWorkspaceResultCollectRecord]:
        statement = (
            select(GroupWorkspaceResultCollectRecord)
            .options(*self._result_collect_record_load_options())
            .order_by(
                GroupWorkspaceResultCollectRecord.created_at.desc(),
                GroupWorkspaceResultCollectRecord.id.desc(),
            )
        )
        if workspace_id is not None:
            statement = statement.where(
                GroupWorkspaceResultCollectRecord.workspace_id == workspace_id
            )
        if user_id is not None:
            statement = statement.where(GroupWorkspaceResultCollectRecord.user_id == user_id)
        if result_share_grant_id is not None:
            statement = statement.where(
                GroupWorkspaceResultCollectRecord.result_share_grant_id == result_share_grant_id
            )
        if status is not None:
            statement = statement.where(GroupWorkspaceResultCollectRecord.status == status)
        if collected_paper_id is not None:
            statement = statement.where(
                GroupWorkspaceResultCollectRecord.collected_paper_id == collected_paper_id
            )
        return list(self.session.scalars(statement))

    def get_result_collect_record_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> GroupWorkspaceResultCollectRecord | None:
        statement = (
            select(GroupWorkspaceResultCollectRecord)
            .options(*self._result_collect_record_load_options())
            .where(GroupWorkspaceResultCollectRecord.idempotency_key == idempotency_key)
            .limit(1)
        )
        return self.session.scalar(statement)

    def add_result_collect_record(
        self,
        record: GroupWorkspaceResultCollectRecord,
    ) -> GroupWorkspaceResultCollectRecord:
        self.session.add(record)
        return record
