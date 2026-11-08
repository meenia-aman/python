from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.module_v3.db import SessionDep
from src.module_v3.email.repository import EmailRepository, SqlAlchemyEmailRepository
from src.module_v3.email.schema import CreateEmailRequest, EmailResponse
from src.module_v3.email.service import EmailService

router = APIRouter(prefix="/emails", tags=["Emails v3"])


def get_email_repo(
    session: SessionDep,
) -> EmailRepository:
    return SqlAlchemyEmailRepository(session)


def get_email_service(
    email_repo: Annotated[EmailRepository, Depends(get_email_repo)],
) -> EmailService:
    return EmailService(email_repo)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EmailResponse)
async def send_email(
    data: CreateEmailRequest,
    email_service: Annotated[EmailService, Depends(get_email_service)],
):
    return await email_service.send_email(data)


@router.get("/user/{user_id}", response_model=list[EmailResponse])
async def get_emails_for_user(
    user_id: UUID,
    email_service: Annotated[EmailService, Depends(get_email_service)],
):
    return await email_service.get_all_for_user(user_id)
