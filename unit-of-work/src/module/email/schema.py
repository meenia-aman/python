from uuid import UUID
from pydantic import BaseModel


class CreateEmailRequest(BaseModel):
    user_id: UUID
    order_id: UUID
