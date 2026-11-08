from fastapi import APIRouter
from src.module.user.route import router as user_router
from src.module.products.product_route import router as product_router
from src.module.order.order_route import router as order_router

api_router = APIRouter()

api_router.include_router(user_router)
api_router.include_router(product_router)
api_router.include_router(order_router)
