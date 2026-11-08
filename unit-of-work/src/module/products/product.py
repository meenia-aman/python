from datetime import datetime
from enum import Enum
import uuid

from sqlalchemy import TIMESTAMP, UUID, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum

from src.db.base import Base


class ProductCategory(str, Enum):
    CLOTHING = "CLOTHING"
    ELECTRONICS = "ELECTRONICS"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    category: Mapped[ProductCategory] = mapped_column(
        SAEnum(
            ProductCategory,
            name="ck_product_category",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )

    price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    stock_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
