"""Operational routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from research_pulse_cn.api.dependencies import get_ops_service
from research_pulse_cn.domain.enums import (
    DeliveryJobStatus,
    PulseJobScheduledReason,
    PulseJobStatus,
    WorkerRole,
    WorkerStatus,
)
from research_pulse_cn.schemas.delivery import DeliveryJobRead
from research_pulse_cn.schemas.ops import (
    DeliveryAttemptRead,
    OpsPulseJobRead,
    ReplayResponse,
    RequeueResponse,
    SchedulerTickItem,
    SchedulerTickResponse,
    WorkerHeartbeatRead,
)
from research_pulse_cn.services.ops import OpsService

router = APIRouter(prefix="/ops", tags=["ops"])
OpsServiceDep = Annotated[OpsService, Depends(get_ops_service)]
UserIdQuery = Annotated[UUID | None, Query()]
SinceHoursQuery = Annotated[int | None, Query(ge=1, le=24 * 30)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(service: OpsServiceDep) -> PlainTextResponse:
    return PlainTextResponse(
        service.metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/heartbeats", response_model=list[WorkerHeartbeatRead])
def list_heartbeats(
    service: OpsServiceDep,
    worker_role: Annotated[WorkerRole | None, Query()] = None,
    status: Annotated[WorkerStatus | None, Query()] = None,
    since_hours: SinceHoursQuery = None,
    limit: LimitQuery = 100,
) -> list[WorkerHeartbeatRead]:
    return service.list_heartbeats(
        worker_role=worker_role,
        status=status,
        since_hours=since_hours,
        limit=limit,
    )


@router.get("/pulse-jobs", response_model=list[OpsPulseJobRead])
def list_pulse_jobs(
    service: OpsServiceDep,
    user_id: UserIdQuery = None,
    status: Annotated[PulseJobStatus | None, Query()] = None,
    scheduled_reason: Annotated[PulseJobScheduledReason | None, Query()] = None,
    since_hours: SinceHoursQuery = None,
    limit: LimitQuery = 100,
) -> list[OpsPulseJobRead]:
    return service.list_pulse_jobs(
        user_id=user_id,
        status=status,
        scheduled_reason=scheduled_reason,
        since_hours=since_hours,
        limit=limit,
    )


@router.get("/delivery-jobs", response_model=list[DeliveryJobRead])
def list_delivery_jobs(
    service: OpsServiceDep,
    user_id: UserIdQuery = None,
    status: Annotated[DeliveryJobStatus | None, Query()] = None,
    since_hours: SinceHoursQuery = None,
    limit: LimitQuery = 100,
) -> list[DeliveryJobRead]:
    return service.list_delivery_jobs(
        user_id=user_id,
        status=status,
        since_hours=since_hours,
        limit=limit,
    )


@router.get("/delivery-attempts", response_model=list[DeliveryAttemptRead])
def list_delivery_attempts(
    service: OpsServiceDep,
    delivery_job_id: Annotated[UUID | None, Query()] = None,
    since_hours: SinceHoursQuery = None,
    limit: LimitQuery = 100,
) -> list[DeliveryAttemptRead]:
    return service.list_delivery_attempts(
        delivery_job_id=delivery_job_id,
        since_hours=since_hours,
        limit=limit,
    )


@router.post("/scheduler/tick", response_model=SchedulerTickResponse)
def scheduler_tick(service: OpsServiceDep) -> SchedulerTickResponse:
    payload = service.scheduler_tick()
    payload["created_jobs"] = [
        SchedulerTickItem(
            pulse_job_id=job.id,
            user_id=job.user_id,
            subscription_policy_id=job.subscription_policy_id,
            schedule_key=job.schedule_key or "",
            scheduled_for=job.scheduled_for,
        )
        for job in payload["created_jobs"]
    ]
    return SchedulerTickResponse(**payload)


@router.post("/delivery-jobs/{delivery_job_id}/requeue", response_model=RequeueResponse)
def requeue_delivery_job(delivery_job_id: UUID, service: OpsServiceDep) -> RequeueResponse:
    action, job = service.requeue_delivery_job(delivery_job_id)
    return RequeueResponse(action=action, delivery_job_id=job.id, status=job.status.value)


@router.post("/pulse-jobs/{pulse_job_id}/replay", response_model=ReplayResponse)
def replay_pulse_job(pulse_job_id: UUID, service: OpsServiceDep) -> ReplayResponse:
    action, job = service.replay_pulse_job(pulse_job_id)
    return ReplayResponse(action=action, pulse_job=job)
