from uuid import UUID
from fastapi import HTTPException, status

from src.module.email.email_service import queue_order_email
from src.module.order.order_uow import OrderUnitOfWork
from src.module.order.order import Order
from src.module.order.schema import CreateOrderRequest


class OrderService:
    def __init__(self, uow: OrderUnitOfWork) -> None:
        self.uow = uow

    async def create_order(self, data: CreateOrderRequest) -> Order:

        async with self.uow:
            user = await self.uow.users.get_by_id(data.user_id)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User now found",
                )

            product = await self.uow.products.get_by_id(data.product_id)

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found",
                )

            if product.stock_count < data.count:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Insufficient stock",
                )

            product.stock_count -= data.count

            order = Order(
                user_id=data.user_id,
                product_id=data.product_id,
                count=data.count,
                total_amount=data.amount * data.count,
            )

            order = await self.uow.orders.add(order)

            await queue_order_email(
                self.uow.emails, user_id=order.user_id, order_id=order.id
            )

            await self.uow.commit()

            return order

    async def get_all_order_for_user(self, user_id: UUID) -> list[Order]:
        async with self.uow:
            return await self.uow.orders.get_all_order_by_user_id(user_id)
