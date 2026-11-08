from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.module_v3.products.model import ProductCategory


class CreateProductRequest(BaseModel):
    category: ProductCategory
    price: int = Field(gt=0, description="Price must be positive")
    stock_count: int = Field(ge=0, description="Stock count cannot be negative")


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: ProductCategory
    price: int
    stock_count: int
    created_at: datetime
    updated_at: datetime
