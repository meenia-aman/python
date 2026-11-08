from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateOrderRequest(BaseModel):
    user_id: UUID
    product_id: UUID
    count: int = Field(gt=0, description="Quantity to purchase")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    product_id: UUID
    count: int
    total_amount: int
    created_at: datetime
