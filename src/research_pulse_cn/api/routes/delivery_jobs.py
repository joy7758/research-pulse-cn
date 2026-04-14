"""Delivery job routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from research_pulse_cn.api.dependencies import get_delivery_service
from research_pulse_cn.domain.enums import DeliveryJobStatus
from research_pulse_cn.schemas.delivery import DeliveryJobRead
from research_pulse_cn.services.delivery import DeliveryService

router = APIRouter(prefix="/delivery-jobs", tags=["delivery-jobs"])
DeliveryServiceDep = Annotated[DeliveryService, Depends(get_delivery_service)]
UserIdQuery = Annotated[UUID | None, Query()]
StatusQuery = Annotated[DeliveryJobStatus | None, Query()]


@router.get("", response_model=list[DeliveryJobRead])
def list_delivery_jobs(
    service: DeliveryServiceDep,
    user_id: UserIdQuery = None,
    status: StatusQuery = None,
) -> list[DeliveryJobRead]:
    return service.list_delivery_jobs(user_id=user_id, status=status)
