"""Admin-managed sync device routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_sync_service
from research_pulse_cn.api.security import require_admin_role
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import AdminRole, ClientType
from research_pulse_cn.schemas.sync import (
    ClientDeviceCreateRequest,
    ClientDeviceRead,
    ClientDeviceRevokeResponse,
    ClientDeviceTokenIssueResponse,
)
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.sync import SyncService

router = APIRouter(prefix="/admin", tags=["admin"])
SyncServiceDep = Annotated[SyncService, Depends(get_sync_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorDep = Annotated[ActorContext, Depends(require_admin_role(AdminRole.OPERATOR))]
UserIdQuery = Annotated[UUID | None, Query()]
ClientTypeQuery = Annotated[ClientType | None, Query()]
IsActiveQuery = Annotated[bool | None, Query()]


@router.get("/client-devices", response_model=list[ClientDeviceRead])
def list_client_devices(
    _actor: OperatorDep,
    service: SyncServiceDep,
    user_id: UserIdQuery = None,
    client_type: ClientTypeQuery = None,
    is_active: IsActiveQuery = None,
) -> list[ClientDeviceRead]:
    return [
        _to_device_read(device)
        for device in service.list_devices(
            user_id=user_id,
            client_type=client_type,
            is_active=is_active,
        )
    ]


@router.post(
    "/client-devices",
    response_model=ClientDeviceTokenIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_client_device(
    payload: ClientDeviceCreateRequest,
    request: Request,
    actor: OperatorDep,
    service: SyncServiceDep,
    audit_service: AuditServiceDep,
) -> ClientDeviceTokenIssueResponse:
    device, issued = service.create_device(
        user_id=payload.user_id,
        client_type=payload.client_type,
        display_name=payload.display_name,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="client_device.create",
        resource_type="client_device",
        resource_id=str(device.id),
        status_code=201,
        metadata={"user_id": str(device.user_id), "client_type": device.client_type.value},
    )
    return ClientDeviceTokenIssueResponse(
        device=_to_device_read(device),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
    )


@router.post(
    "/client-devices/{client_device_id}/rotate-token",
    response_model=ClientDeviceTokenIssueResponse,
)
def rotate_client_device_token(
    client_device_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: SyncServiceDep,
    audit_service: AuditServiceDep,
) -> ClientDeviceTokenIssueResponse:
    device, issued = service.rotate_device_token(
        client_device_id,
        created_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="client_device.rotate_token",
        resource_type="client_device",
        resource_id=str(device.id),
        status_code=200,
    )
    return ClientDeviceTokenIssueResponse(
        device=_to_device_read(device),
        plain_text_token=issued.plain_text_token,
        expires_at=issued.expires_at,
    )


@router.post("/client-devices/{client_device_id}/revoke", response_model=ClientDeviceRevokeResponse)
def revoke_client_device(
    client_device_id: UUID,
    request: Request,
    actor: OperatorDep,
    service: SyncServiceDep,
    audit_service: AuditServiceDep,
) -> ClientDeviceRevokeResponse:
    device = service.revoke_device(client_device_id)
    revoked_at = device.updated_at
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="client_device.revoke",
        resource_type="client_device",
        resource_id=str(device.id),
        status_code=200,
    )
    return ClientDeviceRevokeResponse(device=_to_device_read(device), revoked_at=revoked_at)


def _to_device_read(device) -> ClientDeviceRead:
    cursor = device.cursor
    return ClientDeviceRead(
        id=device.id,
        user_id=device.user_id,
        client_type=device.client_type,
        display_name=device.display_name,
        is_active=device.is_active,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
        last_event_sequence=0 if cursor is None else cursor.last_event_sequence,
        last_synced_at=None if cursor is None else cursor.last_synced_at,
    )
