# Register the tables referenced by Email when this UoW runs outside the web app.
import src.models  # noqa: F401
from src.db.sqlAlchemyBaseUnitOfWork import SqlAlchemyBaseUnitOfWork
from src.module.email.emailRepository import EmailRepository
from src.module.email.sqlalchemyEmailRepository import SqlAlchemyEmailRepository


class EmailUnitOfWork(SqlAlchemyBaseUnitOfWork):
    emails: EmailRepository

    def init_repositories(self) -> None:
        assert self.session is not None
        self.emails = SqlAlchemyEmailRepository(self.session)
