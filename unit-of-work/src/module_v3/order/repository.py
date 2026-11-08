from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.module_v3.order.model import Order


class OrderRepository(Protocol):
    async def add(self, order: Order) -> Order: ...
    async def get_by_id(self, order_id: UUID) -> Order | None: ...
    async def get_all_for_user(self, user_id: UUID) -> list[Order]: ...


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_all_for_user(self, user_id: UUID) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
