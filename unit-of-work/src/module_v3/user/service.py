from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from src.module_v3.user.model import User
from src.module_v3.user.repository import UserRepository
from src.module_v3.user.schema import CreateUserRequest


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def create_user(
        self,
        data: CreateUserRequest,
    ) -> User:
        prev_user = await self.user_repo.get_by_email(str(data.email))
        if prev_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        user = User(name=data.name, email=str(data.email))
        try:
            user = await self.user_repo.add(user)
        except IntegrityError as exc:
            # The pre-check can race. PostgreSQL's unique constraint is decisive.
            cause = exc.orig.__cause__
            if (
                getattr(exc.orig, "sqlstate", None) == "23505"
                and getattr(cause, "constraint_name", None) == "users_email_key"
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists",
                ) from exc
            raise

        return user

    async def get_by_user_id(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_all_users(self) -> list[User]:
        return await self.user_repo.get_all()
