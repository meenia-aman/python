from typing import Annotated

from fastapi import APIRouter, Depends

from src.module.user.user_uow import UserUnitOfWork
from src.module.user.schema import CreateUserRequest
from src.module.user.service import UserService


router = APIRouter()


def get_user_uow() -> UserUnitOfWork:
    return UserUnitOfWork()


def get_user_service(
    uow: Annotated[UserUnitOfWork, Depends(get_user_uow)],
) -> UserService:
    return UserService(uow)


@router.post("/register")
async def create_user(
    data: CreateUserRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    result = await user_service.create_user(data)
    return result


@router.get("/users")
async def get_all_user(
    user_service: Annotated[UserService, Depends(get_user_service)],
):
    result = await user_service.get_all_users()
    return result
