from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.module.user.userRepository import UserRepository
from src.module.user.user import User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def add(self, data: User) -> User:
        self.session.add(data)
        return data

    async def get(self) -> list[User]:
        statement = select(User)

        result = await self.session.execute(statement)

        return list(result.scalars().all())
