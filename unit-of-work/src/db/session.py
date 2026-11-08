from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


DATABASE_URL = "postgresql+asyncpg://postgres:mypassword@localhost:5432/unit-of-work"

engine: AsyncEngine = create_async_engine(
    url=DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            print(" Session Yield")
        except Exception:
            await session.rollback()
            print("Exception occured rollbacked")
            raise
        finally:
            await session.close()
            print("Session Closed")
