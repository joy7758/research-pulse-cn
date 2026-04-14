"""Delivery schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from research_pulse_cn.domain.enums import ChannelType, DeliveryJobStatus
from research_pulse_cn.schemas.common import ORMModel


class DeliveryJobRead(ORMModel):
    id: UUID
    pulse_card_id: UUID | None
    pulse_job_id: UUID | None
    user_id: UUID
    channel: ChannelType
    endpoint: str
    idem_key: str
    payload: dict[str, Any]
    status: DeliveryJobStatus
    retry_count: int
    next_retry_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None
