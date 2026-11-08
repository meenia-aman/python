from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.module.products.product import Product
from src.module.products.productRepository import ProductRepsository


class SqlAlchemyProductRepository(ProductRepsository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, product_id) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get(self) -> list[Product]:
        result = await self.session.execute(select(Product))
        return list(result.scalars().all())

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.flush()
        return product
