"""Operational schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from research_pulse_cn.domain.enums import (
    ChannelType,
    DeliveryAttemptStatus,
    PulseJobScheduledReason,
    PulseJobStatus,
    WorkerRole,
    WorkerStatus,
)
from research_pulse_cn.schemas.common import ORMModel


class ComponentStatusRead(BaseModel):
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    components: dict[str, ComponentStatusRead] = Field(default_factory=dict)


class SchedulerTickItem(BaseModel):
    pulse_job_id: UUID
    user_id: UUID
    subscription_policy_id: UUID
    schedule_key: str
    scheduled_for: datetime


class SchedulerTickResponse(BaseModel):
    status: str
    ticked_at: datetime
    daily_policies_seen: int
    jobs_created: int
    jobs_existing: int
    jobs_skipped_not_due: int
    created_jobs: list[SchedulerTickItem] = Field(default_factory=list)
    note: str


class WorkerHeartbeatRead(ORMModel):
    id: UUID
    worker_name: str
    worker_role: WorkerRole
    status: WorkerStatus
    hostname_or_instance: str
    pid: int | None
    started_at: datetime
    last_heartbeat_at: datetime
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_json",
        serialization_alias="metadata",
    )


class DeliveryAttemptRead(ORMModel):
    id: UUID
    delivery_job_id: UUID
    attempt_number: int
    channel: ChannelType
    adapter_name: str
    status: DeliveryAttemptStatus
    response_summary: str | None
    error_summary: str | None
    started_at: datetime
    finished_at: datetime | None


class OpsPulseJobRead(ORMModel):
    id: UUID
    user_id: UUID
    subscription_policy_id: UUID | None
    source_pulse_job_id: UUID | None
    scheduled_for: datetime
    scheduled_reason: PulseJobScheduledReason
    schedule_key: str | None
    status: PulseJobStatus
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    lease_owner: str | None
    lease_expires_at: datetime | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class ReplayResponse(BaseModel):
    action: str
    pulse_job: OpsPulseJobRead


class RequeueResponse(BaseModel):
    action: str
    delivery_job_id: UUID
    status: str
