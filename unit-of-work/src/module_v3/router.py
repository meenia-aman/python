from fastapi import APIRouter

from src.module_v3.email.route import router as email_router
from src.module_v3.order.route import router as order_router
from src.module_v3.products.route import router as product_router
from src.module_v3.user.route import router as user_router

api_router = APIRouter(prefix="/v3")

api_router.include_router(user_router)
api_router.include_router(product_router)
api_router.include_router(email_router)
api_router.include_router(order_router)
