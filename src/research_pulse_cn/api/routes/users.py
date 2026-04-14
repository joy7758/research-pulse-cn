"""User routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from research_pulse_cn.api.dependencies import get_user_service
from research_pulse_cn.schemas.user import UserProfileCreate, UserProfileRead, UserProfileUpdate
from research_pulse_cn.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("", response_model=list[UserProfileRead])
def list_users(service: UserServiceDep) -> list[UserProfileRead]:
    return service.list_users()


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserProfileCreate,
    service: UserServiceDep,
) -> UserProfileRead:
    return service.create_user(payload)


@router.get("/{user_id}", response_model=UserProfileRead)
def get_user(user_id: UUID, service: UserServiceDep) -> UserProfileRead:
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserProfileRead)
def update_user(
    user_id: UUID,
    payload: UserProfileUpdate,
    service: UserServiceDep,
) -> UserProfileRead:
    return service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, service: UserServiceDep) -> Response:
    service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
