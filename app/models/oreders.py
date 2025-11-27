from sqlalchemy import Boolean, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class OrderItem(Base):
    __tablename__ = "order_items"


class Order(Base):
    __tablename__ = "orders"

    