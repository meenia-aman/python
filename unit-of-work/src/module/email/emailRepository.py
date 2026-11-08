from typing import Protocol
from uuid import UUID

from src.module.email.email import Email


class EmailRepository(Protocol):
    async def add(self, email: Email) -> Email: ...

    async def get_by_id(self, id: UUID) -> Email | None: ...

    async def get_all_email_by_user_id(self, user_id: UUID) -> list[Email]: ...
