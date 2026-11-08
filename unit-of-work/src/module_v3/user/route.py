from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.module_v3.db import SessionDep
from src.module_v3.user.repository import SqlAlchemyUserRepository, UserRepository
from src.module_v3.user.schema import CreateUserRequest, UserResponse
from src.module_v3.user.service import UserService

router = APIRouter(prefix="/users", tags=["Users v3"])


def get_user_repo(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_user_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(user_repo)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(
    data: CreateUserRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return await user_service.create_user(data)


@router.get("", response_model=list[UserResponse])
async def get_all_users(
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return await user_service.get_all_users()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    return await user_service.get_by_user_id(user_id)
