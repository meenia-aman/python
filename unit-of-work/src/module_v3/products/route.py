from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.module_v3.db import SessionDep
from src.module_v3.products.repository import (
    ProductRepository,
    SqlAlchemyProductRepository,
)
from src.module_v3.products.schema import CreateProductRequest, ProductResponse
from src.module_v3.products.service import ProductService

router = APIRouter(prefix="/products", tags=["Products v3"])


def get_product_repo(
    session: SessionDep,
) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


def get_product_service(
    product_repo: Annotated[ProductRepository, Depends(get_product_repo)],
) -> ProductService:
    return ProductService(product_repo)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProductResponse)
async def create_product(
    data: CreateProductRequest,
    product_service: Annotated[ProductService, Depends(get_product_service)],
):
    return await product_service.create_product(data)


@router.get("", response_model=list[ProductResponse])
async def get_all_products(
    product_service: Annotated[ProductService, Depends(get_product_service)],
):
    return await product_service.get_all_products()


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_by_id(
    product_id: UUID,
    product_service: Annotated[ProductService, Depends(get_product_service)],
):
    return await product_service.get_by_id(product_id)
