from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.module_v3.email.model import Email


class EmailRepository(Protocol):
    async def add(self, email: Email) -> Email: ...
    async def get_by_id(self, id: UUID) -> Email | None: ...
    async def get_all_for_user(self, user_id: UUID) -> list[Email]: ...


class SqlAlchemyEmailRepository(EmailRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, email: Email) -> Email:
        self.session.add(email)
        await self.session.flush()
        return email

    async def get_by_id(self, id: UUID) -> Email | None:
        return await self.session.get(Email, id)

    async def get_all_for_user(self, user_id: UUID) -> list[Email]:
        stmt = select(Email).where(Email.user_id == user_id).order_by(Email.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
