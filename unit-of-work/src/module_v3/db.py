from typing import Annotated, Any, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    __mapper_args__: dict[str, Any] = {"eager_defaults": True}


engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autobegin=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One session and transaction per API operation; shared by all repositories."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


# Commit/rollback and close before FastAPI sends the response. Keep the default
# dependency cache enabled so every repository in this operation gets this session.
SessionDep = Annotated[AsyncSession, Depends(get_db, scope="function")]
