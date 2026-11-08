from uuid import UUID

from fastapi import HTTPException, status

from src.module_v3.products.model import Product
from src.module_v3.products.repository import ProductRepository
from src.module_v3.products.schema import CreateProductRequest


class ProductService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self.product_repo = product_repo

    async def create_product(
        self,
        data: CreateProductRequest,
    ) -> Product:
        product = Product(
            category=data.category,
            price=data.price,
            stock_count=data.stock_count,
        )
        product = await self.product_repo.add(product)

        return product

    async def reserve_stock(
        self,
        product_id: UUID,
        count: int,
    ) -> Product:
        # Also protect callers outside HTTP/Pydantic validation.
        if count <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Quantity must be positive",
            )

        # Lock the row so concurrent orders don't oversell
        product = await self.product_repo.get_for_update(product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )

        if product.stock_count < count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {product.stock_count}, requested: {count}",
            )

        # Deduct stock in memory
        product.stock_count -= count

        return product

    async def get_by_id(self, product_id: UUID) -> Product:
        product = await self.product_repo.get_by_id(product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    async def get_all_products(self) -> list[Product]:
        return await self.product_repo.get_all()
