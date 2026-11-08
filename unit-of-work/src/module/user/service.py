from uuid import UUID

from fastapi import HTTPException, status

from src.module.user.user_uow import UserUnitOfWork
from src.module.user.schema import CreateUserRequest
from src.module.user.user import User


class UserService:
    def __init__(self, uow: UserUnitOfWork):
        self.uow = uow

    async def create_user(self, data: CreateUserRequest) -> User:

        async with self.uow:
            prev_user = await self.uow.users.get_by_email(data.email)

            if prev_user is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists",
                )

            user = User(name=data.name, email=data.email)

            user = await self.uow.users.add(user)

            await self.uow.commit()

            return user

    async def get_by_user_id(self, user_id: UUID) -> User | None:

        async with self.uow:
            return await self.uow.users.get_by_id(user_id)

    async def get_all_users(self) -> list[User]:

        async with self.uow:
            return await self.uow.users.get()
