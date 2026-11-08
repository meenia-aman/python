from pydantic import BaseModel

from src.module.products.product import ProductCategory


class CreateProductRequest(BaseModel):
    category: ProductCategory
    price: int
    stock_count: int
