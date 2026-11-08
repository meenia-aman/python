from uuid import UUID

from fastapi import HTTPException, status

from src.module_v3.email.schema import CreateEmailRequest
from src.module_v3.email.service import EmailService
from src.module_v3.order.model import Order
from src.module_v3.order.repository import OrderRepository
from src.module_v3.order.schema import CreateOrderRequest
from src.module_v3.products.service import ProductService
from src.module_v3.user.service import UserService


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepository,
        user_service: UserService,
        product_service: ProductService,
        email_service: EmailService,
    ) -> None:
        self.order_repo = order_repo
        self.user_service = user_service
        self.product_service = product_service
        self.email_service = email_service

    async def create_order(self, data: CreateOrderRequest) -> Order:
        # The caller owns the transaction. Every step uses its shared session.
        user = await self.user_service.get_by_user_id(data.user_id)
        product = await self.product_service.reserve_stock(
            product_id=data.product_id,
            count=data.count,
        )
        order = await self.order_repo.add(
            Order(
                user_id=user.id,
                product_id=product.id,
                count=data.count,
                total_amount=product.price * data.count,
            )
        )
        await self.email_service.send_email(
            CreateEmailRequest(user_id=order.user_id, order_id=order.id),
        )
        return order

    async def get_by_id(self, order_id: UUID) -> Order:
        order = await self.order_repo.get_by_id(order_id)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )
        return order

    async def get_all_for_user(self, user_id: UUID) -> list[Order]:
        return await self.order_repo.get_all_for_user(user_id)
