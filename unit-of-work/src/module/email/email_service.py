from uuid import UUID

from src.module.email.email import Email
from src.module.email.emailRepository import EmailRepository
from src.module.email.email_uow import EmailUnitOfWork
from src.module.email.schema import CreateEmailRequest


async def queue_order_email(
    emails: EmailRepository,
    *,
    user_id: UUID,
    order_id: UUID,
) -> Email:
    """Stage a pending email in the caller's transaction."""
    return await emails.add(Email(user_id=user_id, order_id=order_id))


class EmailService:
    def __init__(self, uow: EmailUnitOfWork) -> None:
        self.uow = uow

    async def send_email(self, data: CreateEmailRequest) -> Email:
        """Queue an order email as a standalone operation."""
        async with self.uow as uow:
            email = await queue_order_email(
                uow.emails, user_id=data.user_id, order_id=data.order_id
            )
            await uow.commit()
            return email
