from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=3, max_length=50)
    email: EmailStr
