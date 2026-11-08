from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.module.email.email import Email
from src.module.email.emailRepository import EmailRepository


class SqlAlchemyEmailRepository(EmailRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, email: Email) -> Email:
        self.session.add(email)

        await self.session.flush()

        return email

    async def get_by_id(self, id: UUID) -> Email | None:
        result = await self.session.get(Email, id)
        return result

    async def get_all_email_by_user_id(self, user_id: UUID) -> list[Email]:
        statement = select(Email).where(Email.user_id == user_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
