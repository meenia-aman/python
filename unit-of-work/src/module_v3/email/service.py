from uuid import UUID

from src.module_v3.email.model import Email
from src.module_v3.email.repository import EmailRepository
from src.module_v3.email.schema import CreateEmailRequest


class EmailService:
    def __init__(self, email_repo: EmailRepository) -> None:
        self.email_repo = email_repo

    async def send_email(
        self,
        data: CreateEmailRequest,
    ) -> Email:
        """Queue a PENDING email record in the caller's transaction; no network I/O."""
        email = Email(user_id=data.user_id, order_id=data.order_id)
        email = await self.email_repo.add(email)

        return email

    async def get_all_for_user(self, user_id: UUID) -> list[Email]:
        return await self.email_repo.get_all_for_user(user_id)
