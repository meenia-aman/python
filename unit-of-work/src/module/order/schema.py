from uuid import UUID

from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    user_id: UUID
    product_id: UUID
    count: int
    amount: int
