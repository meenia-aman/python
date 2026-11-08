from typing import Protocol
from uuid import UUID
from src.module.order.order import Order


class OrderRepository(Protocol):
    async def add(self, order: Order) -> Order: ...

    async def get_by_id(self, order_id: UUID) -> Order | None: ...

    async def get_all_order_by_user_id(self, user_id: UUID) -> list[Order]: ...
