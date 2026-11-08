from src.db.sqlAlchemyBaseUnitOfWork import SqlAlchemyBaseUnitOfWork
from src.module.user.sqlalchemyRepository import SqlAlchemyUserRepository
from src.module.user.userRepository import UserRepository


class UserUnitOfWork(SqlAlchemyBaseUnitOfWork):
    users: UserRepository

    def init_repositories(self) -> None:
        assert self.session is not None
        self.users = SqlAlchemyUserRepository(self.session)
