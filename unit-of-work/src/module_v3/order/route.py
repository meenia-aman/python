from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.module_v3.db import SessionDep
from src.module_v3.email.route import get_email_service
from src.module_v3.email.service import EmailService
from src.module_v3.order.repository import (
    OrderRepository,
    SqlAlchemyOrderRepository,
)
from src.module_v3.order.schema import CreateOrderRequest, OrderResponse
from src.module_v3.order.service import OrderService
from src.module_v3.products.route import get_product_service
from src.module_v3.products.service import ProductService
from src.module_v3.user.route import get_user_service
from src.module_v3.user.service import UserService

router = APIRouter(prefix="/orders", tags=["Orders v3"])


def get_order_repo(
    session: SessionDep,
) -> OrderRepository:
    return SqlAlchemyOrderRepository(session)


def get_order_service(
    order_repo: Annotated[OrderRepository, Depends(get_order_repo)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> OrderService:
    return OrderService(
        order_repo=order_repo,
        user_service=user_service,
        product_service=product_service,
        email_service=email_service,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
async def create_order(
    data: CreateOrderRequest,
    order_service: Annotated[OrderService, Depends(get_order_service)],
):
    return await order_service.create_order(data)


@router.get("/user/{user_id}", response_model=list[OrderResponse])
async def get_orders_for_user(
    user_id: UUID,
    order_service: Annotated[OrderService, Depends(get_order_service)],
):
    return await order_service.get_all_for_user(user_id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_by_id(
    order_id: UUID,
    order_service: Annotated[OrderService, Depends(get_order_service)],
):
    return await order_service.get_by_id(order_id)
