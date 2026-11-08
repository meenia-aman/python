from typing import Annotated

from fastapi import APIRouter, Depends

from src.module.products.product_uow import ProductUnitOfWork
from src.module.products.productService import ProductService
from src.module.products.schema import CreateProductRequest

router = APIRouter(prefix="/products", tags=["Products"])


def get_product_uow() -> ProductUnitOfWork:
    return ProductUnitOfWork()


def get_product_service(uow: Annotated[ProductUnitOfWork, Depends(get_product_uow)]):
    return ProductService(uow)


@router.post("/")
async def create_product(
    data: CreateProductRequest,
    product_service: Annotated[ProductService, Depends(get_product_service)],
):

    result = await product_service.create_product(data)

    return result


@router.get("/")
async def get_products(
    product_service: Annotated[ProductService, Depends(get_product_service)],
):

    result = await product_service.get_all_products()

    return result
