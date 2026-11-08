from typing import Protocol

from src.module.products.product import Product


class ProductRepsository(Protocol):
    async def add(self, product: Product) -> Product: ...

    async def get_by_id(self, product_id) -> Product | None: ...

    async def get(self) -> list[Product]: ...
