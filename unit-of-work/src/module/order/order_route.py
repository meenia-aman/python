from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from src.module.order.order_uow import OrderUnitOfWork
from src.module.order.schema import CreateOrderRequest
from src.module.order.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Order"])


def get_order_uow() -> OrderUnitOfWork:
    return OrderUnitOfWork()


def get_order_service(
    uow: Annotated[OrderUnitOfWork, Depends(get_order_uow)],
) -> OrderService:
    return OrderService(uow)


@router.post("/")
async def create_order(
    data: CreateOrderRequest,
    order_service: Annotated[OrderService, Depends(get_order_service)],
):

    result = await order_service.create_order(data)

    return result


@router.get("/{user_id}")
async def get_order_by_user_id(
    user_id: UUID,
    order_service: Annotated[OrderService, Depends(get_order_service)],
):

    result = await order_service.get_all_order_for_user(user_id)

    return result
