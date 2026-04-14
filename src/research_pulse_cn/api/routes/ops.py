"""Operational routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse

from research_pulse_cn.api.audit import audit_request_action
from research_pulse_cn.api.dependencies import get_audit_service, get_ops_service
from research_pulse_cn.api.security import require_admin_or_service
from research_pulse_cn.domain.auth import ActorContext
from research_pulse_cn.domain.enums import (
    AdminRole,
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
from research_pulse_cn.services.audit import AuditService
from research_pulse_cn.services.ops import OpsService

router = APIRouter(prefix="/ops", tags=["ops"])
OpsServiceDep = Annotated[OpsService, Depends(get_ops_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
OperatorOrServiceDep = Annotated[
    ActorContext,
    Depends(require_admin_or_service(AdminRole.OPERATOR)),
]
UserIdQuery = Annotated[UUID | None, Query()]
SinceHoursQuery = Annotated[int | None, Query(ge=1, le=24 * 30)]
LimitQuery = Annotated[int, Query(ge=1, le=500)]


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(
    _actor: OperatorOrServiceDep,
    service: OpsServiceDep,
) -> PlainTextResponse:
    return PlainTextResponse(
        service.metrics_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/heartbeats", response_model=list[WorkerHeartbeatRead])
def list_heartbeats(
    _actor: OperatorOrServiceDep,
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
    _actor: OperatorOrServiceDep,
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
    _actor: OperatorOrServiceDep,
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
    _actor: OperatorOrServiceDep,
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
def scheduler_tick(
    request: Request,
    actor: OperatorOrServiceDep,
    service: OpsServiceDep,
    audit_service: AuditServiceDep,
) -> SchedulerTickResponse:
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
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="ops.scheduler.tick",
        resource_type="pulse_job",
        status_code=200,
        metadata={
            "jobs_created": payload["jobs_created"],
            "jobs_existing": payload["jobs_existing"],
        },
    )
    return SchedulerTickResponse(**payload)


@router.post("/delivery-jobs/{delivery_job_id}/requeue", response_model=RequeueResponse)
def requeue_delivery_job(
    delivery_job_id: UUID,
    request: Request,
    actor: OperatorOrServiceDep,
    service: OpsServiceDep,
    audit_service: AuditServiceDep,
) -> RequeueResponse:
    action, job = service.requeue_delivery_job(delivery_job_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="delivery_job.requeue",
        resource_type="delivery_job",
        resource_id=str(job.id),
        status_code=200,
        metadata={"action_result": action},
    )
    return RequeueResponse(action=action, delivery_job_id=job.id, status=job.status.value)


@router.post("/pulse-jobs/{pulse_job_id}/replay", response_model=ReplayResponse)
def replay_pulse_job(
    pulse_job_id: UUID,
    request: Request,
    actor: OperatorOrServiceDep,
    service: OpsServiceDep,
    audit_service: AuditServiceDep,
) -> ReplayResponse:
    action, job = service.replay_pulse_job(pulse_job_id)
    audit_request_action(
        audit_service=audit_service,
        request=request,
        actor=actor,
        action="pulse_job.replay",
        resource_type="pulse_job",
        resource_id=str(job.id),
        status_code=200,
        metadata={"action_result": action, "source_pulse_job_id": str(pulse_job_id)},
    )
    return ReplayResponse(action=action, pulse_job=job)
