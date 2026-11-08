from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.module_v3.products.model import Product


class ProductRepository(Protocol):
    async def get_by_id(self, product_id: UUID) -> Product | None: ...
    async def get_for_update(self, product_id: UUID) -> Product | None: ...
    async def add(self, product: Product) -> Product: ...
    async def get_all(self) -> list[Product]: ...


class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get_for_update(self, product_id: UUID) -> Product | None:
        # Preserve pending changes before refreshing an already-loaded product.
        await self.session.flush()
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product

    async def get_all(self) -> list[Product]:
        stmt = select(Product).order_by(Product.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
