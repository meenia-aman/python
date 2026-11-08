from src.db.sqlAlchemyBaseUnitOfWork import SqlAlchemyBaseUnitOfWork
from src.module.email.emailRepository import EmailRepository
from src.module.email.sqlalchemyEmailRepository import SqlAlchemyEmailRepository
from src.module.order.orderRepository import OrderRepository
from src.module.order.sqlalchemyOrderRepository import SqlAlchemyOrderRepository
from src.module.products.productRepository import ProductRepsository
from src.module.products.sqlalchemyProductRepository import SqlAlchemyProductRepository
from src.module.user.sqlalchemyRepository import SqlAlchemyUserRepository
from src.module.user.userRepository import UserRepository


class OrderUnitOfWork(SqlAlchemyBaseUnitOfWork):
    orders: OrderRepository
    products: ProductRepsository
    emails: EmailRepository
    users: UserRepository

    def init_repositories(self) -> None:
        assert self.session is not None

        self.orders = SqlAlchemyOrderRepository(self.session)
        self.products = SqlAlchemyProductRepository(self.session)
        self.emails = SqlAlchemyEmailRepository(self.session)
        self.users = SqlAlchemyUserRepository(self.session)
