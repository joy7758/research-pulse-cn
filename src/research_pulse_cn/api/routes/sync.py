"""Device-token protected sync routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from research_pulse_cn.api.dependencies import get_sync_service
from research_pulse_cn.api.sync_security import get_current_device
from research_pulse_cn.core.request_context import bind_log_context
from research_pulse_cn.domain.sync import DeviceContext
from research_pulse_cn.schemas.sync import (
    ClientDeviceRead,
    SyncAckRequest,
    SyncAckResponse,
    SyncEventRead,
    SyncFeedResponse,
    SyncMeResponse,
    SyncMutationResultRead,
    SyncPushRequest,
    SyncPushResponse,
    SyncUserSummary,
)
from research_pulse_cn.services.sync import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])
SyncServiceDep = Annotated[SyncService, Depends(get_sync_service)]
DeviceDep = Annotated[DeviceContext, Depends(get_current_device)]
AfterSequenceQuery = Annotated[int | None, Query(ge=0)]
LimitQuery = Annotated[int | None, Query(ge=1)]


@router.get("/me", response_model=SyncMeResponse)
def sync_me(device: DeviceDep, service: SyncServiceDep) -> SyncMeResponse:
    with bind_log_context(client_device_id=device.client_device_id, user_id=device.user_id):
        payload = service.get_sync_me(device)
    return SyncMeResponse(
        device=ClientDeviceRead(**payload["device"]),
        user=SyncUserSummary(**payload["user"]),
    )


@router.get("/feed", response_model=SyncFeedResponse)
def sync_feed(
    device: DeviceDep,
    service: SyncServiceDep,
    after_sequence: AfterSequenceQuery = None,
    limit: LimitQuery = None,
) -> SyncFeedResponse:
    payload = service.feed(
        device,
        after_sequence=after_sequence,
        limit=limit,
    )
    return SyncFeedResponse(
        events=[SyncEventRead.model_validate(event) for event in payload["events"]],
        next_after_sequence=payload["next_after_sequence"],
        has_more=payload["has_more"],
    )


@router.post("/ack", response_model=SyncAckResponse)
def sync_ack(
    payload: SyncAckRequest,
    device: DeviceDep,
    service: SyncServiceDep,
) -> SyncAckResponse:
    with bind_log_context(client_device_id=device.client_device_id, user_id=device.user_id):
        cursor = service.ack(device, last_event_sequence=payload.last_event_sequence)
    return SyncAckResponse(
        last_event_sequence=cursor.last_event_sequence,
        last_synced_at=cursor.last_synced_at,
    )


@router.post("/push", response_model=SyncPushResponse)
def sync_push(
    payload: SyncPushRequest,
    device: DeviceDep,
    service: SyncServiceDep,
) -> SyncPushResponse:
    results = service.push(
        device,
        mutations=[item.model_dump() for item in payload.mutations],
    )
    return SyncPushResponse(
        results=[SyncMutationResultRead(**item) for item in results],
    )
