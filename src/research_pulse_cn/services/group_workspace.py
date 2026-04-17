"""Admin-managed group workspaces and read-only structured result sharing."""

from __future__ import annotations

import hashlib
import logging
import secrets
import string
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy.orm import Session

from research_pulse_cn.auth.crypto import generate_refresh_token, hash_token
from research_pulse_cn.core.config import get_settings
from research_pulse_cn.core.errors import AuthenticationError, NotFoundError, ValidationFailedError
from research_pulse_cn.core.metrics import get_metrics
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.db.models import (
    GroupWorkspace,
    GroupWorkspaceInviteClaim,
    GroupWorkspaceInviteGrant,
    GroupWorkspaceMember,
    GroupWorkspacePaper,
    GroupWorkspaceResultCollectRecord,
    PaperProfile,
    PulseDigestIssue,
    ResultShareAlias,
    ResultShareGrant,
    ResultShareViewEvent,
    utcnow,
)
from research_pulse_cn.domain.enums import (
    GroupWorkspaceInviteClaimStatus,
    GroupWorkspaceInviteGrantStatus,
    GroupWorkspaceInviteRole,
    GroupWorkspaceMemberRole,
    GroupWorkspaceResultCollectStatus,
    GroupWorkspaceStatus,
    PulseCardType,
    ResultShareAliasStatus,
    ResultShareGrantStatus,
    ResultShareHandoffTargetKind,
    ResultShareKind,
    ResultShareViewAccessMode,
    ResultShareViewEventType,
    ResultShareViewOutcome,
)
from research_pulse_cn.domain.group_workspace import (
    GroupWorkspaceInviteGrantContext,
    IssuedGroupWorkspaceInviteGrant,
    IssuedResultShareAlias,
    IssuedResultShareGrant,
    ResultShareAliasContext,
    ResultShareGrantContext,
)
from research_pulse_cn.domain.progress import derive_progress_percentage
from research_pulse_cn.domain.subscription_self_service import SubscriptionSelfServiceGrantContext
from research_pulse_cn.repositories.digest import DigestRepository
from research_pulse_cn.repositories.group_workspace import GroupWorkspaceRepository
from research_pulse_cn.repositories.paper import PaperRepository
from research_pulse_cn.repositories.user import UserRepository
from research_pulse_cn.services.common import commit_session

WORKSPACE_MEMBER_ROLE_ORDER = {
    GroupWorkspaceMemberRole.OWNER: 0,
    GroupWorkspaceMemberRole.EDITOR: 1,
    GroupWorkspaceMemberRole.VIEWER: 2,
}

SHARED_SECTION_ORDER = [
    "today_focus",
    "yesterday_recap",
    "signal_updates",
    "related_papers",
    "other_updates",
]

SHARED_SECTION_TITLE_BY_KIND = {
    "today_focus": "Today Focus",
    "yesterday_recap": "Yesterday Recap",
    "signal_updates": "Signal Updates",
    "related_papers": "Related Papers",
    "other_updates": "Other Updates",
}

INVITE_ROLE_ASSIGNABLE_VALUES = frozenset(
    {
        GroupWorkspaceInviteRole.EDITOR,
        GroupWorkspaceInviteRole.VIEWER,
    }
)

RESULT_COLLECTABLE_SHARE_KINDS = frozenset(
    {
        ResultShareKind.DIGEST_ISSUE,
        ResultShareKind.PAPER_SNAPSHOT,
    }
)

RESULT_SHARE_ALIAS_ALPHABET = string.ascii_letters + string.digits
logger = logging.getLogger(__name__)


class GroupWorkspaceService:
    """Create admin-managed group workspaces and resolve public result share grants."""

    def __init__(self, session: Session, *, now_provider=None) -> None:
        self.session = session
        self.settings = get_settings()
        self.now_provider = now_provider or utcnow
        self.repository = GroupWorkspaceRepository(session)
        self.user_repository = UserRepository(session)
        self.paper_repository = PaperRepository(session)
        self.digest_repository = DigestRepository(session)
        self.metrics = get_metrics()

    def list_workspaces(
        self,
        *,
        status: GroupWorkspaceStatus | None = None,
        user_id: UUID | None = None,
    ) -> list[GroupWorkspace]:
        return self.repository.list_workspaces(status=status, user_id=user_id)

    def get_workspace(self, workspace_id: UUID) -> GroupWorkspace:
        workspace = self.repository.get_workspace(workspace_id)
        if workspace is None:
            raise NotFoundError(f"group workspace {workspace_id} was not found")
        return workspace

    def create_workspace(
        self,
        *,
        slug: str,
        name: str,
        description: str | None,
        created_by_admin_id: UUID | None,
    ) -> GroupWorkspace:
        workspace = GroupWorkspace(
            slug=slug.strip(),
            name=name.strip(),
            description=description,
            status=GroupWorkspaceStatus.ACTIVE,
            created_by_admin_id=created_by_admin_id,
        )
        self.repository.add_workspace(workspace)
        commit_session(self.session)
        persisted = self.get_workspace(workspace.id)
        self.metrics.increment("group_workspaces_created_total")
        return persisted

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        slug: str | None = None,
        name: str | None = None,
        description: str | None = None,
        status: GroupWorkspaceStatus | None = None,
        update_fields: set[str] | None = None,
    ) -> GroupWorkspace:
        workspace = self.get_workspace(workspace_id)
        explicit_fields = update_fields or set()
        if "slug" in explicit_fields and slug is not None:
            workspace.slug = slug.strip()
        if "name" in explicit_fields and name is not None:
            workspace.name = name.strip()
        if "description" in explicit_fields:
            workspace.description = description
        if "status" in explicit_fields and status is not None:
            workspace.status = status
        commit_session(self.session)
        return self.get_workspace(workspace.id)

    def add_member(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: GroupWorkspaceMemberRole,
    ) -> GroupWorkspaceMember:
        workspace = self.get_workspace(workspace_id)
        user = self.user_repository.get(user_id)
        if user is None:
            raise NotFoundError(f"user {user_id} was not found")
        member = GroupWorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=role,
            joined_at=self.now_provider(),
        )
        self.repository.add_workspace_member(member)
        commit_session(self.session)
        refreshed = self.repository.get_workspace_member(
            workspace_id=workspace.id,
            member_id=member.id,
        )
        if refreshed is None:
            raise NotFoundError(f"group workspace member {member.id} was not found")
        return refreshed

    def remove_member(self, *, workspace_id: UUID, member_id: UUID) -> None:
        self.get_workspace(workspace_id)
        member = self.repository.get_workspace_member(
            workspace_id=workspace_id,
            member_id=member_id,
        )
        if member is None:
            raise NotFoundError(f"group workspace member {member_id} was not found")
        self.repository.delete_workspace_member(member)
        commit_session(self.session)

    def add_paper(
        self,
        *,
        workspace_id: UUID,
        paper_id: UUID,
        added_by_admin_id: UUID | None,
    ) -> GroupWorkspacePaper:
        workspace = self.get_workspace(workspace_id)
        paper = self.paper_repository.get(paper_id)
        if paper is None:
            raise NotFoundError(f"paper {paper_id} was not found")
        workspace_paper = GroupWorkspacePaper(
            workspace_id=workspace.id,
            paper_id=paper.id,
            added_by_admin_id=added_by_admin_id,
        )
        self.repository.add_workspace_paper(workspace_paper)
        commit_session(self.session)
        refreshed = self.repository.get_workspace_paper(
            workspace_id=workspace.id,
            paper_id=paper.id,
        )
        if refreshed is None:
            raise NotFoundError(f"group workspace paper {paper.id} was not found")
        return refreshed

    def remove_paper(self, *, workspace_id: UUID, paper_id: UUID) -> None:
        self.get_workspace(workspace_id)
        workspace_paper = self.repository.get_workspace_paper(
            workspace_id=workspace_id,
            paper_id=paper_id,
        )
        if workspace_paper is None:
            raise NotFoundError(f"group workspace paper {paper_id} was not found")
        self.repository.delete_workspace_paper(workspace_paper)
        commit_session(self.session)

    def get_workspace_board(
        self,
        workspace_id: UUID,
        *,
        expose_admin_fields: bool,
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        return self._workspace_board_payload(workspace, expose_admin_fields=expose_admin_fields)

    def list_workspace_memberships_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[GroupWorkspaceMember]:
        memberships = self.repository.list_workspace_memberships_for_user(user_id=user_id)
        return [membership for membership in memberships if membership.workspace is not None]

    def list_invite_grants(
        self,
        *,
        workspace_id: UUID | None = None,
        status: GroupWorkspaceInviteGrantStatus | None = None,
        role_to_assign: GroupWorkspaceInviteRole | None = None,
    ) -> list[GroupWorkspaceInviteGrant]:
        grants = self.repository.list_invite_grants(
            workspace_id=workspace_id,
            status=status,
            role_to_assign=role_to_assign,
        )
        self._refresh_expired_invite_grants(grants)
        return grants

    def get_invite_grant(self, grant_id: UUID) -> GroupWorkspaceInviteGrant:
        grant = self.repository.get_invite_grant(grant_id)
        if grant is None:
            raise NotFoundError(f"group workspace invite grant {grant_id} was not found")
        if self._mark_invite_expired_if_needed(grant):
            commit_session(self.session)
        return grant

    def serialize_invite_grant(self, grant: GroupWorkspaceInviteGrant) -> dict[str, Any]:
        return {
            "id": grant.id,
            "workspace_id": grant.workspace_id,
            "role_to_assign": grant.role_to_assign,
            "status": grant.status,
            "display_label": grant.display_label,
            "max_claims": grant.max_claims,
            "claim_count": grant.claim_count,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "issued_by_admin_id": grant.issued_by_admin_id,
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def serialize_invite_claim(self, claim: GroupWorkspaceInviteClaim) -> dict[str, Any]:
        return {
            "id": claim.id,
            "invite_grant_id": claim.invite_grant_id,
            "workspace_id": claim.workspace_id,
            "user_id": claim.user_id,
            "membership_id": claim.membership_id,
            "role_assigned": claim.role_assigned,
            "claim_status": claim.claim_status,
            "reason_codes": list(claim.reason_codes or []),
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
            "claimed_at": claim.claimed_at,
        }

    def create_invite_grant(
        self,
        *,
        workspace_id: UUID,
        role_to_assign: GroupWorkspaceInviteRole,
        display_label: str | None,
        max_claims: int | None,
        expires_at: datetime | None,
        issued_by_admin_id: UUID | None,
    ) -> tuple[GroupWorkspaceInviteGrant, IssuedGroupWorkspaceInviteGrant]:
        self._ensure_invites_enabled()
        workspace = self.get_workspace(workspace_id)
        if workspace.status != GroupWorkspaceStatus.ACTIVE:
            raise ValidationFailedError(
                "invite grants require an active workspace",
                errors=[
                    {
                        "field_id": "workspace_id",
                        "code": "workspace_archived",
                        "message": "invite grants require an active workspace",
                    }
                ],
            )
        if role_to_assign not in INVITE_ROLE_ASSIGNABLE_VALUES:
            raise ValidationFailedError(
                "invite grants may assign only editor or viewer",
                errors=[
                    {
                        "field_id": "role_to_assign",
                        "code": "role_not_assignable",
                        "message": "invite grants may assign only editor or viewer",
                    }
                ],
            )
        effective_max_claims = (
            self.settings.group_workspace_invite_default_max_claims
            if max_claims is None
            else max_claims
        )
        if effective_max_claims is not None and effective_max_claims < 1:
            raise ValidationFailedError(
                "max_claims must be at least 1",
                errors=[
                    {
                        "field_id": "max_claims",
                        "code": "invalid",
                        "message": "max_claims must be at least 1",
                    }
                ],
            )
        raw_token = generate_refresh_token()
        grant = GroupWorkspaceInviteGrant(
            workspace_id=workspace.id,
            role_to_assign=role_to_assign,
            token_hash=hash_token(raw_token),
            status=GroupWorkspaceInviteGrantStatus.ACTIVE,
            display_label=display_label,
            max_claims=effective_max_claims,
            claim_count=0,
            expires_at=expires_at or self._default_invite_expires_at(),
            issued_by_admin_id=issued_by_admin_id,
        )
        self.repository.add_invite_grant(grant)
        commit_session(self.session)
        persisted = self.get_invite_grant(grant.id)
        self.metrics.increment("group_workspace_invite_grants_issued_total")
        return persisted, IssuedGroupWorkspaceInviteGrant(
            grant_id=persisted.id,
            plain_text_token=raw_token,
            expires_at=persisted.expires_at,
        )

    def revoke_invite_grant(self, grant_id: UUID) -> GroupWorkspaceInviteGrant:
        grant = self.get_invite_grant(grant_id)
        if grant.status != GroupWorkspaceInviteGrantStatus.REVOKED:
            grant.status = GroupWorkspaceInviteGrantStatus.REVOKED
            commit_session(self.session)
        return self.get_invite_grant(grant_id)

    def list_invite_claims(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        claim_status: GroupWorkspaceInviteClaimStatus | None = None,
    ) -> list[GroupWorkspaceInviteClaim]:
        return self.repository.list_invite_claims(
            workspace_id=workspace_id,
            user_id=user_id,
            claim_status=claim_status,
        )

    def authenticate_invite_token(self, raw_token: str) -> GroupWorkspaceInviteGrantContext:
        self._ensure_invites_enabled()
        grant = self.repository.get_invite_grant_by_token_hash(hash_token(raw_token))
        if grant is None:
            raise AuthenticationError("group workspace invite grant was not found")
        now = self.now_provider()
        if grant.status == GroupWorkspaceInviteGrantStatus.REVOKED:
            raise AuthenticationError("group workspace invite grant has been revoked")
        if grant.status == GroupWorkspaceInviteGrantStatus.EXPIRED:
            raise AuthenticationError("group workspace invite grant has expired")
        if grant.status == GroupWorkspaceInviteGrantStatus.EXHAUSTED:
            raise AuthenticationError("group workspace invite grant has been exhausted")
        if self._mark_invite_expired_if_needed(grant, now=now):
            commit_session(self.session)
            if grant.status == GroupWorkspaceInviteGrantStatus.EXPIRED:
                raise AuthenticationError("group workspace invite grant has expired")
            if grant.status == GroupWorkspaceInviteGrantStatus.EXHAUSTED:
                raise AuthenticationError("group workspace invite grant has been exhausted")
        grant.last_used_at = now
        commit_session(self.session)
        return GroupWorkspaceInviteGrantContext(
            grant_id=grant.id,
            workspace_id=grant.workspace_id,
            role_to_assign=grant.role_to_assign,
            status=grant.status,
            display_label=grant.display_label,
            max_claims=grant.max_claims,
            claim_count=grant.claim_count,
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def invite_bootstrap(self, grant: GroupWorkspaceInviteGrantContext) -> dict[str, Any]:
        self._ensure_public_bootstrap_enabled()
        stored = self.get_invite_grant(grant.grant_id)
        workspace = stored.workspace or self.get_workspace(stored.workspace_id)
        self.metrics.increment("group_workspace_invite_bootstrap_requests_total")
        with bind_log_context(
            workspace_id=workspace.id,
            invite_grant_id=stored.id,
        ):
            return {
                "invite": self._public_invite_summary(stored),
                "workspace": self._workspace_safe_summary(workspace),
                "role_to_assign": stored.role_to_assign,
                "remaining_claims": self._remaining_claims(stored),
                "expires_at": stored.expires_at,
                "result_collect_handoff_reserve": self._result_collect_handoff_reserve_summary(),
                "notes": [
                    "This invite exposes a safe workspace summary only.",
                    "Joining requires an existing subscription self-service grant.",
                ],
            }

    def preview_invite_claim(
        self,
        *,
        raw_token: str,
        grant: SubscriptionSelfServiceGrantContext,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_invite_claim_previews_total")
        evaluation = self._evaluate_invite_for_user(raw_token=raw_token, user_id=grant.user_id)
        return {
            "can_claim": evaluation["can_claim"],
            "reason_codes": evaluation["reason_codes"],
            "current_membership": (
                None
                if evaluation["membership"] is None
                else self._workspace_membership_summary(evaluation["membership"])
            ),
            "invite": (
                None
                if evaluation["invite_grant"] is None
                else self._public_invite_summary(evaluation["invite_grant"])
            ),
            "workspace": (
                None
                if evaluation["workspace"] is None
                else self._workspace_safe_summary(evaluation["workspace"])
            ),
            "result_collect_handoff_reserve": self._result_collect_handoff_reserve_summary(),
        }

    def claim_workspace_invite(
        self,
        *,
        raw_token: str,
        grant: SubscriptionSelfServiceGrantContext,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_invite_claims_total")
        evaluation = self._evaluate_invite_for_user(raw_token=raw_token, user_id=grant.user_id)
        invite_grant: GroupWorkspaceInviteGrant | None = evaluation["invite_grant"]
        workspace: GroupWorkspace | None = evaluation["workspace"]
        membership: GroupWorkspaceMember | None = evaluation["membership"]
        reason_codes = list(evaluation["reason_codes"])

        if not evaluation["can_claim"]:
            invite_claim = self._record_invite_claim_if_applicable(
                invite_grant=invite_grant,
                workspace=workspace,
                user_id=grant.user_id,
                membership=membership,
                claim_status=(
                    GroupWorkspaceInviteClaimStatus.ALREADY_MEMBER
                    if reason_codes == ["already_member"]
                    else GroupWorkspaceInviteClaimStatus.REJECTED
                ),
                reason_codes=reason_codes,
                claimed_at=None,
            )
            return {
                "action": "already_member" if reason_codes == ["already_member"] else "rejected",
                "membership": (
                    None if membership is None else self._workspace_membership_summary(membership)
                ),
                "invite_claim": (
                    None if invite_claim is None else self.serialize_invite_claim(invite_claim)
                ),
                "invite": (
                    None if invite_grant is None else self._public_invite_summary(invite_grant)
                ),
                "workspace": (
                    None if workspace is None else self._workspace_safe_summary(workspace)
                ),
                "result_collect_handoff_reserve": self._result_collect_handoff_reserve_summary(),
            }

        assert invite_grant is not None
        assert workspace is not None
        role = GroupWorkspaceMemberRole(invite_grant.role_to_assign.value)
        new_membership = GroupWorkspaceMember(
            workspace_id=workspace.id,
            user_id=grant.user_id,
            role=role,
            joined_at=self.now_provider(),
        )
        self.repository.add_workspace_member(new_membership)
        self.session.flush()
        invite_grant.claim_count += 1
        if self._remaining_claims(invite_grant) == 0:
            invite_grant.status = GroupWorkspaceInviteGrantStatus.EXHAUSTED
        invite_claim = self._record_invite_claim(
            invite_grant=invite_grant,
            workspace=workspace,
            user_id=grant.user_id,
            membership=new_membership,
            claim_status=GroupWorkspaceInviteClaimStatus.CLAIMED,
            reason_codes=[],
            claimed_at=self.now_provider(),
        )
        commit_session(self.session)
        persisted_membership = self.repository.get_workspace_member_for_user(
            workspace_id=workspace.id,
            user_id=grant.user_id,
        )
        persisted_claim = self.repository.get_invite_claim(
            invite_grant_id=invite_grant.id,
            user_id=grant.user_id,
        )
        return {
            "action": "claimed",
            "membership": (
                None
                if persisted_membership is None
                else self._workspace_membership_summary(persisted_membership)
            ),
            "invite_claim": (
                None if persisted_claim is None else self.serialize_invite_claim(persisted_claim)
            ),
            "invite": self._public_invite_summary(self.get_invite_grant(invite_grant.id)),
            "workspace": self._workspace_safe_summary(self.get_workspace(workspace.id)),
            "result_collect_handoff_reserve": self._result_collect_handoff_reserve_summary(),
        }

    def list_result_share_grants(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        status: ResultShareGrantStatus | None = None,
    ) -> list[ResultShareGrant]:
        grants = self.repository.list_result_share_grants(
            workspace_id=workspace_id,
            share_kind=share_kind,
            status=status,
        )
        self._refresh_expired_grants(grants)
        if user_id is not None:
            grants = [grant for grant in grants if self._grant_matches_user(grant, user_id=user_id)]
        return grants

    def get_result_share_grant(self, grant_id: UUID) -> ResultShareGrant:
        grant = self.repository.get_result_share_grant(grant_id)
        if grant is None:
            raise NotFoundError(f"result share grant {grant_id} was not found")
        self._mark_expired_if_needed(grant)
        return grant

    def list_result_share_aliases(
        self,
        *,
        result_share_grant_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        status: ResultShareAliasStatus | None = None,
    ) -> list[ResultShareAlias]:
        aliases = self.repository.list_result_share_aliases(
            result_share_grant_id=result_share_grant_id,
            share_kind=share_kind,
            status=status,
        )
        self._refresh_expired_aliases(aliases)
        return aliases

    def get_result_share_alias(self, alias_id: UUID) -> ResultShareAlias:
        alias = self.repository.get_result_share_alias(alias_id)
        if alias is None:
            raise NotFoundError(f"result share alias {alias_id} was not found")
        self._mark_alias_expired_if_needed(alias)
        return alias

    def list_result_collect_records(
        self,
        *,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        result_share_grant_id: UUID | None = None,
        status: GroupWorkspaceResultCollectStatus | None = None,
        collected_paper_id: UUID | None = None,
    ) -> list[GroupWorkspaceResultCollectRecord]:
        return self.repository.list_result_collect_records(
            workspace_id=workspace_id,
            user_id=user_id,
            result_share_grant_id=result_share_grant_id,
            status=status,
            collected_paper_id=collected_paper_id,
        )

    def serialize_result_share_grant(self, grant: ResultShareGrant) -> dict[str, Any]:
        return {
            "id": grant.id,
            "share_kind": grant.share_kind,
            "workspace_id": grant.workspace_id,
            "digest_issue_id": grant.digest_issue_id,
            "paper_id": grant.paper_id,
            "status": grant.status,
            "display_label": grant.display_label,
            "issued_by_admin_id": grant.issued_by_admin_id,
            "expires_at": grant.expires_at,
            "last_used_at": grant.last_used_at,
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def serialize_result_share_alias(self, alias: ResultShareAlias) -> dict[str, Any]:
        share_kind = (
            alias.result_share_grant.share_kind
            if alias.result_share_grant is not None
            else self.get_result_share_grant(alias.result_share_grant_id).share_kind
        )
        return {
            "id": alias.id,
            "result_share_grant_id": alias.result_share_grant_id,
            "share_kind": share_kind,
            "status": alias.status,
            "display_label": alias.display_label,
            "alias_prefix": alias.alias_prefix,
            "expires_at": alias.expires_at,
            "last_used_at": alias.last_used_at,
            "created_at": alias.created_at,
            "updated_at": alias.updated_at,
        }

    def list_result_share_view_events(
        self,
        *,
        result_share_grant_id: UUID | None = None,
        result_share_alias_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        access_mode: ResultShareViewAccessMode | None = None,
        event_type: ResultShareViewEventType | None = None,
        outcome: ResultShareViewOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[ResultShareViewEvent]:
        normalized_from, normalized_to = self._normalize_result_share_analytics_window(
            date_from=date_from,
            date_to=date_to,
        )
        return self.repository.list_result_share_view_events(
            result_share_grant_id=result_share_grant_id,
            result_share_alias_id=result_share_alias_id,
            share_kind=share_kind,
            access_mode=access_mode,
            event_type=event_type,
            outcome=outcome,
            date_from=normalized_from,
            date_to=normalized_to,
        )

    def summarize_result_share_view_events(
        self,
        *,
        result_share_grant_id: UUID | None = None,
        result_share_alias_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        access_mode: ResultShareViewAccessMode | None = None,
        event_type: ResultShareViewEventType | None = None,
        outcome: ResultShareViewOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        events = self.list_result_share_view_events(
            result_share_grant_id=result_share_grant_id,
            result_share_alias_id=result_share_alias_id,
            share_kind=share_kind,
            access_mode=access_mode,
            event_type=event_type,
            outcome=outcome,
            date_from=date_from,
            date_to=date_to,
        )
        by_share_kind: dict[str, int] = {}
        by_access_mode: dict[str, int] = {}
        by_handoff_target: dict[str, int] = {}
        distinct_fingerprints: set[str] = set()
        last_event_at: datetime | None = None
        for event in events:
            by_share_kind[event.share_kind.value] = by_share_kind.get(event.share_kind.value, 0) + 1
            by_access_mode[event.access_mode.value] = (
                by_access_mode.get(event.access_mode.value, 0) + 1
            )
            if event.handoff_target_kind is not None:
                by_handoff_target[event.handoff_target_kind.value] = (
                    by_handoff_target.get(event.handoff_target_kind.value, 0) + 1
                )
            if event.request_fingerprint_hash:
                distinct_fingerprints.add(event.request_fingerprint_hash)
            if last_event_at is None or event.occurred_at > last_event_at:
                last_event_at = event.occurred_at
        return {
            "total_events": len(events),
            "resolved_events": sum(
                1 for event in events if event.outcome == ResultShareViewOutcome.RESOLVED
            ),
            "rejected_events": sum(
                1 for event in events if event.outcome == ResultShareViewOutcome.REJECTED
            ),
            "bootstrap_view_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.BOOTSTRAP_VIEW
            ),
            "content_view_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.CONTENT_VIEW
            ),
            "redirect_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.REDIRECT
            ),
            "invite_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT
            ),
            "collect_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT
            ),
            "distinct_fingerprint_count": (
                len(distinct_fingerprints)
                if self.settings.result_share_analytics_enable_fingerprint
                else None
            ),
            "by_share_kind": by_share_kind,
            "by_access_mode": by_access_mode,
            "by_handoff_target": by_handoff_target,
            "last_event_at": last_event_at,
        }

    def serialize_result_share_view_event(self, event: ResultShareViewEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "result_share_grant_id": event.result_share_grant_id,
            "result_share_alias_id": event.result_share_alias_id,
            "share_kind": event.share_kind,
            "access_mode": event.access_mode,
            "event_type": event.event_type,
            "outcome": event.outcome,
            "handoff_target_kind": event.handoff_target_kind,
            "referrer_host": event.referrer_host,
            "user_agent_family": event.user_agent_family,
            "occurred_at": event.occurred_at,
            "created_at": event.created_at,
        }

    def summarize_group_workspace_conversion_overview(
        self,
        *,
        workspace_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        access_mode: ResultShareViewAccessMode | None = None,
        event_type: ResultShareViewEventType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        normalized_from, normalized_to = self._normalize_result_share_analytics_window(
            date_from=date_from,
            date_to=date_to,
        )
        events = self.list_result_share_view_events(
            share_kind=share_kind,
            access_mode=access_mode,
            event_type=event_type,
            date_from=normalized_from,
            date_to=normalized_to,
        )
        if workspace_id is not None:
            events = [
                event
                for event in events
                if self._result_share_event_workspace_id(event) == workspace_id
            ]

        claims = [
            claim
            for claim in self.list_invite_claims(workspace_id=workspace_id)
            if self._timestamp_in_window(
                self._invite_claim_activity_at(claim),
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        collects = [
            record
            for record in self.list_result_collect_records(workspace_id=workspace_id)
            if self._result_collect_record_matches_share_kind(record, share_kind=share_kind)
            and self._timestamp_in_window(
                record.created_at,
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]

        by_share_kind: dict[str, int] = {}
        by_access_mode: dict[str, int] = {}
        by_handoff_target: dict[str, int] = {}
        unique_grant_ids: set[UUID] = set()
        unique_workspace_ids: set[UUID] = set()
        last_activity_at: datetime | None = None

        for event in events:
            by_share_kind[event.share_kind.value] = by_share_kind.get(event.share_kind.value, 0) + 1
            by_access_mode[event.access_mode.value] = (
                by_access_mode.get(event.access_mode.value, 0) + 1
            )
            if event.handoff_target_kind is not None:
                by_handoff_target[event.handoff_target_kind.value] = (
                    by_handoff_target.get(event.handoff_target_kind.value, 0) + 1
                )
            if event.result_share_grant_id is not None:
                unique_grant_ids.add(event.result_share_grant_id)
            workspace_ref = self._result_share_event_workspace_id(event)
            if workspace_ref is not None:
                unique_workspace_ids.add(workspace_ref)
            if last_activity_at is None or event.occurred_at > last_activity_at:
                last_activity_at = event.occurred_at

        for claim in claims:
            unique_workspace_ids.add(claim.workspace_id)
            activity_at = self._invite_claim_activity_at(claim)
            if last_activity_at is None or activity_at > last_activity_at:
                last_activity_at = activity_at

        for record in collects:
            unique_workspace_ids.add(record.workspace_id)
            if record.result_share_grant_id is not None:
                unique_grant_ids.add(record.result_share_grant_id)
            if last_activity_at is None or record.created_at > last_activity_at:
                last_activity_at = record.created_at

        return {
            "window_start": normalized_from,
            "window_end": normalized_to,
            "total_share_view_events": len(events),
            "bootstrap_view_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.BOOTSTRAP_VIEW
            ),
            "content_view_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.CONTENT_VIEW
            ),
            "redirect_count": sum(
                1 for event in events if event.event_type == ResultShareViewEventType.REDIRECT
            ),
            "invite_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT
            ),
            "collect_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT
            ),
            "resolved_event_count": sum(
                1 for event in events if event.outcome == ResultShareViewOutcome.RESOLVED
            ),
            "rejected_event_count": sum(
                1 for event in events if event.outcome == ResultShareViewOutcome.REJECTED
            ),
            "by_share_kind": by_share_kind,
            "by_access_mode": by_access_mode,
            "by_handoff_target": by_handoff_target,
            "invite_claimed_count": sum(
                1
                for claim in claims
                if claim.claim_status == GroupWorkspaceInviteClaimStatus.CLAIMED
            ),
            "invite_already_member_count": sum(
                1
                for claim in claims
                if claim.claim_status == GroupWorkspaceInviteClaimStatus.ALREADY_MEMBER
            ),
            "invite_rejected_count": sum(
                1
                for claim in claims
                if claim.claim_status == GroupWorkspaceInviteClaimStatus.REJECTED
            ),
            "collect_collected_count": sum(
                1
                for record in collects
                if record.status == GroupWorkspaceResultCollectStatus.COLLECTED
            ),
            "collect_already_present_count": sum(
                1
                for record in collects
                if record.status == GroupWorkspaceResultCollectStatus.ALREADY_PRESENT
            ),
            "collect_rejected_count": sum(
                1
                for record in collects
                if record.status == GroupWorkspaceResultCollectStatus.REJECTED
            ),
            "unique_result_share_grant_count": len(unique_grant_ids),
            "unique_workspace_count": len(unique_workspace_ids),
            "last_activity_at": last_activity_at,
            "attribution_scope": self._conversion_attribution_scope_summary(
                workspace_overview=False,
                include_inventory_metrics=False,
                include_workspace_metrics=False,
                share_filter_applied=share_kind is not None,
                event_filters_applied=access_mode is not None or event_type is not None,
            ),
        }

    def summarize_workspace_conversion_overview(
        self,
        *,
        workspace_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        normalized_from, normalized_to = self._normalize_result_share_analytics_window(
            date_from=date_from,
            date_to=date_to,
        )

        events = [
            event
            for event in self.list_result_share_view_events(
                date_from=normalized_from,
                date_to=normalized_to,
            )
            if self._result_share_event_workspace_id(event) == workspace.id
        ]
        claims = [
            claim
            for claim in self.list_invite_claims(workspace_id=workspace.id)
            if self._timestamp_in_window(
                self._invite_claim_activity_at(claim),
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        all_workspace_collects = self.list_result_collect_records(workspace_id=workspace.id)
        collects = [
            record
            for record in all_workspace_collects
            if self._timestamp_in_window(
                record.created_at,
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        active_board_grants = self.list_result_share_grants(
            workspace_id=workspace.id,
            share_kind=ResultShareKind.WORKSPACE_BOARD,
            status=ResultShareGrantStatus.ACTIVE,
        )
        active_invite_grants = self.list_invite_grants(
            workspace_id=workspace.id,
            status=GroupWorkspaceInviteGrantStatus.ACTIVE,
        )
        active_digest_issue_share_grant_ids = {
            record.result_share_grant_id
            for record in all_workspace_collects
            if record.result_share_grant_id is not None
            and record.share_kind == ResultShareKind.DIGEST_ISSUE
            and record.result_share_grant is not None
            and record.result_share_grant.status == ResultShareGrantStatus.ACTIVE
        }
        active_paper_snapshot_share_grant_ids = {
            record.result_share_grant_id
            for record in all_workspace_collects
            if record.result_share_grant_id is not None
            and record.share_kind == ResultShareKind.PAPER_SNAPSHOT
            and record.result_share_grant is not None
            and record.result_share_grant.status == ResultShareGrantStatus.ACTIVE
        }

        last_activity_at: datetime | None = None
        for event in events:
            if last_activity_at is None or event.occurred_at > last_activity_at:
                last_activity_at = event.occurred_at
        for claim in claims:
            activity_at = self._invite_claim_activity_at(claim)
            if last_activity_at is None or activity_at > last_activity_at:
                last_activity_at = activity_at
        for record in collects:
            if last_activity_at is None or record.created_at > last_activity_at:
                last_activity_at = record.created_at

        non_rejected_collects = [
            record
            for record in collects
            if record.status
            in {
                GroupWorkspaceResultCollectStatus.COLLECTED,
                GroupWorkspaceResultCollectStatus.ALREADY_PRESENT,
            }
        ]
        return {
            "window_start": normalized_from,
            "window_end": normalized_to,
            "workspace": self._workspace_safe_summary(workspace),
            "active_workspace_board_share_grant_count": len(active_board_grants),
            "active_digest_issue_share_grant_count": len(active_digest_issue_share_grant_ids),
            "active_paper_snapshot_share_grant_count": len(active_paper_snapshot_share_grant_ids),
            "active_invite_grant_count": len(active_invite_grants),
            "workspace_board_view_count": sum(
                1
                for event in events
                if event.share_kind == ResultShareKind.WORKSPACE_BOARD
                and event.event_type
                in {
                    ResultShareViewEventType.BOOTSTRAP_VIEW,
                    ResultShareViewEventType.CONTENT_VIEW,
                }
            ),
            "invite_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT
            ),
            "collect_handoff_redirect_count": sum(
                1
                for event in events
                if event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT
            ),
            "invite_claimed_count": sum(
                1
                for claim in claims
                if claim.claim_status == GroupWorkspaceInviteClaimStatus.CLAIMED
            ),
            "invite_already_member_count": sum(
                1
                for claim in claims
                if claim.claim_status == GroupWorkspaceInviteClaimStatus.ALREADY_MEMBER
            ),
            "collect_collected_count": sum(
                1
                for record in collects
                if record.status == GroupWorkspaceResultCollectStatus.COLLECTED
            ),
            "collect_already_present_count": sum(
                1
                for record in collects
                if record.status == GroupWorkspaceResultCollectStatus.ALREADY_PRESENT
            ),
            "unique_collected_paper_count": len(
                {record.collected_paper_id for record in non_rejected_collects}
            ),
            "unique_collecting_user_count": len(
                {record.user_id for record in non_rejected_collects}
            ),
            "last_activity_at": last_activity_at,
            "attribution_scope": self._conversion_attribution_scope_summary(
                workspace_overview=True,
                include_inventory_metrics=False,
                include_workspace_metrics=True,
                share_filter_applied=False,
                event_filters_applied=False,
            ),
        }

    def summarize_group_workspace_conversion_drilldown(
        self,
        *,
        workspace_id: UUID | None = None,
        share_kind: ResultShareKind | None = None,
        access_mode: ResultShareViewAccessMode | None = None,
        event_type: ResultShareViewEventType | None = None,
        outcome: ResultShareViewOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        normalized_from, normalized_to = self._normalize_result_share_analytics_window(
            date_from=date_from,
            date_to=date_to,
        )
        effective_limit = max(1, min(limit, 100))
        events = self.list_result_share_view_events(
            share_kind=share_kind,
            access_mode=access_mode,
            event_type=event_type,
            outcome=outcome,
            date_from=normalized_from,
            date_to=normalized_to,
        )
        if workspace_id is not None:
            events = [
                event
                for event in events
                if self._result_share_event_workspace_id(event) == workspace_id
            ]
        claims = [
            claim
            for claim in self.list_invite_claims(workspace_id=workspace_id)
            if self._timestamp_in_window(
                self._invite_claim_activity_at(claim),
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        collects = [
            record
            for record in self.list_result_collect_records(workspace_id=workspace_id)
            if self._result_collect_record_matches_share_kind(record, share_kind=share_kind)
            and self._timestamp_in_window(
                record.created_at,
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        attribution_scope = self._conversion_attribution_scope_summary(
            workspace_overview=False,
            include_inventory_metrics=False,
            include_workspace_metrics=False,
            share_filter_applied=share_kind is not None,
            event_filters_applied=access_mode is not None
            or event_type is not None
            or outcome is not None,
        )
        return {
            "window_start": normalized_from,
            "window_end": normalized_to,
            "daily_buckets": self._conversion_daily_buckets(
                events=events,
                claims=claims,
                collects=collects,
            ),
            "top_workspaces": self._conversion_top_workspaces(
                events=events,
                claims=claims,
                collects=collects,
                limit=effective_limit,
            ),
            "top_result_share_grants": self._conversion_top_result_share_grants(
                events=events,
                collects=collects,
                limit=effective_limit,
            ),
            "recent_share_events": [
                self._serialize_conversion_recent_share_event(event)
                for event in events[:effective_limit]
            ],
            "recent_invite_claims": [
                self._serialize_conversion_recent_invite_claim(claim)
                for claim in sorted(
                    claims,
                    key=self._invite_claim_activity_at,
                    reverse=True,
                )[:effective_limit]
            ],
            "recent_collect_records": [
                self._serialize_conversion_recent_collect_record(record)
                for record in collects[:effective_limit]
            ],
            "attribution_scope": attribution_scope,
            "notes": self._conversion_drilldown_notes(
                workspace_overview=False,
                attribution_scope=attribution_scope,
            ),
        }

    def summarize_workspace_conversion_drilldown(
        self,
        *,
        workspace_id: UUID,
        share_kind: ResultShareKind | None = None,
        access_mode: ResultShareViewAccessMode | None = None,
        event_type: ResultShareViewEventType | None = None,
        outcome: ResultShareViewOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        workspace = self.get_workspace(workspace_id)
        normalized_from, normalized_to = self._normalize_result_share_analytics_window(
            date_from=date_from,
            date_to=date_to,
        )
        effective_limit = max(1, min(limit, 100))
        events = [
            event
            for event in self.list_result_share_view_events(
                share_kind=share_kind,
                access_mode=access_mode,
                event_type=event_type,
                outcome=outcome,
                date_from=normalized_from,
                date_to=normalized_to,
            )
            if self._result_share_event_workspace_id(event) == workspace.id
        ]
        claims = [
            claim
            for claim in self.list_invite_claims(workspace_id=workspace.id)
            if self._timestamp_in_window(
                self._invite_claim_activity_at(claim),
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        all_workspace_collects = self.list_result_collect_records(workspace_id=workspace.id)
        collects = [
            record
            for record in all_workspace_collects
            if self._result_collect_record_matches_share_kind(record, share_kind=share_kind)
            and self._timestamp_in_window(
                record.created_at,
                date_from=normalized_from,
                date_to=normalized_to,
            )
        ]
        active_board_grants = self.list_result_share_grants(
            workspace_id=workspace.id,
            share_kind=ResultShareKind.WORKSPACE_BOARD,
            status=ResultShareGrantStatus.ACTIVE,
        )
        active_invite_grants = self.list_invite_grants(
            workspace_id=workspace.id,
            status=GroupWorkspaceInviteGrantStatus.ACTIVE,
        )
        active_digest_issue_share_grant_ids = {
            record.result_share_grant_id
            for record in all_workspace_collects
            if record.result_share_grant_id is not None
            and record.share_kind == ResultShareKind.DIGEST_ISSUE
            and record.result_share_grant is not None
            and record.result_share_grant.status == ResultShareGrantStatus.ACTIVE
        }
        active_paper_snapshot_share_grant_ids = {
            record.result_share_grant_id
            for record in all_workspace_collects
            if record.result_share_grant_id is not None
            and record.share_kind == ResultShareKind.PAPER_SNAPSHOT
            and record.result_share_grant is not None
            and record.result_share_grant.status == ResultShareGrantStatus.ACTIVE
        }
        attribution_scope = self._conversion_attribution_scope_summary(
            workspace_overview=True,
            include_inventory_metrics=False,
            include_workspace_metrics=True,
            share_filter_applied=share_kind is not None,
            event_filters_applied=access_mode is not None
            or event_type is not None
            or outcome is not None,
        )
        return {
            "window_start": normalized_from,
            "window_end": normalized_to,
            "workspace": self._workspace_safe_summary(workspace),
            "daily_buckets": self._conversion_daily_buckets(
                events=events,
                claims=claims,
                collects=collects,
            ),
            "recent_share_events": [
                self._serialize_conversion_recent_share_event(event)
                for event in events[:effective_limit]
            ],
            "recent_invite_claims": [
                self._serialize_conversion_recent_invite_claim(claim)
                for claim in sorted(
                    claims,
                    key=self._invite_claim_activity_at,
                    reverse=True,
                )[:effective_limit]
            ],
            "recent_collect_records": [
                self._serialize_conversion_recent_collect_record(record)
                for record in collects[:effective_limit]
            ],
            "active_share_grant_snapshot": {
                "active_workspace_board_share_grant_count": len(active_board_grants),
                "active_digest_issue_share_grant_count": len(active_digest_issue_share_grant_ids),
                "active_paper_snapshot_share_grant_count": len(
                    active_paper_snapshot_share_grant_ids
                ),
            },
            "active_invite_grant_snapshot": {
                "active_invite_grant_count": len(active_invite_grants),
            },
            "attribution_scope": attribution_scope,
            "notes": self._conversion_drilldown_notes(
                workspace_overview=True,
                attribution_scope=attribution_scope,
            ),
        }

    def serialize_result_collect_record(
        self,
        record: GroupWorkspaceResultCollectRecord,
    ) -> dict[str, Any]:
        return {
            "id": record.id,
            "workspace_id": record.workspace_id,
            "user_id": record.user_id,
            "result_share_grant_id": record.result_share_grant_id,
            "share_kind": record.share_kind,
            "digest_issue_id": record.digest_issue_id,
            "source_pulse_card_id": record.source_pulse_card_id,
            "source_paper_id": record.source_paper_id,
            "collected_paper_id": record.collected_paper_id,
            "status": record.status,
            "reason_codes": list(record.reason_codes or []),
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _serialize_conversion_recent_share_event(
        self,
        event: ResultShareViewEvent,
    ) -> dict[str, Any]:
        return {
            "id": event.id,
            "result_share_grant_id": event.result_share_grant_id,
            "result_share_alias_id": event.result_share_alias_id,
            "share_kind": event.share_kind,
            "access_mode": event.access_mode,
            "event_type": event.event_type,
            "outcome": event.outcome,
            "handoff_target_kind": event.handoff_target_kind,
            "occurred_at": event.occurred_at,
        }

    def _serialize_conversion_recent_invite_claim(
        self,
        claim: GroupWorkspaceInviteClaim,
    ) -> dict[str, Any]:
        return {
            "id": claim.id,
            "invite_grant_id": claim.invite_grant_id,
            "workspace_id": claim.workspace_id,
            "user_id": claim.user_id,
            "claim_status": claim.claim_status,
            "role_assigned": claim.role_assigned,
            "claimed_at": claim.claimed_at,
            "reason_codes": list(claim.reason_codes or []),
        }

    def _serialize_conversion_recent_collect_record(
        self,
        record: GroupWorkspaceResultCollectRecord,
    ) -> dict[str, Any]:
        return {
            "id": record.id,
            "workspace_id": record.workspace_id,
            "user_id": record.user_id,
            "result_share_grant_id": record.result_share_grant_id,
            "share_kind": record.share_kind,
            "collected_paper_id": record.collected_paper_id,
            "status": record.status,
            "reason_codes": list(record.reason_codes or []),
            "created_at": record.created_at,
        }

    def _conversion_daily_buckets(
        self,
        *,
        events: Sequence[ResultShareViewEvent],
        claims: Sequence[GroupWorkspaceInviteClaim],
        collects: Sequence[GroupWorkspaceResultCollectRecord],
    ) -> list[dict[str, Any]]:
        buckets: dict[date, dict[str, Any]] = {}

        def ensure_bucket(day_value):
            if day_value not in buckets:
                buckets[day_value] = {
                    "day": day_value,
                    "share_view_count": 0,
                    "invite_handoff_redirect_count": 0,
                    "collect_handoff_redirect_count": 0,
                    "invite_claimed_count": 0,
                    "invite_already_member_count": 0,
                    "collect_collected_count": 0,
                    "collect_already_present_count": 0,
                }
            return buckets[day_value]

        for event in events:
            bucket = ensure_bucket(event.occurred_at.date())
            if event.event_type in {
                ResultShareViewEventType.BOOTSTRAP_VIEW,
                ResultShareViewEventType.CONTENT_VIEW,
            }:
                bucket["share_view_count"] += 1
            elif event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT:
                bucket["invite_handoff_redirect_count"] += 1
            elif event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT:
                bucket["collect_handoff_redirect_count"] += 1

        for claim in claims:
            bucket = ensure_bucket(self._invite_claim_activity_at(claim).date())
            if claim.claim_status == GroupWorkspaceInviteClaimStatus.CLAIMED:
                bucket["invite_claimed_count"] += 1
            elif claim.claim_status == GroupWorkspaceInviteClaimStatus.ALREADY_MEMBER:
                bucket["invite_already_member_count"] += 1

        for record in collects:
            bucket = ensure_bucket(record.created_at.date())
            if record.status == GroupWorkspaceResultCollectStatus.COLLECTED:
                bucket["collect_collected_count"] += 1
            elif record.status == GroupWorkspaceResultCollectStatus.ALREADY_PRESENT:
                bucket["collect_already_present_count"] += 1

        return [buckets[day_value] for day_value in sorted(buckets)]

    def _conversion_top_workspaces(
        self,
        *,
        events: Sequence[ResultShareViewEvent],
        claims: Sequence[GroupWorkspaceInviteClaim],
        collects: Sequence[GroupWorkspaceResultCollectRecord],
        limit: int,
    ) -> list[dict[str, Any]]:
        aggregates: dict[UUID, dict[str, Any]] = {}

        def ensure_workspace_aggregate(workspace_id: UUID) -> dict[str, Any]:
            if workspace_id not in aggregates:
                aggregates[workspace_id] = {
                    "workspace_board_view_count": 0,
                    "invite_handoff_redirect_count": 0,
                    "collect_handoff_redirect_count": 0,
                    "invite_claimed_count": 0,
                    "collect_collected_count": 0,
                    "last_activity_at": None,
                }
            return aggregates[workspace_id]

        for event in events:
            workspace_ref = self._result_share_event_workspace_id(event)
            if workspace_ref is None:
                continue
            aggregate = ensure_workspace_aggregate(workspace_ref)
            if event.share_kind == ResultShareKind.WORKSPACE_BOARD and event.event_type in {
                ResultShareViewEventType.BOOTSTRAP_VIEW,
                ResultShareViewEventType.CONTENT_VIEW,
            }:
                aggregate["workspace_board_view_count"] += 1
            elif event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT:
                aggregate["invite_handoff_redirect_count"] += 1
            elif event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT:
                aggregate["collect_handoff_redirect_count"] += 1
            aggregate["last_activity_at"] = self._max_activity_timestamp(
                aggregate["last_activity_at"],
                event.occurred_at,
            )

        for claim in claims:
            aggregate = ensure_workspace_aggregate(claim.workspace_id)
            if claim.claim_status == GroupWorkspaceInviteClaimStatus.CLAIMED:
                aggregate["invite_claimed_count"] += 1
            aggregate["last_activity_at"] = self._max_activity_timestamp(
                aggregate["last_activity_at"],
                self._invite_claim_activity_at(claim),
            )

        for record in collects:
            aggregate = ensure_workspace_aggregate(record.workspace_id)
            if record.status == GroupWorkspaceResultCollectStatus.COLLECTED:
                aggregate["collect_collected_count"] += 1
            aggregate["last_activity_at"] = self._max_activity_timestamp(
                aggregate["last_activity_at"],
                record.created_at,
            )

        rows: list[dict[str, Any]] = []
        for workspace_id, aggregate in aggregates.items():
            workspace = self.get_workspace(workspace_id)
            rows.append(
                {
                    "workspace": self._workspace_safe_summary(workspace),
                    **aggregate,
                }
            )

        def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
            score = (
                row["workspace_board_view_count"]
                + row["invite_handoff_redirect_count"]
                + row["collect_handoff_redirect_count"]
                + row["invite_claimed_count"]
                + row["collect_collected_count"]
            )
            last_activity = row["last_activity_at"] or datetime.min.replace(tzinfo=UTC)
            return (score, last_activity, row["workspace"]["name"])

        rows.sort(key=sort_key, reverse=True)
        return rows[:limit]

    def _conversion_top_result_share_grants(
        self,
        *,
        events: Sequence[ResultShareViewEvent],
        collects: Sequence[GroupWorkspaceResultCollectRecord],
        limit: int,
    ) -> list[dict[str, Any]]:
        aggregates: dict[UUID, dict[str, Any]] = {}

        def ensure_grant_aggregate(
            grant_id: UUID,
            *,
            share_kind: ResultShareKind,
        ) -> dict[str, Any]:
            if grant_id not in aggregates:
                aggregates[grant_id] = {
                    "result_share_grant_id": grant_id,
                    "share_kind": share_kind,
                    "bootstrap_view_count": 0,
                    "content_view_count": 0,
                    "invite_handoff_redirect_count": 0,
                    "collect_handoff_redirect_count": 0,
                    "collect_collected_count": 0,
                    "last_activity_at": None,
                }
            return aggregates[grant_id]

        for event in events:
            if event.result_share_grant_id is None:
                continue
            aggregate = ensure_grant_aggregate(
                event.result_share_grant_id,
                share_kind=event.share_kind,
            )
            if event.event_type == ResultShareViewEventType.BOOTSTRAP_VIEW:
                aggregate["bootstrap_view_count"] += 1
            elif event.event_type == ResultShareViewEventType.CONTENT_VIEW:
                aggregate["content_view_count"] += 1
            elif event.event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT:
                aggregate["invite_handoff_redirect_count"] += 1
            elif event.event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT:
                aggregate["collect_handoff_redirect_count"] += 1
            aggregate["last_activity_at"] = self._max_activity_timestamp(
                aggregate["last_activity_at"],
                event.occurred_at,
            )

        for record in collects:
            if record.result_share_grant_id is None:
                continue
            aggregate = ensure_grant_aggregate(
                record.result_share_grant_id,
                share_kind=record.share_kind,
            )
            if record.status == GroupWorkspaceResultCollectStatus.COLLECTED:
                aggregate["collect_collected_count"] += 1
            aggregate["last_activity_at"] = self._max_activity_timestamp(
                aggregate["last_activity_at"],
                record.created_at,
            )

        rows = list(aggregates.values())

        def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
            score = (
                row["bootstrap_view_count"]
                + row["content_view_count"]
                + row["invite_handoff_redirect_count"]
                + row["collect_handoff_redirect_count"]
                + row["collect_collected_count"]
            )
            last_activity = row["last_activity_at"] or datetime.min.replace(tzinfo=UTC)
            return (score, last_activity, str(row["result_share_grant_id"]))

        rows.sort(key=sort_key, reverse=True)
        return rows[:limit]

    def _conversion_drilldown_notes(
        self,
        *,
        workspace_overview: bool,
        attribution_scope: dict[str, Any],
    ) -> list[str]:
        notes = list(attribution_scope.get("notes", []))
        notes.append(
            "Daily buckets count bootstrap/content share views separately from invite and "
            "collect handoff redirects."
        )
        if workspace_overview:
            notes.append(
                "Active share-grant and invite-grant snapshots describe current workspace "
                "inventory and do not imply causal conversion."
            )
        else:
            notes.append(
                "Top result-share grants include only records with persisted "
                "result_share_grant_id links."
            )
            notes.append(
                "Top workspaces combine direct share-event and collect signals with "
                "workspace-level invite claim aggregates."
            )
        return notes

    def _max_activity_timestamp(
        self,
        left: datetime | None,
        right: datetime | None,
    ) -> datetime | None:
        if left is None:
            return right
        if right is None:
            return left
        return left if left >= right else right

    def create_result_share_grant(
        self,
        *,
        share_kind: ResultShareKind,
        workspace_id: UUID | None,
        digest_issue_id: UUID | None,
        paper_id: UUID | None,
        display_label: str | None,
        issued_by_admin_id: UUID | None,
        expires_at: datetime | None,
    ) -> tuple[ResultShareGrant, IssuedResultShareGrant]:
        workspace = None
        digest_issue = None
        paper = None
        if share_kind == ResultShareKind.WORKSPACE_BOARD:
            if workspace_id is None or digest_issue_id is not None or paper_id is not None:
                raise ValidationFailedError(
                    "workspace_board share grants require workspace_id only",
                    errors=[
                        {
                            "field_id": "share_kind",
                            "code": "target_mismatch",
                            "message": "workspace_board share grants require workspace_id only",
                        }
                    ],
                )
            workspace = self.get_workspace(workspace_id)
        elif share_kind == ResultShareKind.DIGEST_ISSUE:
            if digest_issue_id is None or workspace_id is not None or paper_id is not None:
                raise ValidationFailedError(
                    "digest_issue share grants require digest_issue_id only",
                    errors=[
                        {
                            "field_id": "share_kind",
                            "code": "target_mismatch",
                            "message": "digest_issue share grants require digest_issue_id only",
                        }
                    ],
                )
            digest_issue = self.digest_repository.get_digest_issue(digest_issue_id)
            if digest_issue is None:
                raise NotFoundError(f"digest issue {digest_issue_id} was not found")
        elif share_kind == ResultShareKind.PAPER_SNAPSHOT:
            if paper_id is None or workspace_id is not None or digest_issue_id is not None:
                raise ValidationFailedError(
                    "paper_snapshot share grants require paper_id only",
                    errors=[
                        {
                            "field_id": "share_kind",
                            "code": "target_mismatch",
                            "message": "paper_snapshot share grants require paper_id only",
                        }
                    ],
                )
            paper = self.paper_repository.get(paper_id)
            if paper is None:
                raise NotFoundError(f"paper {paper_id} was not found")
        else:
            raise ValidationFailedError(
                "unsupported result share kind",
                errors=[
                    {
                        "field_id": "share_kind",
                        "code": "unsupported",
                        "message": "unsupported result share kind",
                    }
                ],
            )

        raw_token = generate_refresh_token()
        grant = ResultShareGrant(
            share_kind=share_kind,
            workspace_id=None if workspace is None else workspace.id,
            digest_issue_id=None if digest_issue is None else digest_issue.id,
            paper_id=None if paper is None else paper.id,
            token_hash=hash_token(raw_token),
            status=ResultShareGrantStatus.ACTIVE,
            display_label=display_label,
            issued_by_admin_id=issued_by_admin_id,
            expires_at=expires_at,
        )
        self.repository.add_result_share_grant(grant)
        commit_session(self.session)
        persisted = self.get_result_share_grant(grant.id)
        self.metrics.increment("result_share_grants_issued_total")
        return persisted, IssuedResultShareGrant(
            grant_id=persisted.id,
            plain_text_token=raw_token,
            expires_at=persisted.expires_at,
        )

    def revoke_result_share_grant(self, grant_id: UUID) -> ResultShareGrant:
        grant = self.get_result_share_grant(grant_id)
        if grant.status != ResultShareGrantStatus.REVOKED:
            grant.status = ResultShareGrantStatus.REVOKED
            commit_session(self.session)
        return self.get_result_share_grant(grant_id)

    def create_result_share_alias(
        self,
        *,
        result_share_grant_id: UUID,
        display_label: str | None,
        issued_by_admin_id: UUID | None,
        expires_at: datetime | None,
    ) -> tuple[ResultShareAlias, IssuedResultShareAlias]:
        self._ensure_result_share_alias_enabled()
        grant = self.get_result_share_grant(result_share_grant_id)
        now = self.now_provider()
        effective_expires_at = expires_at
        if effective_expires_at is None and self.settings.result_share_alias_ttl_hours > 0:
            effective_expires_at = now + timedelta(hours=self.settings.result_share_alias_ttl_hours)
        raw_alias = self._generate_result_share_alias()
        alias = ResultShareAlias(
            result_share_grant_id=grant.id,
            alias_hash=hash_token(raw_alias),
            alias_prefix=raw_alias[:6],
            status=ResultShareAliasStatus.ACTIVE,
            display_label=display_label,
            issued_by_admin_id=issued_by_admin_id,
            expires_at=effective_expires_at,
        )
        self.repository.add_result_share_alias(alias)
        commit_session(self.session)
        persisted = self.get_result_share_alias(alias.id)
        self.metrics.increment("result_share_aliases_issued_total")
        return persisted, IssuedResultShareAlias(
            alias_id=persisted.id,
            plain_text_alias=raw_alias,
            expires_at=persisted.expires_at,
        )

    def revoke_result_share_alias(self, alias_id: UUID) -> ResultShareAlias:
        alias = self.get_result_share_alias(alias_id)
        if alias.status != ResultShareAliasStatus.REVOKED:
            alias.status = ResultShareAliasStatus.REVOKED
            commit_session(self.session)
        return self.get_result_share_alias(alias_id)

    def authenticate_share_token(self, raw_token: str) -> ResultShareGrantContext:
        grant = self.repository.get_result_share_grant_by_token_hash(hash_token(raw_token))
        if grant is None:
            raise AuthenticationError("result share grant was not found")
        now = self.now_provider()
        if grant.status == ResultShareGrantStatus.REVOKED:
            raise AuthenticationError("result share grant has been revoked")
        if grant.status == ResultShareGrantStatus.EXPIRED:
            raise AuthenticationError("result share grant has expired")
        if self._mark_expired_if_needed(grant, now=now):
            raise AuthenticationError("result share grant has expired")
        grant.last_used_at = now
        commit_session(self.session)
        return ResultShareGrantContext(
            grant_id=grant.id,
            share_kind=grant.share_kind,
            workspace_id=grant.workspace_id,
            digest_issue_id=grant.digest_issue_id,
            paper_id=grant.paper_id,
            status=grant.status,
            display_label=grant.display_label,
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def authenticate_share_alias(self, raw_alias: str) -> ResultShareAliasContext:
        self._ensure_result_share_alias_enabled()
        alias = self.repository.get_result_share_alias_by_hash(hash_token(raw_alias))
        if alias is None:
            raise AuthenticationError("result share alias was not found")
        now = self.now_provider()
        if alias.status == ResultShareAliasStatus.REVOKED:
            raise AuthenticationError("result share alias has been revoked")
        if alias.status == ResultShareAliasStatus.EXPIRED:
            raise AuthenticationError("result share alias has expired")
        if self._mark_alias_expired_if_needed(alias, now=now):
            raise AuthenticationError("result share alias has expired")
        grant = alias.result_share_grant or self.get_result_share_grant(alias.result_share_grant_id)
        if grant.status == ResultShareGrantStatus.REVOKED:
            raise AuthenticationError("result share grant has been revoked")
        if grant.status == ResultShareGrantStatus.EXPIRED:
            raise AuthenticationError("result share grant has expired")
        if self._mark_expired_if_needed(grant, now=now):
            raise AuthenticationError("result share grant has expired")
        alias.last_used_at = now
        grant.last_used_at = now
        commit_session(self.session)
        self.metrics.increment("result_share_alias_resolutions_total")
        return ResultShareAliasContext(
            alias_id=alias.id,
            grant_id=grant.id,
            share_kind=grant.share_kind,
            workspace_id=grant.workspace_id,
            digest_issue_id=grant.digest_issue_id,
            paper_id=grant.paper_id,
            status=alias.status,
            display_label=alias.display_label,
            expires_at=alias.expires_at,
            last_used_at=alias.last_used_at,
        )

    def safe_record_result_share_view_event(
        self,
        *,
        access_mode: ResultShareViewAccessMode,
        event_type: ResultShareViewEventType,
        outcome: ResultShareViewOutcome,
        handoff_target_kind: ResultShareHandoffTargetKind | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        client_host: str | None = None,
        accept_language: str | None = None,
        grant_context: ResultShareGrantContext | None = None,
        alias_context: ResultShareAliasContext | None = None,
        raw_share_token: str | None = None,
        raw_alias: str | None = None,
    ) -> None:
        if not self.settings.result_share_analytics_enabled:
            return
        try:
            self._record_result_share_view_event(
                access_mode=access_mode,
                event_type=event_type,
                outcome=outcome,
                handoff_target_kind=handoff_target_kind,
                referrer=referrer,
                user_agent=user_agent,
                client_host=client_host,
                accept_language=accept_language,
                grant_context=grant_context,
                alias_context=alias_context,
                raw_share_token=raw_share_token,
                raw_alias=raw_alias,
            )
        except Exception:
            self.session.rollback()
            logger.warning(
                "result share analytics event recording failed",
                exc_info=True,
                extra={
                    "share_kind": None if grant_context is None else grant_context.share_kind.value,
                    "access_mode": access_mode.value,
                    "event_type": event_type.value,
                    "outcome": outcome.value,
                    "result_share_grant_id": (
                        None if grant_context is None else str(grant_context.grant_id)
                    ),
                    "result_share_alias_id": (
                        None if alias_context is None else str(alias_context.alias_id)
                    ),
                    "handoff_target_kind": (
                        None if handoff_target_kind is None else handoff_target_kind.value
                    ),
                },
            )

    def build_share_alias_redirect_url(self, raw_alias: str) -> str:
        if not self.settings.result_share_redirect_enabled:
            raise ValidationFailedError("result share alias redirect is disabled")
        entry_url = self.settings.result_share_web_entry_url
        if not entry_url:
            raise ValidationFailedError("result share web entry URL is not configured")
        self.authenticate_share_alias(raw_alias)
        self.metrics.increment("result_share_alias_redirects_total")
        return f"{entry_url}/share-alias/{raw_alias}"

    def build_result_share_invite_handoff_redirect_url(
        self,
        *,
        share_kind: ResultShareKind,
    ) -> str:
        self._ensure_result_share_invite_handoff_enabled()
        if share_kind not in self.settings.result_share_invite_handoff_allowed_share_kind_list:
            raise ValidationFailedError(
                "result share invite handoff is not supported for this share"
            )
        entry_url = self.settings.group_workspace_invite_web_entry_url
        if not entry_url:
            raise ValidationFailedError("group workspace invite web entry URL is not configured")
        return self._append_public_query_params(
            entry_url,
            {"from": "workspace_board_share"},
        )

    def build_result_share_collect_handoff_redirect_url(
        self,
        *,
        share_kind: ResultShareKind,
    ) -> str:
        self._ensure_result_share_collect_handoff_enabled()
        if share_kind not in self.settings.result_share_collect_handoff_allowed_share_kind_list:
            raise ValidationFailedError(
                "result share collect handoff is not supported for this share"
            )
        entry_url = self.settings.result_share_web_entry_url
        if not entry_url:
            raise ValidationFailedError("result share web entry URL is not configured")
        return self._append_public_query_params(
            entry_url,
            {"from": "workspace_board_collect_handoff"},
        )

    def _record_result_share_view_event(
        self,
        *,
        access_mode: ResultShareViewAccessMode,
        event_type: ResultShareViewEventType,
        outcome: ResultShareViewOutcome,
        handoff_target_kind: ResultShareHandoffTargetKind | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        client_host: str | None = None,
        accept_language: str | None = None,
        grant_context: ResultShareGrantContext | None = None,
        alias_context: ResultShareAliasContext | None = None,
        raw_share_token: str | None = None,
        raw_alias: str | None = None,
    ) -> None:
        subject = self._resolve_result_share_view_event_subject(
            grant_context=grant_context,
            alias_context=alias_context,
            raw_share_token=raw_share_token,
            raw_alias=raw_alias,
        )
        if subject is None:
            return
        referrer_host = self._extract_result_share_referrer_host(referrer)
        user_agent_family = self._extract_result_share_user_agent_family(user_agent)
        fingerprint = self._build_result_share_request_fingerprint(
            client_host=client_host,
            referrer_host=referrer_host,
            user_agent_family=user_agent_family,
            accept_language=accept_language,
        )
        event = ResultShareViewEvent(
            result_share_grant_id=subject["grant_id"],
            result_share_alias_id=subject["alias_id"],
            share_kind=subject["share_kind"],
            access_mode=access_mode,
            event_type=event_type,
            outcome=outcome,
            handoff_target_kind=handoff_target_kind,
            request_fingerprint_hash=fingerprint,
            referrer_host=referrer_host,
            user_agent_family=user_agent_family,
            occurred_at=self.now_provider(),
        )
        self.repository.add_result_share_view_event(event)
        commit_session(self.session)
        self.metrics.increment("result_share_view_events_recorded_total")
        if event_type == ResultShareViewEventType.BOOTSTRAP_VIEW:
            self.metrics.increment("result_share_bootstrap_views_total")
        elif event_type == ResultShareViewEventType.CONTENT_VIEW:
            self.metrics.increment("result_share_content_views_total")
        elif event_type == ResultShareViewEventType.REDIRECT:
            self.metrics.increment("result_share_redirect_views_total")
        elif event_type == ResultShareViewEventType.INVITE_HANDOFF_REDIRECT:
            self.metrics.increment("result_share_invite_handoff_redirects_total")
        elif event_type == ResultShareViewEventType.COLLECT_HANDOFF_REDIRECT:
            self.metrics.increment("result_share_collect_handoff_redirects_total")

    def _resolve_result_share_view_event_subject(
        self,
        *,
        grant_context: ResultShareGrantContext | None,
        alias_context: ResultShareAliasContext | None,
        raw_share_token: str | None,
        raw_alias: str | None,
    ) -> dict[str, Any] | None:
        if grant_context is not None:
            return {
                "grant_id": grant_context.grant_id,
                "alias_id": None if alias_context is None else alias_context.alias_id,
                "share_kind": grant_context.share_kind,
            }
        if alias_context is not None:
            return {
                "grant_id": alias_context.grant_id,
                "alias_id": alias_context.alias_id,
                "share_kind": alias_context.share_kind,
            }
        if raw_alias:
            alias = self.repository.get_result_share_alias_by_hash(hash_token(raw_alias))
            if alias is not None:
                grant = alias.result_share_grant or self.repository.get_result_share_grant(
                    alias.result_share_grant_id
                )
                if grant is not None:
                    return {
                        "grant_id": grant.id,
                        "alias_id": alias.id,
                        "share_kind": grant.share_kind,
                    }
        if raw_share_token:
            grant = self.repository.get_result_share_grant_by_token_hash(
                hash_token(raw_share_token)
            )
            if grant is not None:
                return {
                    "grant_id": grant.id,
                    "alias_id": None,
                    "share_kind": grant.share_kind,
                }
        return None

    def _extract_result_share_referrer_host(self, referrer: str | None) -> str | None:
        if not self.settings.result_share_analytics_capture_referrer_host or not referrer:
            return None
        parsed = urlparse(referrer.strip())
        return parsed.hostname.lower() if parsed.hostname else None

    def _extract_result_share_user_agent_family(self, user_agent: str | None) -> str | None:
        if not self.settings.result_share_analytics_capture_user_agent_family or not user_agent:
            return None
        normalized = user_agent.strip().lower()
        if not normalized:
            return None
        if any(token in normalized for token in ("bot", "crawler", "spider")):
            return "bot"
        if "edg/" in normalized or "edge/" in normalized:
            return "edge"
        if "firefox/" in normalized:
            return "firefox"
        if "chrome/" in normalized or "crios/" in normalized:
            return "chrome"
        if "safari/" in normalized:
            return "safari"
        if "curl/" in normalized:
            return "curl"
        if "wget/" in normalized:
            return "wget"
        if "python-requests" in normalized:
            return "python-requests"
        return "other"

    def _build_result_share_request_fingerprint(
        self,
        *,
        client_host: str | None,
        referrer_host: str | None,
        user_agent_family: str | None,
        accept_language: str | None,
    ) -> str | None:
        if not self.settings.result_share_analytics_enable_fingerprint:
            return None
        normalized_accept_language = (accept_language or "").split(",")[0].strip().lower()
        payload = "|".join(
            (
                self.settings.result_share_analytics_fingerprint_salt or "",
                client_host or "",
                referrer_host or "",
                user_agent_family or "",
                normalized_accept_language,
            )
        )
        if not payload.replace("|", ""):
            return None
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _result_share_event_workspace_id(self, event: ResultShareViewEvent) -> UUID | None:
        if event.result_share_grant is not None:
            return event.result_share_grant.workspace_id
        if event.result_share_grant_id is None:
            return None
        grant = self.repository.get_result_share_grant(event.result_share_grant_id)
        return None if grant is None else grant.workspace_id

    def _invite_claim_activity_at(self, claim: GroupWorkspaceInviteClaim) -> datetime:
        return claim.claimed_at or claim.updated_at or claim.created_at

    def _timestamp_in_window(
        self,
        timestamp: datetime,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> bool:
        normalized_timestamp = self._normalize_utc_timestamp(timestamp)
        normalized_from = None if date_from is None else self._normalize_utc_timestamp(date_from)
        normalized_to = None if date_to is None else self._normalize_utc_timestamp(date_to)
        if normalized_from is not None and normalized_timestamp < normalized_from:
            return False
        if normalized_to is not None and normalized_timestamp > normalized_to:
            return False
        return True

    def _normalize_utc_timestamp(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _result_collect_record_matches_share_kind(
        self,
        record: GroupWorkspaceResultCollectRecord,
        *,
        share_kind: ResultShareKind | None,
    ) -> bool:
        return share_kind is None or record.share_kind == share_kind

    def _conversion_attribution_scope_summary(
        self,
        *,
        workspace_overview: bool,
        include_inventory_metrics: bool,
        include_workspace_metrics: bool,
        share_filter_applied: bool,
        event_filters_applied: bool,
    ) -> dict[str, Any]:
        if workspace_overview:
            direct_metrics = [
                "active_workspace_board_share_grant_count",
                "active_digest_issue_share_grant_count",
                "active_paper_snapshot_share_grant_count",
                "active_invite_grant_count",
                "workspace_board_view_count",
                "invite_handoff_redirect_count",
                "collect_handoff_redirect_count",
                "collect_collected_count",
                "collect_already_present_count",
            ]
            workspace_level_metrics = [
                "invite_claimed_count",
                "invite_already_member_count",
            ]
        else:
            direct_metrics = [
                "total_share_view_events",
                "bootstrap_view_count",
                "content_view_count",
                "redirect_count",
                "invite_handoff_redirect_count",
                "collect_handoff_redirect_count",
                "resolved_event_count",
                "rejected_event_count",
                "by_share_kind",
                "by_access_mode",
                "by_handoff_target",
                "collect_collected_count",
                "collect_already_present_count",
                "collect_rejected_count",
                "unique_result_share_grant_count",
            ]
            workspace_level_metrics = [
                "invite_claimed_count",
                "invite_already_member_count",
                "invite_rejected_count",
                "unique_workspace_count",
            ]
        notes = [
            (
                "Invite claim metrics are workspace-level aggregate signals in v1 and are not "
                "strict per-share causal attribution."
            ),
            (
                "Collect metrics are directly linked when result_share_grant_id is present; "
                "records without that link remain aggregate-only signals."
            ),
        ]
        if workspace_overview:
            notes.append(
                "workspace digest_issue and paper_snapshot share-grant counts are derived "
                "from active share grants linked through collect records into this "
                "workspace."
            )
        if share_filter_applied:
            notes.append(
                "share_kind filters scope view-event metrics and collect records; invite "
                "claims remain workspace-level aggregates."
            )
        if event_filters_applied:
            notes.append(
                "access_mode and event_type filters scope only "
                "ResultShareViewEvent-derived metrics."
            )
        if include_inventory_metrics:
            direct_metrics.extend(
                [
                    "active_workspace_board_share_grant_count",
                    "active_digest_issue_share_grant_count",
                    "active_paper_snapshot_share_grant_count",
                    "active_invite_grant_count",
                ]
            )
        if include_workspace_metrics:
            workspace_level_metrics.extend(
                [
                    "unique_collected_paper_count",
                    "unique_collecting_user_count",
                ]
            )
        return {
            "direct_attribution_metrics": direct_metrics,
            "workspace_level_aggregate_metrics": workspace_level_metrics,
            "notes": notes,
        }

    def _normalize_result_share_analytics_window(
        self,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[datetime | None, datetime | None]:
        if date_from is not None and date_to is not None and date_to < date_from:
            raise ValidationFailedError("date_to must be greater than or equal to date_from")
        normalized_from = date_from
        if (
            normalized_from is None
            and self.settings.result_share_analytics_default_lookback_days > 0
        ):
            normalized_from = self.now_provider() - timedelta(
                days=self.settings.result_share_analytics_default_lookback_days
            )
        return normalized_from, date_to

    def _ensure_result_share_invite_handoff_enabled(self) -> None:
        if not self.settings.result_share_invite_handoff_enabled:
            raise ValidationFailedError("result share invite handoff is disabled")

    def _share_invite_handoff_redirect_supported(self, share_kind: ResultShareKind) -> bool:
        if not self.settings.result_share_invite_handoff_enabled:
            return False
        if self.settings.group_workspace_invite_web_entry_url is None:
            return False
        return share_kind in self.settings.result_share_invite_handoff_allowed_share_kind_list

    def _ensure_result_share_collect_handoff_enabled(self) -> None:
        if not self.settings.result_share_collect_handoff_enabled:
            raise ValidationFailedError("result share collect handoff is disabled")

    def _share_result_collect_handoff_redirect_supported(self, share_kind: ResultShareKind) -> bool:
        if not self.settings.result_share_collect_handoff_enabled:
            return False
        if self.settings.result_share_web_entry_url is None:
            return False
        return share_kind in self.settings.result_share_collect_handoff_allowed_share_kind_list

    def _build_share_invite_handoff_public_url(
        self,
        *,
        share_kind: ResultShareKind,
        access_mode: ResultShareViewAccessMode | None,
        access_value: str | None,
    ) -> str | None:
        if access_mode not in {
            ResultShareViewAccessMode.SHARE_TOKEN,
            ResultShareViewAccessMode.ALIAS,
        }:
            return None
        if not access_value or not self._share_invite_handoff_redirect_supported(share_kind):
            return None
        encoded_value = quote(access_value, safe="")
        if access_mode == ResultShareViewAccessMode.SHARE_TOKEN:
            return f"/result-shares/{encoded_value}/invite-handoff"
        return f"/share-aliases/{encoded_value}/invite-handoff"

    def _build_share_result_collect_handoff_public_url(
        self,
        *,
        share_kind: ResultShareKind,
        access_mode: ResultShareViewAccessMode | None,
        access_value: str | None,
    ) -> str | None:
        if access_mode not in {
            ResultShareViewAccessMode.SHARE_TOKEN,
            ResultShareViewAccessMode.ALIAS,
        }:
            return None
        if not access_value or not self._share_result_collect_handoff_redirect_supported(
            share_kind
        ):
            return None
        encoded_value = quote(access_value, safe="")
        if access_mode == ResultShareViewAccessMode.SHARE_TOKEN:
            return f"/result-shares/{encoded_value}/collect-handoff"
        return f"/share-aliases/{encoded_value}/collect-handoff"

    def _append_public_query_params(self, base_url: str, params: dict[str, str]) -> str:
        split = urlsplit(base_url)
        query_items = dict(parse_qsl(split.query, keep_blank_values=True))
        query_items.update(params)
        return urlunsplit(
            (
                split.scheme,
                split.netloc,
                split.path,
                urlencode(query_items),
                split.fragment,
            )
        )

    def share_bootstrap(
        self,
        grant: ResultShareGrantContext,
        *,
        access_mode: ResultShareViewAccessMode | None = None,
        access_value: str | None = None,
    ) -> dict[str, Any]:
        stored = self.get_result_share_grant(grant.grant_id)
        with bind_log_context(
            result_share_grant_id=stored.id,
            share_kind=stored.share_kind.value,
            workspace_id=stored.workspace_id,
        ):
            return {
                "grant": {
                    "id": stored.id,
                    "share_kind": stored.share_kind,
                    "display_label": stored.display_label,
                    "status": stored.status,
                    "expires_at": stored.expires_at,
                    "created_at": stored.created_at,
                },
                "target": self._share_target_summary(stored),
                "collection_reserve": self._share_collection_reserve_summary(stored),
                "workspace_invite_handoff_reserve": self._share_workspace_invite_handoff_summary(
                    stored,
                    access_mode=access_mode,
                    access_value=access_value,
                ),
                "result_collect_handoff_reserve": self._share_result_collect_handoff_summary(
                    stored,
                    access_mode=access_mode,
                    access_value=access_value,
                ),
                "notes": [
                    "This share link exposes structured read-only results only.",
                    "Source files, local attachments, and local note contents are excluded.",
                ],
            }

    def share_content(self, grant: ResultShareGrantContext) -> dict[str, Any]:
        stored = self.get_result_share_grant(grant.grant_id)
        with bind_log_context(
            result_share_grant_id=stored.id,
            share_kind=stored.share_kind.value,
            workspace_id=stored.workspace_id,
        ):
            self.metrics.increment("result_share_content_requests_total")
            if stored.share_kind == ResultShareKind.DIGEST_ISSUE:
                if stored.digest_issue is None:
                    raise NotFoundError("shared digest issue was not found")
                return self._shared_digest_issue_payload(stored.digest_issue)
            if stored.share_kind == ResultShareKind.PAPER_SNAPSHOT:
                if stored.paper is None:
                    raise NotFoundError("shared paper was not found")
                return self._shared_paper_snapshot_payload(stored.paper)
            if stored.share_kind == ResultShareKind.WORKSPACE_BOARD:
                if stored.workspace is None:
                    raise NotFoundError("shared workspace was not found")
                return self._shared_workspace_board_payload(stored.workspace)
            raise NotFoundError("shared content was not found")

    def self_service_workspace_memberships(
        self,
        *,
        user_id: UUID,
    ) -> list[dict[str, Any]]:
        return [
            self._workspace_membership_summary(membership)
            for membership in self.list_workspace_memberships_for_user(user_id=user_id)
        ]

    def preview_result_share_collect(
        self,
        *,
        raw_token: str,
        grant: SubscriptionSelfServiceGrantContext,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_result_collect_previews_total")
        evaluation = self._evaluate_collect_preview(raw_token=raw_token, user_id=grant.user_id)
        return {
            "share": (
                None
                if evaluation["share_grant"] is None
                else self._result_collect_share_summary(evaluation["share_grant"])
            ),
            "collectable_items": list(evaluation["collectable_items"]),
            "eligible_workspaces": list(evaluation["eligible_workspaces"]),
            "can_collect": evaluation["can_collect"],
            "reason_codes": list(evaluation["reason_codes"]),
            "notes": list(evaluation["notes"]),
        }

    def preview_result_share_collect_by_alias(
        self,
        *,
        raw_alias: str,
        grant: SubscriptionSelfServiceGrantContext,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_result_collect_previews_total")
        evaluation = self._evaluate_collect_preview_by_alias(
            raw_alias=raw_alias,
            user_id=grant.user_id,
        )
        return {
            "share": (
                None
                if evaluation["share_grant"] is None
                else self._result_collect_share_summary(evaluation["share_grant"])
            ),
            "collectable_items": list(evaluation["collectable_items"]),
            "eligible_workspaces": list(evaluation["eligible_workspaces"]),
            "can_collect": evaluation["can_collect"],
            "reason_codes": list(evaluation["reason_codes"]),
            "notes": list(evaluation["notes"]),
        }

    def collect_result_share(
        self,
        *,
        raw_token: str,
        grant: SubscriptionSelfServiceGrantContext,
        workspace_id: UUID,
        paper_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_result_collect_actions_total")
        evaluation = self._evaluate_collect_preview(raw_token=raw_token, user_id=grant.user_id)
        return self._collect_result_share_from_evaluation(
            evaluation=evaluation,
            grant=grant,
            workspace_id=workspace_id,
            paper_ids=paper_ids,
        )

    def _collect_result_share_from_evaluation(
        self,
        *,
        evaluation: dict[str, Any],
        grant: SubscriptionSelfServiceGrantContext,
        workspace_id: UUID,
        paper_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        share_grant: ResultShareGrant | None = evaluation["share_grant"]
        if share_grant is None:
            return {
                "action": "rejected",
                "workspace": None,
                "collected_results": [],
                "notes": list(evaluation["reason_codes"] or ["share_not_found"]),
            }

        workspace = self.repository.get_workspace(workspace_id)
        membership = self.repository.get_workspace_member_for_user(
            workspace_id=workspace_id,
            user_id=grant.user_id,
        )
        request_reasons = list(evaluation["reason_codes"])
        if workspace is None or membership is None:
            request_reasons.append("workspace_not_found")
        else:
            if workspace.status != GroupWorkspaceStatus.ACTIVE:
                request_reasons.append("workspace_archived")
            if (
                membership.role
                not in self.settings.group_workspace_result_collect_allowed_role_list
            ):
                request_reasons.append("role_not_allowed")
        request_reasons = self._dedupe_reason_codes(request_reasons)
        if request_reasons:
            return {
                "action": "rejected",
                "workspace": None if workspace is None else self._workspace_safe_summary(workspace),
                "collected_results": [],
                "notes": request_reasons,
            }

        assert workspace is not None
        selected_items, selection_reason_codes = self._select_collectable_items(
            share_kind=share_grant.share_kind,
            collectable_items=evaluation["collectable_items"],
            paper_ids=paper_ids,
        )
        if selection_reason_codes:
            return {
                "action": "rejected",
                "workspace": self._workspace_safe_summary(workspace),
                "collected_results": [],
                "notes": selection_reason_codes,
            }

        collected_results: list[dict[str, Any]] = []
        any_collected = False
        all_already_present = True
        for item in selected_items:
            result_status, record = self._collect_single_result_item(
                share_grant=share_grant,
                workspace=workspace,
                user_id=grant.user_id,
                item=item,
            )
            if result_status == GroupWorkspaceResultCollectStatus.COLLECTED:
                any_collected = True
                all_already_present = False
            elif result_status != GroupWorkspaceResultCollectStatus.ALREADY_PRESENT:
                all_already_present = False
            collected_results.append(
                {
                    "paper_id": item["paper_id"],
                    "status": result_status,
                    "reason_codes": (
                        ["already_present"]
                        if result_status == GroupWorkspaceResultCollectStatus.ALREADY_PRESENT
                        else []
                    ),
                    "collect_record": (
                        None if record is None else self.serialize_result_collect_record(record)
                    ),
                    "paper": self._collected_paper_summary(
                        self._require_paper(UUID(str(item["paper_id"])))
                    ),
                }
            )

        commit_session(self.session)
        return {
            "action": (
                "collected"
                if any_collected
                else "already_present"
                if all_already_present
                else "rejected"
            ),
            "workspace": self._workspace_safe_summary(self.get_workspace(workspace.id)),
            "collected_results": collected_results,
            "notes": [
                "Structured paper objects were collected into the workspace without source files."
            ],
        }

    def collect_result_share_by_alias(
        self,
        *,
        raw_alias: str,
        grant: SubscriptionSelfServiceGrantContext,
        workspace_id: UUID,
        paper_ids: Sequence[UUID] | None = None,
    ) -> dict[str, Any]:
        self.metrics.increment("group_workspace_result_collect_actions_total")
        evaluation = self._evaluate_collect_preview_by_alias(
            raw_alias=raw_alias,
            user_id=grant.user_id,
        )
        return self._collect_result_share_from_evaluation(
            evaluation=evaluation,
            grant=grant,
            workspace_id=workspace_id,
            paper_ids=paper_ids,
        )

    def self_service_workspace_result_collections(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID | None = None,
        status: GroupWorkspaceResultCollectStatus | None = None,
    ) -> list[dict[str, Any]]:
        records = self.list_result_collect_records(
            workspace_id=workspace_id,
            user_id=user_id,
            status=status,
        )
        payloads: list[dict[str, Any]] = []
        for record in records:
            if record.workspace is None or record.collected_paper is None:
                continue
            payloads.append(
                {
                    "record": self.serialize_result_collect_record(record),
                    "workspace": self._workspace_safe_summary(record.workspace),
                    "paper": self._collected_paper_summary(record.collected_paper),
                }
            )
        return payloads

    def mini_workspace_invite_reserve(self) -> dict[str, Any]:
        return {
            "supported": True,
            "editable_via_current_mini_grant": False,
            "separate_self_service_grant_required": True,
            "claim_supported_via_self_service": True,
            "notes": [
                "Mini remains read-only in this phase.",
                "Claiming workspace membership requires a separate self-service grant.",
            ],
        }

    def mini_workspace_collect_reserve(self) -> dict[str, Any]:
        return {
            "supported": True,
            "editable_via_current_mini_grant": False,
            "separate_self_service_grant_required": True,
            "supported_share_kinds": [
                ResultShareKind.DIGEST_ISSUE.value,
                ResultShareKind.PAPER_SNAPSHOT.value,
            ],
            "notes": [
                "Mini remains read-only in this phase.",
                "Workspace result collection requires a separate self-service grant.",
            ],
        }

    def _ensure_invites_enabled(self) -> None:
        if not self.settings.group_workspace_invites_enabled:
            raise ValidationFailedError(
                "group workspace invites are not enabled",
                errors=[
                    {
                        "field_id": "invites",
                        "code": "invites_disabled",
                        "message": "group workspace invites are not enabled",
                    }
                ],
            )

    def _ensure_public_bootstrap_enabled(self) -> None:
        self._ensure_invites_enabled()
        if not self.settings.group_workspace_invite_public_bootstrap_enabled:
            raise ValidationFailedError(
                "group workspace invite bootstrap is not enabled",
                errors=[
                    {
                        "field_id": "public_bootstrap",
                        "code": "disabled",
                        "message": "group workspace invite bootstrap is not enabled",
                    }
                ],
            )

    def _default_invite_expires_at(self) -> datetime | None:
        ttl_hours = self.settings.group_workspace_invite_ttl_hours
        return self.now_provider() + timedelta(hours=ttl_hours) if ttl_hours is not None else None

    def _refresh_expired_invite_grants(self, grants: Sequence[GroupWorkspaceInviteGrant]) -> None:
        updated = False
        now = self.now_provider()
        for grant in grants:
            updated = self._mark_invite_expired_if_needed(grant, now=now) or updated
        if updated:
            commit_session(self.session)

    def _mark_invite_expired_if_needed(
        self,
        grant: GroupWorkspaceInviteGrant,
        *,
        now: datetime | None = None,
    ) -> bool:
        current_time = self._coerce_utc(now or self.now_provider())
        expires_at = self._coerce_utc(grant.expires_at)
        if (
            grant.status == GroupWorkspaceInviteGrantStatus.ACTIVE
            and expires_at is not None
            and expires_at <= current_time
        ):
            grant.status = GroupWorkspaceInviteGrantStatus.EXPIRED
            return True
        if (
            grant.status == GroupWorkspaceInviteGrantStatus.ACTIVE
            and grant.max_claims is not None
            and grant.claim_count >= grant.max_claims
        ):
            grant.status = GroupWorkspaceInviteGrantStatus.EXHAUSTED
            return True
        return False

    def _evaluate_invite_for_user(
        self,
        *,
        raw_token: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        if not self.settings.group_workspace_invites_enabled:
            return self._invite_evaluation_result(reason_codes=["invites_disabled"])
        invite_grant = self.repository.get_invite_grant_by_token_hash(hash_token(raw_token))
        if invite_grant is None:
            return self._invite_evaluation_result(reason_codes=["invite_not_found"])
        now = self.now_provider()
        self._mark_invite_expired_if_needed(invite_grant, now=now)
        invite_grant.last_used_at = now
        commit_session(self.session)
        workspace = invite_grant.workspace
        membership = self.repository.get_workspace_member_for_user(
            workspace_id=invite_grant.workspace_id,
            user_id=user_id,
        )
        if membership is not None:
            return self._invite_evaluation_result(
                invite_grant=invite_grant,
                workspace=workspace,
                membership=membership,
                reason_codes=["already_member"],
            )
        reason_codes: list[str] = []
        if invite_grant.status == GroupWorkspaceInviteGrantStatus.REVOKED:
            reason_codes.append("invite_revoked")
        elif invite_grant.status == GroupWorkspaceInviteGrantStatus.EXPIRED:
            reason_codes.append("invite_expired")
        elif invite_grant.status == GroupWorkspaceInviteGrantStatus.EXHAUSTED:
            reason_codes.append("invite_exhausted")
        if workspace is None or workspace.status != GroupWorkspaceStatus.ACTIVE:
            reason_codes.append("workspace_archived")
        if invite_grant.role_to_assign not in INVITE_ROLE_ASSIGNABLE_VALUES:
            reason_codes.append("role_not_assignable")
        return self._invite_evaluation_result(
            invite_grant=invite_grant,
            workspace=workspace,
            membership=membership,
            reason_codes=reason_codes,
        )

    def _invite_evaluation_result(
        self,
        *,
        invite_grant: GroupWorkspaceInviteGrant | None = None,
        workspace: GroupWorkspace | None = None,
        membership: GroupWorkspaceMember | None = None,
        reason_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        reasons = list(reason_codes or [])
        return {
            "invite_grant": invite_grant,
            "workspace": workspace,
            "membership": membership,
            "reason_codes": reasons,
            "can_claim": not reasons,
        }

    def _record_invite_claim_if_applicable(
        self,
        *,
        invite_grant: GroupWorkspaceInviteGrant | None,
        workspace: GroupWorkspace | None,
        user_id: UUID,
        membership: GroupWorkspaceMember | None,
        claim_status: GroupWorkspaceInviteClaimStatus,
        reason_codes: list[str],
        claimed_at: datetime | None,
    ) -> GroupWorkspaceInviteClaim | None:
        if invite_grant is None or workspace is None:
            return None
        self._record_invite_claim(
            invite_grant=invite_grant,
            workspace=workspace,
            user_id=user_id,
            membership=membership,
            claim_status=claim_status,
            reason_codes=reason_codes,
            claimed_at=claimed_at,
        )
        commit_session(self.session)
        return self.repository.get_invite_claim(invite_grant_id=invite_grant.id, user_id=user_id)

    def _record_invite_claim(
        self,
        *,
        invite_grant: GroupWorkspaceInviteGrant,
        workspace: GroupWorkspace,
        user_id: UUID,
        membership: GroupWorkspaceMember | None,
        claim_status: GroupWorkspaceInviteClaimStatus,
        reason_codes: list[str],
        claimed_at: datetime | None,
    ) -> GroupWorkspaceInviteClaim:
        existing = self.repository.get_invite_claim(
            invite_grant_id=invite_grant.id,
            user_id=user_id,
        )
        if existing is None:
            existing = GroupWorkspaceInviteClaim(
                invite_grant_id=invite_grant.id,
                workspace_id=workspace.id,
                user_id=user_id,
                membership_id=None if membership is None else membership.id,
                role_assigned=invite_grant.role_to_assign,
                claim_status=claim_status,
                reason_codes=list(reason_codes),
                claimed_at=claimed_at,
            )
            self.repository.add_invite_claim(existing)
            return existing
        existing.workspace_id = workspace.id
        existing.membership_id = None if membership is None else membership.id
        existing.role_assigned = invite_grant.role_to_assign
        existing.claim_status = claim_status
        existing.reason_codes = list(reason_codes)
        if claimed_at is not None:
            existing.claimed_at = claimed_at
        return existing

    def _refresh_expired_grants(self, grants: Sequence[ResultShareGrant]) -> None:
        updated = False
        now = self.now_provider()
        for grant in grants:
            updated = self._mark_expired_if_needed(grant, now=now) or updated
        if updated:
            commit_session(self.session)

    def _refresh_expired_aliases(self, aliases: Sequence[ResultShareAlias]) -> None:
        updated = False
        now = self.now_provider()
        for alias in aliases:
            updated = self._mark_alias_expired_if_needed(alias, now=now) or updated
        if updated:
            commit_session(self.session)

    def _mark_expired_if_needed(
        self,
        grant: ResultShareGrant,
        *,
        now: datetime | None = None,
    ) -> bool:
        current_time = self._coerce_utc(now or self.now_provider())
        expires_at = self._coerce_utc(grant.expires_at)
        if (
            grant.status == ResultShareGrantStatus.ACTIVE
            and expires_at is not None
            and expires_at <= current_time
        ):
            grant.status = ResultShareGrantStatus.EXPIRED
            return True
        return False

    def _mark_alias_expired_if_needed(
        self,
        alias: ResultShareAlias,
        *,
        now: datetime | None = None,
    ) -> bool:
        current_time = self._coerce_utc(now or self.now_provider())
        expires_at = self._coerce_utc(alias.expires_at)
        if (
            alias.status == ResultShareAliasStatus.ACTIVE
            and expires_at is not None
            and expires_at <= current_time
        ):
            alias.status = ResultShareAliasStatus.EXPIRED
            return True
        return False

    def _ensure_result_share_alias_enabled(self) -> None:
        if not self.settings.result_share_alias_enabled:
            raise ValidationFailedError("result share aliasing is disabled")

    def _generate_result_share_alias(self) -> str:
        length = max(8, int(self.settings.result_share_alias_length))
        while True:
            alias = "".join(secrets.choice(RESULT_SHARE_ALIAS_ALPHABET) for _ in range(length))
            if self.repository.get_result_share_alias_by_hash(hash_token(alias)) is None:
                return alias

    def _result_share_grant_context(self, grant: ResultShareGrant) -> ResultShareGrantContext:
        return ResultShareGrantContext(
            grant_id=grant.id,
            share_kind=grant.share_kind,
            workspace_id=grant.workspace_id,
            digest_issue_id=grant.digest_issue_id,
            paper_id=grant.paper_id,
            status=grant.status,
            display_label=grant.display_label,
            expires_at=grant.expires_at,
            last_used_at=grant.last_used_at,
        )

    def _grant_matches_user(self, grant: ResultShareGrant, *, user_id: UUID) -> bool:
        if grant.digest_issue is not None:
            return grant.digest_issue.user_id == user_id
        if grant.paper is not None:
            return grant.paper.user_id == user_id
        if grant.workspace is not None:
            return any(member.user_id == user_id for member in grant.workspace.members)
        return False

    def _workspace_summary(self, workspace: GroupWorkspace) -> dict[str, Any]:
        return {
            "id": workspace.id,
            "slug": workspace.slug,
            "name": workspace.name,
            "description": workspace.description,
            "status": workspace.status,
            "created_by_admin_id": workspace.created_by_admin_id,
            "created_at": workspace.created_at,
            "updated_at": workspace.updated_at,
        }

    def _workspace_safe_summary(self, workspace: GroupWorkspace) -> dict[str, Any]:
        return {
            "id": workspace.id,
            "slug": workspace.slug,
            "name": workspace.name,
            "description": workspace.description,
            "status": workspace.status,
        }

    def _workspace_membership_summary(self, membership: GroupWorkspaceMember) -> dict[str, Any]:
        workspace = membership.workspace
        if workspace is None:
            workspace = self.get_workspace(membership.workspace_id)
        return {
            "member_id": membership.id,
            "workspace_id": membership.workspace_id,
            "user_id": membership.user_id,
            "role": membership.role,
            "joined_at": membership.joined_at,
            "workspace_summary": self._workspace_safe_summary(workspace),
            "result_collect_handoff_reserve": self._result_collect_handoff_reserve_summary(),
        }

    def _public_invite_summary(self, grant: GroupWorkspaceInviteGrant) -> dict[str, Any]:
        return {
            "id": grant.id,
            "workspace_id": grant.workspace_id,
            "role_to_assign": grant.role_to_assign,
            "status": grant.status,
            "display_label": grant.display_label,
            "max_claims": grant.max_claims,
            "claim_count": grant.claim_count,
            "expires_at": grant.expires_at,
            "created_at": grant.created_at,
        }

    def _result_collect_handoff_reserve_summary(self) -> dict[str, Any]:
        return {
            "supported": True,
            "separate_result_share_token_required": True,
            "result_share_bootstrap_available": True,
            "collect_supported_via_self_service": True,
            "direct_collect_via_invite_page": False,
            "source_files_included": False,
            "supported_share_kinds": [
                ResultShareKind.DIGEST_ISSUE.value,
                ResultShareKind.PAPER_SNAPSHOT.value,
            ],
            "result_share_shell_entry_url": self.settings.result_share_web_entry_url,
            "notes": [
                "Joining the workspace does not automatically collect digest or paper shares.",
                (
                    "Collecting shared results requires a separate result-share token and the "
                    "existing self-service collect flow."
                ),
                "Source files and local attachments are not included.",
            ],
        }

    def _remaining_claims(self, grant: GroupWorkspaceInviteGrant) -> int | None:
        if grant.max_claims is None:
            return None
        return max(grant.max_claims - grant.claim_count, 0)

    def _workspace_member_summary(
        self,
        member: GroupWorkspaceMember,
        *,
        expose_email: bool,
    ) -> dict[str, Any]:
        return {
            "member_id": member.id,
            "user_id": member.user_id,
            "role": member.role,
            "name": member.user.name,
            "email": member.user.email if expose_email else None,
            "joined_at": member.joined_at,
        }

    def _latest_signal_summary(self, paper: PaperProfile) -> dict[str, Any] | None:
        if not paper.signal_snapshots:
            return None
        latest = max(
            paper.signal_snapshots,
            key=lambda snapshot: (
                self._coerce_utc(snapshot.fetched_at) or datetime.min.replace(tzinfo=UTC),
                str(snapshot.id),
            ),
        )
        return {
            "source": latest.source,
            "citation_count": latest.citation_count,
            "download_count": latest.download_count,
            "read_count": latest.read_count,
            "inclusion_status": latest.inclusion_status,
            "fetched_at": latest.fetched_at,
        }

    def _workspace_paper_snapshot(
        self,
        paper: PaperProfile,
        *,
        expose_owner_fields: bool,
    ) -> dict[str, Any]:
        return {
            "paper_id": paper.id,
            "user_id": paper.user_id,
            "owner_name": paper.user.name if expose_owner_fields else None,
            "owner_email": paper.user.email if expose_owner_fields else None,
            "title": paper.title,
            "type": paper.type,
            "stage": paper.stage,
            "venue": paper.venue,
            "priority": paper.priority,
            "next_action": paper.next_action,
            "blocker": paper.blocker,
            "last_touch_at": paper.last_touch_at,
            "progress_percentage": derive_progress_percentage(paper.type),
            "latest_signal_summary": self._latest_signal_summary(paper),
        }

    def _workspace_board_payload(
        self,
        workspace: GroupWorkspace,
        *,
        expose_admin_fields: bool,
    ) -> dict[str, Any]:
        members = sorted(
            workspace.members,
            key=lambda member: (
                WORKSPACE_MEMBER_ROLE_ORDER.get(member.role, len(WORKSPACE_MEMBER_ROLE_ORDER)),
                self._coerce_utc(member.joined_at) or datetime.min.replace(tzinfo=UTC),
                str(member.user_id),
            ),
        )
        papers = sorted(
            (entry.paper for entry in workspace.papers),
            key=lambda paper: (
                -paper.priority,
                -(
                    self._coerce_utc(paper.last_touch_at) or datetime.min.replace(tzinfo=UTC)
                ).timestamp(),
                paper.title.lower(),
                str(paper.id),
            ),
        )
        member_payloads = [
            self._workspace_member_summary(member, expose_email=expose_admin_fields)
            for member in members
        ]
        paper_payloads = [
            self._workspace_paper_snapshot(
                paper,
                expose_owner_fields=expose_admin_fields,
            )
            for paper in papers
        ]
        return {
            "workspace": self._workspace_summary(workspace),
            "member_count": len(member_payloads),
            "paper_count": len(paper_payloads),
            "members": member_payloads,
            "papers": paper_payloads,
            "quick_stats": {
                "member_count": len(member_payloads),
                "paper_count": len(paper_payloads),
                "blocked_paper_count": sum(1 for paper in paper_payloads if paper["blocker"]),
                "papers_with_signals_count": sum(
                    1 for paper in paper_payloads if paper["latest_signal_summary"] is not None
                ),
            },
        }

    def _share_target_summary(self, grant: ResultShareGrant) -> dict[str, Any]:
        title: str | None = grant.display_label
        if grant.share_kind == ResultShareKind.WORKSPACE_BOARD and grant.workspace is not None:
            title = title or grant.workspace.name
        elif grant.share_kind == ResultShareKind.DIGEST_ISSUE and grant.digest_issue is not None:
            title = title or grant.digest_issue.title
        elif grant.share_kind == ResultShareKind.PAPER_SNAPSHOT and grant.paper is not None:
            title = title or grant.paper.title
        return {
            "workspace_id": grant.workspace_id,
            "digest_issue_id": grant.digest_issue_id,
            "paper_id": grant.paper_id,
            "title": title,
        }

    def _share_collection_reserve_summary(self, grant: ResultShareGrant) -> dict[str, Any]:
        share_kind_collectable = (
            grant.share_kind in RESULT_COLLECTABLE_SHARE_KINDS
            and grant.share_kind
            in self.settings.group_workspace_result_collect_allowed_share_kind_list
        )
        supported = share_kind_collectable and self.settings.group_workspace_result_collect_enabled
        if share_kind_collectable and not self.settings.group_workspace_result_collect_enabled:
            notes = [
                "Structured paper collection is currently disabled.",
                "Source files and local attachments are not included.",
            ]
        elif share_kind_collectable:
            notes = [
                "Structured paper collection is available through a separate self-service grant.",
                "Source files and local attachments are not included.",
            ]
        else:
            notes = [
                "Workspace-board shares are not collectable in this phase.",
                "Source files and local attachments are not included.",
            ]
        return {
            "supported": supported,
            "share_kind_collectable": share_kind_collectable,
            "collect_supported_via_self_service": supported,
            "source_files_included": False,
            "notes": notes,
        }

    def _share_workspace_invite_handoff_summary(
        self,
        grant: ResultShareGrant,
        *,
        access_mode: ResultShareViewAccessMode | None = None,
        access_value: str | None = None,
    ) -> dict[str, Any] | None:
        if grant.share_kind != ResultShareKind.WORKSPACE_BOARD:
            return None
        handoff_redirect_supported = self._share_invite_handoff_redirect_supported(grant.share_kind)
        return {
            "supported": True,
            "share_kind": ResultShareKind.WORKSPACE_BOARD.value,
            "separate_invite_token_required": True,
            "invite_bootstrap_available": True,
            "self_service_claim_supported": True,
            "direct_claim_via_share_page": False,
            "handoff_redirect_supported": handoff_redirect_supported,
            "source_files_included": False,
            "invite_shell_entry_url": self.settings.group_workspace_invite_web_entry_url,
            "invite_handoff_url": self._build_share_invite_handoff_public_url(
                share_kind=grant.share_kind,
                access_mode=access_mode,
                access_value=access_value,
            ),
            "notes": [
                "This workspace-board share is read-only and cannot claim membership directly.",
                (
                    "Joining requires a separate invite token and the existing "
                    "self-service claim flow."
                ),
                "Source files and local attachments are not included.",
            ],
        }

    def _share_result_collect_handoff_summary(
        self,
        grant: ResultShareGrant,
        *,
        access_mode: ResultShareViewAccessMode | None = None,
        access_value: str | None = None,
    ) -> dict[str, Any] | None:
        if grant.share_kind != ResultShareKind.WORKSPACE_BOARD:
            return None
        handoff_redirect_supported = self._share_result_collect_handoff_redirect_supported(
            grant.share_kind
        )
        return {
            "supported": True,
            "share_kind": ResultShareKind.WORKSPACE_BOARD.value,
            "separate_result_share_token_required": True,
            "result_share_bootstrap_available": True,
            "collect_supported_via_self_service": True,
            "direct_collect_via_current_share": False,
            "handoff_redirect_supported": handoff_redirect_supported,
            "source_files_included": False,
            "supported_share_kinds": [
                ResultShareKind.DIGEST_ISSUE.value,
                ResultShareKind.PAPER_SNAPSHOT.value,
            ],
            "result_share_shell_entry_url": self.settings.result_share_web_entry_url,
            "collect_handoff_url": self._build_share_result_collect_handoff_public_url(
                share_kind=grant.share_kind,
                access_mode=access_mode,
                access_value=access_value,
            ),
            "notes": [
                "This workspace-board share is read-only and cannot collect papers directly.",
                (
                    "Collecting papers into the workspace requires a separate digest or "
                    "paper share token and the existing self-service collect flow."
                ),
                "Source files and local attachments are not included.",
            ],
        }

    def _result_collect_share_summary(self, grant: ResultShareGrant) -> dict[str, Any]:
        return {
            "id": grant.id,
            "share_kind": grant.share_kind,
            "status": grant.status,
            "display_label": grant.display_label,
            "expires_at": grant.expires_at,
            "target": self._share_target_summary(grant),
        }

    def _collected_paper_summary(self, paper: PaperProfile) -> dict[str, Any]:
        return {
            "paper_id": paper.id,
            "title": paper.title,
            "type": paper.type,
            "stage": paper.stage,
            "venue": paper.venue,
            "priority": paper.priority,
            "next_action": paper.next_action,
            "blocker": paper.blocker,
            "progress_percentage": derive_progress_percentage(paper.type),
        }

    def _collectable_paper_summary(
        self,
        paper: PaperProfile,
        *,
        source_card_type: str | None = None,
        source_pulse_card_id: UUID | None = None,
        source_section_kind: str | None = None,
        notes: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            **self._collected_paper_summary(paper),
            "source_card_type": source_card_type,
            "source_pulse_card_id": source_pulse_card_id,
            "source_section_kind": source_section_kind,
            "notes": None if notes is None else list(notes),
        }

    def _eligible_collect_workspaces(self, *, user_id: UUID) -> list[dict[str, Any]]:
        memberships = self.list_workspace_memberships_for_user(user_id=user_id)
        allowed_roles = set(self.settings.group_workspace_result_collect_allowed_role_list)
        eligible: list[dict[str, Any]] = []
        for membership in memberships:
            workspace = membership.workspace
            if workspace is None or workspace.status != GroupWorkspaceStatus.ACTIVE:
                continue
            if membership.role not in allowed_roles:
                continue
            eligible.append(
                {
                    "workspace": self._workspace_safe_summary(workspace),
                    "membership_role": membership.role,
                }
            )
        return eligible

    def _extract_collectable_items(
        self,
        grant: ResultShareGrant,
    ) -> tuple[list[dict[str, Any]], list[str], list[str]]:
        share_kind = grant.share_kind
        if share_kind not in self.settings.group_workspace_result_collect_allowed_share_kind_list:
            return [], ["share_kind_not_collectable"], []
        if share_kind == ResultShareKind.WORKSPACE_BOARD:
            return [], ["share_kind_not_collectable"], []
        if share_kind == ResultShareKind.PAPER_SNAPSHOT:
            if grant.paper is None:
                return [], ["no_collectable_papers"], []
            return (
                [self._collectable_paper_summary(grant.paper)],
                [],
                ["Collection adds structured paper records to a workspace without source files."],
            )
        if share_kind != ResultShareKind.DIGEST_ISSUE:
            return [], ["share_kind_not_collectable"], []
        if grant.digest_issue is None:
            return [], ["no_collectable_papers"], []
        payload = self._shared_digest_issue_payload(grant.digest_issue)
        sections = list(payload.get("sections") or [])
        stable_items: list[tuple[str | None, dict[str, Any]]] = []
        if sections:
            for section in sections:
                section_kind = str(section.get("kind") or "")
                for item in list(section.get("items") or []):
                    stable_items.append((section_kind, item))
        else:
            for item in list(payload.get("items") or []):
                stable_items.append((None, item))
        collectable_items: list[dict[str, Any]] = []
        seen_paper_ids: set[UUID] = set()
        for section_kind, item in stable_items:
            paper_id = item.get("source_paper_id")
            if paper_id is None:
                continue
            paper = item.get("paper")
            if not isinstance(paper, dict):
                continue
            try:
                paper_uuid = UUID(str(paper_id))
            except ValueError:
                continue
            if paper_uuid in seen_paper_ids:
                continue
            seen_paper_ids.add(paper_uuid)
            resolved_paper = self.paper_repository.get(paper_uuid)
            if resolved_paper is None:
                continue
            collectable_items.append(
                self._collectable_paper_summary(
                    resolved_paper,
                    source_card_type=item.get("card_type"),
                    source_pulse_card_id=(
                        None
                        if item.get("pulse_card_id") is None
                        else UUID(str(item["pulse_card_id"]))
                    ),
                    source_section_kind=section_kind,
                    notes=[],
                )
            )
            if (
                len(collectable_items)
                >= self.settings.group_workspace_result_collect_max_papers_per_digest
            ):
                break
        reason_codes = [] if collectable_items else ["no_collectable_papers"]
        notes = [
            (
                "Digest collection dedupes papers by source_paper_id and preserves "
                "stable first-seen order."
            )
        ]
        return collectable_items, reason_codes, notes

    def _evaluate_collect_preview(
        self,
        *,
        raw_token: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        share_grant = self.repository.get_result_share_grant_by_token_hash(hash_token(raw_token))
        if share_grant is None:
            return {
                "share_grant": None,
                "collectable_items": [],
                "eligible_workspaces": [],
                "reason_codes": ["share_not_found"],
                "notes": [],
                "can_collect": False,
            }
        now = self.now_provider()
        self._mark_expired_if_needed(share_grant, now=now)
        share_grant.last_used_at = now
        commit_session(self.session)
        return self._evaluate_collect_preview_for_share_grant(
            share_grant=share_grant,
            user_id=user_id,
        )

    def _evaluate_collect_preview_by_alias(
        self,
        *,
        raw_alias: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        try:
            alias_context = self.authenticate_share_alias(raw_alias)
        except AuthenticationError as exc:
            detail = str(exc).lower()
            if "revoked" in detail:
                reason_code = "share_revoked"
            elif "expired" in detail:
                reason_code = "share_expired"
            else:
                reason_code = "share_not_found"
            return {
                "share_grant": None,
                "collectable_items": [],
                "eligible_workspaces": [],
                "reason_codes": [reason_code],
                "notes": [],
                "can_collect": False,
            }
        share_grant = self.get_result_share_grant(alias_context.grant_id)
        return self._evaluate_collect_preview_for_share_grant(
            share_grant=share_grant,
            user_id=user_id,
        )

    def _evaluate_collect_preview_for_share_grant(
        self,
        *,
        share_grant: ResultShareGrant,
        user_id: UUID,
    ) -> dict[str, Any]:
        reason_codes: list[str] = []
        if not self.settings.group_workspace_result_collect_enabled:
            reason_codes.append("collect_disabled")
        if share_grant.status == ResultShareGrantStatus.REVOKED:
            reason_codes.append("share_revoked")
        elif share_grant.status == ResultShareGrantStatus.EXPIRED:
            reason_codes.append("share_expired")
        collectable_items, extract_reasons, notes = self._extract_collectable_items(share_grant)
        reason_codes.extend(extract_reasons)
        eligible_workspaces = self._eligible_collect_workspaces(user_id=user_id)
        if not eligible_workspaces:
            reason_codes.append("no_eligible_workspace_membership")
        reason_codes = self._dedupe_reason_codes(reason_codes)
        return {
            "share_grant": share_grant,
            "collectable_items": collectable_items,
            "eligible_workspaces": eligible_workspaces,
            "reason_codes": reason_codes,
            "notes": notes,
            "can_collect": not reason_codes,
        }

    def _select_collectable_items(
        self,
        *,
        share_kind: ResultShareKind,
        collectable_items: Sequence[dict[str, Any]],
        paper_ids: Sequence[UUID] | None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if not collectable_items:
            return [], ["no_collectable_papers"]
        item_ids = [UUID(str(item["paper_id"])) for item in collectable_items]
        if share_kind == ResultShareKind.PAPER_SNAPSHOT:
            target_id = item_ids[0]
            if not paper_ids:
                return [collectable_items[0]], []
            requested = {UUID(str(paper_id)) for paper_id in paper_ids}
            if requested == {target_id}:
                return [collectable_items[0]], []
            return [], ["paper_not_collectable"]
        if share_kind == ResultShareKind.DIGEST_ISSUE:
            if not paper_ids:
                if len(collectable_items) == 1:
                    return [collectable_items[0]], []
                return [], ["paper_selection_required"]
            requested = {UUID(str(paper_id)) for paper_id in paper_ids}
            valid = set(item_ids)
            if not requested.issubset(valid):
                return [], ["paper_not_collectable"]
            selected = [
                item for item in collectable_items if UUID(str(item["paper_id"])) in requested
            ]
            return selected, []
        return [], ["share_kind_not_collectable"]

    def _collect_single_result_item(
        self,
        *,
        share_grant: ResultShareGrant,
        workspace: GroupWorkspace,
        user_id: UUID,
        item: dict[str, Any],
    ) -> tuple[GroupWorkspaceResultCollectStatus, GroupWorkspaceResultCollectRecord | None]:
        paper_id = UUID(str(item["paper_id"]))
        idempotency_key = self._build_result_collect_idempotency_key(
            workspace_id=workspace.id,
            user_id=user_id,
            share_grant=share_grant,
            item=item,
        )
        existing_record = self.repository.get_result_collect_record_by_idempotency_key(
            idempotency_key
        )
        workspace_paper = self.repository.get_workspace_paper(
            workspace_id=workspace.id,
            paper_id=paper_id,
        )
        if workspace_paper is not None:
            if existing_record is None:
                existing_record = GroupWorkspaceResultCollectRecord(
                    workspace_id=workspace.id,
                    user_id=user_id,
                    result_share_grant_id=share_grant.id,
                    share_kind=share_grant.share_kind,
                    digest_issue_id=share_grant.digest_issue_id,
                    source_pulse_card_id=item.get("source_pulse_card_id"),
                    source_paper_id=paper_id,
                    collected_paper_id=paper_id,
                    idempotency_key=idempotency_key,
                    status=GroupWorkspaceResultCollectStatus.ALREADY_PRESENT,
                    reason_codes=["already_present"],
                )
                self.repository.add_result_collect_record(existing_record)
                self.session.flush()
                self.metrics.increment("group_workspace_result_collect_records_created_total")
            return GroupWorkspaceResultCollectStatus.ALREADY_PRESENT, existing_record

        collected_paper = self._require_paper(paper_id)
        self.repository.add_workspace_paper(
            GroupWorkspacePaper(
                workspace_id=workspace.id,
                paper_id=collected_paper.id,
                added_by_admin_id=None,
            )
        )
        if existing_record is None:
            existing_record = GroupWorkspaceResultCollectRecord(
                workspace_id=workspace.id,
                user_id=user_id,
                result_share_grant_id=share_grant.id,
                share_kind=share_grant.share_kind,
                digest_issue_id=share_grant.digest_issue_id,
                source_pulse_card_id=item.get("source_pulse_card_id"),
                source_paper_id=paper_id,
                collected_paper_id=paper_id,
                idempotency_key=idempotency_key,
                status=GroupWorkspaceResultCollectStatus.COLLECTED,
                reason_codes=[],
            )
            self.repository.add_result_collect_record(existing_record)
            self.session.flush()
            self.metrics.increment("group_workspace_result_collect_records_created_total")
        else:
            existing_record.status = GroupWorkspaceResultCollectStatus.COLLECTED
            existing_record.reason_codes = []
        return GroupWorkspaceResultCollectStatus.COLLECTED, existing_record

    def _build_result_collect_idempotency_key(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        share_grant: ResultShareGrant,
        item: dict[str, Any],
    ) -> str:
        raw_value = ":".join(
            [
                str(workspace_id),
                str(user_id),
                str(share_grant.id),
                share_grant.share_kind.value,
                "" if share_grant.digest_issue_id is None else str(share_grant.digest_issue_id),
                ""
                if item.get("source_pulse_card_id") is None
                else str(item["source_pulse_card_id"]),
                str(item["paper_id"]),
            ]
        )
        return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()

    def _dedupe_reason_codes(self, values: Sequence[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _require_paper(self, paper_id: UUID) -> PaperProfile:
        paper = self.paper_repository.get(paper_id)
        if paper is None:
            raise NotFoundError(f"paper {paper_id} was not found")
        return paper

    def _shared_workspace_board_payload(self, workspace: GroupWorkspace) -> dict[str, Any]:
        return {
            "share_kind": ResultShareKind.WORKSPACE_BOARD.value,
            **self._workspace_board_payload(workspace, expose_admin_fields=False),
        }

    def _shared_paper_snapshot_payload(self, paper: PaperProfile) -> dict[str, Any]:
        return {
            "share_kind": ResultShareKind.PAPER_SNAPSHOT.value,
            **self._workspace_paper_snapshot(paper, expose_owner_fields=False),
        }

    def _shared_digest_issue_payload(self, issue: PulseDigestIssue) -> dict[str, Any]:
        content_payload = dict(issue.content_payload or {})
        raw_items = list(content_payload.get("items") or [])
        items = self._normalize_digest_items(
            raw_items if raw_items else self._digest_items_from_issue(issue),
            issue=issue,
        )
        structured_sections = list(content_payload.get("sections") or [])
        is_structured = bool(structured_sections)
        sections = (
            self._normalize_sections(structured_sections, issue=issue)
            if is_structured
            else self._build_fallback_sections(items)
        )
        highlights = self._normalize_digest_items(
            list(content_payload.get("highlights") or []),
            issue=issue,
        )
        if not highlights:
            highlights = items[: min(issue.highlight_count, len(items))]
        return {
            "share_kind": ResultShareKind.DIGEST_ISSUE.value,
            "id": issue.id,
            "issue_date": issue.issue_date,
            "status": issue.status,
            "title": issue.title,
            "summary": issue.summary,
            "highlight_count": issue.highlight_count,
            "selected_card_count": issue.selected_card_count,
            "deep_link_path": issue.deep_link_path,
            "highlights": highlights,
            "is_structured": is_structured,
            "fallback_mode": "structured" if is_structured else "highlights_only",
            "section_order": self._normalize_section_order(
                content_payload.get("section_order"),
                is_structured=is_structured,
            ),
            "sections": sections,
            "quick_stats": (
                self._normalize_quick_stats(content_payload.get("quick_stats"))
                if is_structured
                else self._build_quick_stats(items)
            ),
            "focus_card": (
                self._normalize_digest_item(content_payload.get("focus_card"), issue=issue)
                if is_structured
                else self._derive_focus_card_from_sections(sections)
            ),
            "publication_preview": self._normalize_publication_preview(
                content_payload.get("publication_preview"),
                issue=issue,
            ),
            "items": items,
        }

    def _digest_items_from_issue(self, issue: PulseDigestIssue) -> list[dict[str, Any]]:
        return [
            {
                "sort_order": item.sort_order,
                "pulse_card_id": item.pulse_card_id,
                "card_type": item.card_type.value,
                "source_paper_id": item.source_paper_id,
                "title": item.title,
                "summary": item.summary,
                "why_now": item.why_now,
                "action_text": None,
                "deep_link": None,
                "paper": (
                    None
                    if item.source_paper is None
                    else self._workspace_paper_snapshot(
                        item.source_paper,
                        expose_owner_fields=False,
                    )
                ),
            }
            for item in issue.items
        ]

    def _normalize_digest_item(
        self,
        raw_item: dict[str, Any] | None,
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_item, dict):
            return None
        paper = raw_item.get("paper")
        if not isinstance(paper, dict):
            paper = self._resolve_paper_snapshot_for_digest_item(raw_item, issue=issue)
        return {
            "sort_order": int(raw_item.get("sort_order", 0)),
            "pulse_card_id": raw_item.get("pulse_card_id"),
            "card_type": str(raw_item.get("card_type", "")),
            "source_paper_id": raw_item.get("source_paper_id"),
            "title": str(raw_item.get("title", "")),
            "summary": str(raw_item.get("summary", "")),
            "why_now": raw_item.get("why_now"),
            "action_text": raw_item.get("action_text"),
            "deep_link": raw_item.get("deep_link"),
            "paper": paper,
        }

    def _normalize_digest_items(
        self,
        raw_items: Sequence[dict[str, Any]],
        *,
        issue: PulseDigestIssue,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for raw_item in raw_items:
            normalized = self._normalize_digest_item(raw_item, issue=issue)
            if normalized is not None:
                items.append(normalized)
        return sorted(
            items,
            key=lambda item: (
                int(item.get("sort_order", 0)),
                str(item.get("pulse_card_id", "")),
            ),
        )

    def _normalize_sections(
        self,
        raw_sections: Sequence[dict[str, Any]],
        *,
        issue: PulseDigestIssue,
    ) -> list[dict[str, Any]]:
        normalized_sections: list[dict[str, Any]] = []
        for raw_section in raw_sections:
            if not isinstance(raw_section, dict):
                continue
            kind = str(raw_section.get("kind") or "other_updates")
            items = self._normalize_digest_items(list(raw_section.get("items") or []), issue=issue)
            if not items:
                continue
            normalized_sections.append(
                {
                    "kind": kind,
                    "title": str(raw_section.get("title") or self._section_title(kind)),
                    "item_count": int(raw_section.get("item_count") or len(items)),
                    "items": items,
                }
            )
        return self._order_sections(normalized_sections)

    def _normalize_section_order(
        self,
        raw_section_order: Sequence[str] | None,
        *,
        is_structured: bool,
    ) -> list[str]:
        if not is_structured:
            return list(SHARED_SECTION_ORDER)
        ordered: list[str] = []
        for kind in list(raw_section_order or []):
            kind_str = str(kind)
            if kind_str not in ordered:
                ordered.append(kind_str)
        for kind in SHARED_SECTION_ORDER:
            if kind not in ordered:
                ordered.append(kind)
        return ordered

    def _normalize_quick_stats(
        self,
        raw_quick_stats: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_quick_stats, dict):
            return None
        return {
            "selected_card_count": int(raw_quick_stats.get("selected_card_count") or 0),
            "related_paper_count": int(raw_quick_stats.get("related_paper_count") or 0),
            "signal_update_count": int(raw_quick_stats.get("signal_update_count") or 0),
            "touched_paper_count": int(raw_quick_stats.get("touched_paper_count") or 0),
        }

    def _normalize_publication_preview(
        self,
        raw_preview: dict[str, Any] | None,
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        if not isinstance(raw_preview, dict):
            return None
        return {
            "digest_title": raw_preview.get("digest_title"),
            "digest_subtitle": raw_preview.get("digest_subtitle"),
            "digest_highlights": self._normalize_digest_items(
                list(raw_preview.get("digest_highlights") or []),
                issue=issue,
            ),
            "primary_cta_text": raw_preview.get("primary_cta_text"),
            "primary_cta_path": raw_preview.get("primary_cta_path"),
            "mini_program_path": raw_preview.get("mini_program_path"),
            "article_url": raw_preview.get("article_url"),
        }

    def _build_fallback_sections(self, items: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = {kind: [] for kind in SHARED_SECTION_ORDER}
        for item in items:
            buckets[self._fallback_section_kind(str(item.get("card_type") or ""))].append(item)
        sections: list[dict[str, Any]] = []
        for kind in SHARED_SECTION_ORDER:
            bucket = buckets[kind]
            if not bucket:
                continue
            sections.append(
                {
                    "kind": kind,
                    "title": self._section_title(kind),
                    "item_count": len(bucket),
                    "items": list(bucket),
                }
            )
        return sections

    def _build_quick_stats(self, items: Sequence[dict[str, Any]]) -> dict[str, Any]:
        touched_paper_ids = {
            str(item["source_paper_id"])
            for item in items
            if item.get("source_paper_id") is not None
        }
        return {
            "selected_card_count": len(items),
            "related_paper_count": sum(
                1 for item in items if item.get("card_type") == PulseCardType.RELATED_PAPER.value
            ),
            "signal_update_count": sum(
                1 for item in items if item.get("card_type") == PulseCardType.SIGNAL_CHANGE.value
            ),
            "touched_paper_count": len(touched_paper_ids),
        }

    def _derive_focus_card_from_sections(
        self,
        sections: Sequence[dict[str, Any]],
    ) -> dict[str, Any] | None:
        for section in sections:
            items = list(section.get("items") or [])
            if items:
                return items[0]
        return None

    def _fallback_section_kind(self, card_type: str) -> str:
        if card_type in {
            PulseCardType.TODAY_SUGGESTION.value,
            PulseCardType.NEXT_ACTION.value,
            PulseCardType.STALLED_PROGRESS.value,
            PulseCardType.DEADLINE_RISK.value,
        }:
            return "today_focus"
        if card_type == PulseCardType.YESTERDAY_SUMMARY.value:
            return "yesterday_recap"
        if card_type == PulseCardType.SIGNAL_CHANGE.value:
            return "signal_updates"
        if card_type == PulseCardType.RELATED_PAPER.value:
            return "related_papers"
        return "other_updates"

    def _section_title(self, kind: str) -> str:
        return SHARED_SECTION_TITLE_BY_KIND.get(kind, kind.replace("_", " ").title())

    def _order_sections(self, sections: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        order_index = {kind: index for index, kind in enumerate(SHARED_SECTION_ORDER)}
        return sorted(
            sections,
            key=lambda section: (
                order_index.get(str(section.get("kind")), len(order_index)),
                str(section.get("title", "")),
                str(section.get("kind", "")),
            ),
        )

    def _resolve_paper_snapshot_for_digest_item(
        self,
        raw_item: dict[str, Any],
        *,
        issue: PulseDigestIssue,
    ) -> dict[str, Any] | None:
        pulse_card_id = raw_item.get("pulse_card_id")
        source_paper_id = raw_item.get("source_paper_id")
        for item in issue.items:
            if pulse_card_id is not None and str(item.pulse_card_id) == str(pulse_card_id):
                return (
                    None
                    if item.source_paper is None
                    else self._workspace_paper_snapshot(
                        item.source_paper,
                        expose_owner_fields=False,
                    )
                )
            if source_paper_id is not None and str(item.source_paper_id) == str(source_paper_id):
                return (
                    None
                    if item.source_paper is None
                    else self._workspace_paper_snapshot(
                        item.source_paper,
                        expose_owner_fields=False,
                    )
                )
        return None

    def _coerce_utc(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
