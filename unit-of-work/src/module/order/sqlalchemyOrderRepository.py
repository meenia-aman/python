from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.module.order.order import Order
from src.module.order.orderRepository import OrderRepository
from sqlalchemy import select


class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return order

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.session.get(Order, order_id)
        return result

    async def get_all_order_by_user_id(self, user_id: UUID) -> list[Order]:
        statement = select(Order).where(
            Order.user_id == user_id,
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())
