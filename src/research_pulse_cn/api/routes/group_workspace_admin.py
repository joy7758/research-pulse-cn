"""Admin routes for group workspaces and result share grants."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_group_workspace_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
    GroupWorkspaceResultCollectStatus,
    GroupWorkspaceStatus,
    ResultShareAliasStatus,
    ResultShareGrantStatus,
    ResultShareKind,
)
from research_pulse_cn.schemas.group_workspace import (
    GroupWorkspaceBoardRead,
    GroupWorkspaceCreateRequest,
    GroupWorkspaceMemberCreateRequest,
    GroupWorkspaceMemberRead,
    GroupWorkspacePaperCreateRequest,
    GroupWorkspacePaperRead,
    GroupWorkspaceRead,
    GroupWorkspaceResultCollectionRead,
    GroupWorkspaceUpdateRequest,
    ResultShareAliasCreateRequest,
    ResultShareAliasIssueResponse,
    ResultShareAliasRead,
    ResultShareAliasRevokeResponse,
    ResultShareGrantCreateRequest,
    ResultShareGrantIssueResponse,
    ResultShareGrantRead,
    ResultShareGrantRevokeResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.group_workspace import GroupWorkspaceService

router = APIRouter(prefix="/admin", tags=["admin"])
WorkspaceServiceDep = Annotated[GroupWorkspaceService, Depends(get_group_workspace_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
ViewerDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.VIEWER))]


@router.get("/group-workspaces", response_model=list[GroupWorkspaceRead])
def list_group_workspaces(
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
    status_value: Annotated[GroupWorkspaceStatus | None, Query(alias="status")] = None,
    user_id: Annotated[UUID | None, Query()] = None,
) -> list[GroupWorkspaceRead]:
    return [
        GroupWorkspaceRead(**service._workspace_summary(workspace))
        for workspace in service.list_workspaces(status=status_value, user_id=user_id)
    ]


@router.post(
    "/group-workspaces",
    response_model=GroupWorkspaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_group_workspace(
    payload: GroupWorkspaceCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceRead:
    workspace = service.create_workspace(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        created_by_admin_id=actor.actor_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace.create",
        resource_type="group_workspace",
        resource_id=str(workspace.id),
        status_code=201,
        metadata={"slug": workspace.slug},
    )
    return GroupWorkspaceRead(**service._workspace_summary(workspace))


@router.get("/group-workspaces/{workspace_id}", response_model=GroupWorkspaceRead)
def get_group_workspace(
    workspace_id: UUID,
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
) -> GroupWorkspaceRead:
    return GroupWorkspaceRead(**service._workspace_summary(service.get_workspace(workspace_id)))


@router.patch("/group-workspaces/{workspace_id}", response_model=GroupWorkspaceRead)
def update_group_workspace(
    workspace_id: UUID,
    payload: GroupWorkspaceUpdateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceRead:
    workspace = service.update_workspace(
        workspace_id,
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        status=payload.status,
        update_fields=set(payload.model_fields_set),
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace.update",
        resource_type="group_workspace",
        resource_id=str(workspace.id),
        status_code=200,
    )
    return GroupWorkspaceRead(**service._workspace_summary(workspace))


@router.post(
    "/group-workspaces/{workspace_id}/members",
    response_model=GroupWorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def add_group_workspace_member(
    workspace_id: UUID,
    payload: GroupWorkspaceMemberCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspaceMemberRead:
    member = service.add_member(
        workspace_id=workspace_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_member.create",
        resource_type="group_workspace_member",
        resource_id=str(member.id),
        status_code=201,
        metadata={
            "workspace_id": str(workspace_id),
            "user_id": str(member.user_id),
            "role": member.role.value,
        },
    )
    return GroupWorkspaceMemberRead.model_validate(member)


@router.delete(
    "/group-workspaces/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_group_workspace_member(
    workspace_id: UUID,
    member_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.remove_member(workspace_id=workspace_id, member_id=member_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_member.delete",
        resource_type="group_workspace_member",
        resource_id=str(member_id),
        status_code=204,
        metadata={"workspace_id": str(workspace_id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/group-workspaces/{workspace_id}/papers",
    response_model=GroupWorkspacePaperRead,
    status_code=status.HTTP_201_CREATED,
)
def add_group_workspace_paper(
    workspace_id: UUID,
    payload: GroupWorkspacePaperCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> GroupWorkspacePaperRead:
    workspace_paper = service.add_paper(
        workspace_id=workspace_id,
        paper_id=payload.paper_id,
        added_by_admin_id=actor.actor_id,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_paper.create",
        resource_type="group_workspace_paper",
        resource_id=str(workspace_paper.id),
        status_code=201,
        metadata={"workspace_id": str(workspace_id), "paper_id": str(workspace_paper.paper_id)},
    )
    return GroupWorkspacePaperRead.model_validate(workspace_paper)


@router.delete(
    "/group-workspaces/{workspace_id}/papers/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_group_workspace_paper(
    workspace_id: UUID,
    paper_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> Response:
    service.remove_paper(workspace_id=workspace_id, paper_id=paper_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="group_workspace_paper.delete",
        resource_type="group_workspace_paper",
        resource_id=str(paper_id),
        status_code=204,
        metadata={"workspace_id": str(workspace_id)},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/group-workspaces/{workspace_id}/board", response_model=GroupWorkspaceBoardRead)
def get_group_workspace_board(
    workspace_id: UUID,
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
) -> GroupWorkspaceBoardRead:
    return GroupWorkspaceBoardRead(
        **service.get_workspace_board(
            workspace_id,
            expose_admin_fields=True,
        )
    )


@router.get("/result-share-grants", response_model=list[ResultShareGrantRead])
def list_result_share_grants(
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
    workspace_id: Annotated[UUID | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    share_kind: Annotated[ResultShareKind | None, Query()] = None,
    status_value: Annotated[ResultShareGrantStatus | None, Query(alias="status")] = None,
) -> list[ResultShareGrantRead]:
    return [
        ResultShareGrantRead(**service.serialize_result_share_grant(grant))
        for grant in service.list_result_share_grants(
            workspace_id=workspace_id,
            user_id=user_id,
            share_kind=share_kind,
            status=status_value,
        )
    ]


@router.post(
    "/result-share-grants",
    response_model=ResultShareGrantIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_result_share_grant(
    payload: ResultShareGrantCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareGrantIssueResponse:
    grant, issued = service.create_result_share_grant(
        share_kind=payload.share_kind,
        workspace_id=payload.workspace_id,
        digest_issue_id=payload.digest_issue_id,
        paper_id=payload.paper_id,
        display_label=payload.display_label,
        issued_by_admin_id=actor.actor_id,
        expires_at=payload.expires_at,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="result_share_grant.create",
        resource_type="result_share_grant",
        resource_id=str(grant.id),
        status_code=201,
        metadata={
            "share_kind": grant.share_kind.value,
            "workspace_id": None if grant.workspace_id is None else str(grant.workspace_id),
            "digest_issue_id": (
                None if grant.digest_issue_id is None else str(grant.digest_issue_id)
            ),
            "paper_id": None if grant.paper_id is None else str(grant.paper_id),
        },
    )
    return ResultShareGrantIssueResponse(
        grant=ResultShareGrantRead(**service.serialize_result_share_grant(grant)),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
    )


@router.post(
    "/result-share-grants/{grant_id}/revoke",
    response_model=ResultShareGrantRevokeResponse,
)
def revoke_result_share_grant(
    grant_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareGrantRevokeResponse:
    grant = service.revoke_result_share_grant(grant_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="result_share_grant.revoke",
        resource_type="result_share_grant",
        resource_id=str(grant.id),
        status_code=200,
        metadata={"share_kind": grant.share_kind.value},
    )
    return ResultShareGrantRevokeResponse(
        grant=ResultShareGrantRead(**service.serialize_result_share_grant(grant)),
        revoked_at=grant.updated_at,
    )


@router.get("/result-share-aliases", response_model=list[ResultShareAliasRead])
def list_result_share_aliases(
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
    result_share_grant_id: Annotated[UUID | None, Query()] = None,
    share_kind: Annotated[ResultShareKind | None, Query()] = None,
    status_value: Annotated[ResultShareAliasStatus | None, Query(alias="status")] = None,
) -> list[ResultShareAliasRead]:
    return [
        ResultShareAliasRead(**service.serialize_result_share_alias(alias))
        for alias in service.list_result_share_aliases(
            result_share_grant_id=result_share_grant_id,
            share_kind=share_kind,
            status=status_value,
        )
    ]


@router.get("/result-share-aliases/{alias_id}", response_model=ResultShareAliasRead)
def get_result_share_alias(
    alias_id: UUID,
    _actor: OperatorDep,
    service: WorkspaceServiceDep,
) -> ResultShareAliasRead:
    return ResultShareAliasRead(
        **service.serialize_result_share_alias(service.get_result_share_alias(alias_id))
    )


@router.post(
    "/result-share-aliases",
    response_model=ResultShareAliasIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_result_share_alias(
    payload: ResultShareAliasCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareAliasIssueResponse:
    alias, issued = service.create_result_share_alias(
        result_share_grant_id=payload.result_share_grant_id,
        display_label=payload.display_label,
        issued_by_admin_id=actor.actor_id,
        expires_at=payload.expires_at,
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="result_share_alias.create",
        resource_type="result_share_alias",
        resource_id=str(alias.id),
        status_code=201,
        metadata={
            "result_share_grant_id": str(alias.result_share_grant_id),
            "share_kind": service.serialize_result_share_alias(alias)["share_kind"].value,
        },
    )
    return ResultShareAliasIssueResponse(
        alias=ResultShareAliasRead(**service.serialize_result_share_alias(alias)),
        plain_text_alias=issued.plain_text_alias,
        expires_at=issued.expires_at,
    )


@router.post(
    "/result-share-aliases/{alias_id}/revoke",
    response_model=ResultShareAliasRevokeResponse,
)
def revoke_result_share_alias(
    alias_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: WorkspaceServiceDep,
    audit_service: AuditServiceDep,
) -> ResultShareAliasRevokeResponse:
    alias = service.revoke_result_share_alias(alias_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="result_share_alias.revoke",
        resource_type="result_share_alias",
        resource_id=str(alias.id),
        status_code=200,
        metadata={
            "result_share_grant_id": str(alias.result_share_grant_id),
            "share_kind": service.serialize_result_share_alias(alias)["share_kind"].value,
        },
    )
    return ResultShareAliasRevokeResponse(
        alias=ResultShareAliasRead(**service.serialize_result_share_alias(alias)),
        revoked_at=alias.updated_at,
    )


@router.get(
    "/group-workspace-result-collect-records",
    response_model=list[GroupWorkspaceResultCollectionRead],
)
def list_group_workspace_result_collect_records(
    _actor: ViewerDep,
    service: WorkspaceServiceDep,
    workspace_id: Annotated[UUID | None, Query()] = None,
    user_id: Annotated[UUID | None, Query()] = None,
    result_share_grant_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[GroupWorkspaceResultCollectStatus | None, Query()] = None,
    collected_paper_id: Annotated[UUID | None, Query()] = None,
) -> list[GroupWorkspaceResultCollectionRead]:
    records = service.list_result_collect_records(
        workspace_id=workspace_id,
        user_id=user_id,
        result_share_grant_id=result_share_grant_id,
        status=status,
        collected_paper_id=collected_paper_id,
    )
    payloads: list[GroupWorkspaceResultCollectionRead] = []
    for record in records:
        if record.workspace is None or record.collected_paper is None:
            continue
        payloads.append(
            GroupWorkspaceResultCollectionRead(
                record=service.serialize_result_collect_record(record),
                workspace=service._workspace_safe_summary(record.workspace),
                paper=service._collected_paper_summary(record.collected_paper),
            )
        )
    return payloads
