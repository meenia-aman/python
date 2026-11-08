from abc import abstractmethod
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.unit_of_work import AbstractUnitOfWork
from src.db.session import AsyncSessionLocal


class SqlAlchemyBaseUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()

        self.init_repositories()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            if self.session is not None:
                await self.session.close()

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()

    @abstractmethod
    def init_repositories(self) -> None:
        # Every child domain class implements this to wire up its specific repositories

        raise NotImplementedError
