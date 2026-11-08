from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.module_v3.email.model import EmailStatus


class CreateEmailRequest(BaseModel):
    user_id: UUID
    order_id: UUID


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    order_id: UUID
    status: EmailStatus
    created_at: datetime
