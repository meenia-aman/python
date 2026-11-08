from src.module.products.product_uow import ProductUnitOfWork
from src.module.products.product import Product
from src.module.products.schema import CreateProductRequest


class ProductService:
    def __init__(self, uow: ProductUnitOfWork) -> None:
        self.uow = uow

    async def create_product(self, data: CreateProductRequest) -> Product:

        async with self.uow:
            product = Product(
                category=data.category,
                price=data.price,
                stock_count=data.stock_count,
            )

            product = await self.uow.products.add(product)

            await self.uow.commit()

            return product

    async def get_all_products(self) -> list[Product]:

        async with self.uow:
            return await self.uow.products.get()
