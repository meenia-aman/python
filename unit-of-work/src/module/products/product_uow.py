from src.db.sqlAlchemyBaseUnitOfWork import SqlAlchemyBaseUnitOfWork
from src.module.products.productRepository import ProductRepsository
from src.module.products.sqlalchemyProductRepository import SqlAlchemyProductRepository


class ProductUnitOfWork(SqlAlchemyBaseUnitOfWork):
    products: ProductRepsository

    def init_repositories(self) -> None:
        assert self.session is not None
        self.products = SqlAlchemyProductRepository(self.session)
