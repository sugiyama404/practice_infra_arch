from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DECIMAL,
    TIMESTAMP,
    Enum,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)


class Book(Base):
    __tablename__ = "books"
    book_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)


class Inventory(Base):
    __tablename__ = "inventory"
    book_id = Column(String(50), ForeignKey("books.book_id"), primary_key=True)
    available_stock = Column(Integer, nullable=False, default=0)


class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(50), primary_key=True)
    customer_id = Column(
        String(50), ForeignKey("customers.customer_id"), nullable=False
    )
    status = Column(
        Enum("PENDING", "CONFIRMED", "CANCELLED", "FAILED"),
        nullable=False,
        default="PENDING",
    )
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    confirmed_at = Column(TIMESTAMP, nullable=True)
    cancelled_at = Column(TIMESTAMP, nullable=True)
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    book_id = Column(String(50), ForeignKey("books.book_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    order = relationship("Order", back_populates="items")


class Event(Base):
    __tablename__ = "events"
    event_id = Column(String(36), primary_key=True)
    aggregate_id = Column(String(50), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())
