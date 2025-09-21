from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    Enum,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import uuid

Base = declarative_base()


class PaymentMethod(enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    ELECTRONIC_MONEY = "ELECTRONIC_MONEY"
    COD = "COD"


class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class OrderStatus(enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ShipmentStatus(enum.Enum):
    PENDING = "PENDING"
    ARRANGED = "ARRANGED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


class SagaStatus(enum.Enum):
    STARTED = "STARTED"
    ORDER_CREATED = "ORDER_CREATED"
    STOCK_RESERVED = "STOCK_RESERVED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    SHIPPING_ARRANGED = "SHIPPING_ARRANGED"
    COMPLETED = "COMPLETED"
    COMPENSATION_STARTED = "COMPENSATION_STARTED"
    FAILED = "FAILED"


class EventType(enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_FAILED = "ORDER_FAILED"
    STOCK_RESERVED = "STOCK_RESERVED"
    STOCK_RELEASED = "STOCK_RELEASED"
    STOCK_UNAVAILABLE = "STOCK_UNAVAILABLE"
    PAYMENT_STARTED = "PAYMENT_STARTED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_REFUNDED = "PAYMENT_REFUNDED"
    SHIPPING_ARRANGED = "SHIPPING_ARRANGED"
    SHIPPING_SHIPPED = "SHIPPING_SHIPPED"
    SHIPPING_DELIVERED = "SHIPPING_DELIVERED"
    SHIPPING_FAILED = "SHIPPING_FAILED"


class StepStatus(enum.Enum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))
    address = Column(Text)
    payment_method_default = Column(
        Enum(PaymentMethod), default=PaymentMethod.CREDIT_CARD
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


class Book(Base):
    __tablename__ = "books"

    book_id = Column(String(50), primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
    isbn = Column(String(20), unique=True)
    category = Column(String(50))
    price = Column(Float, nullable=False)
    publisher = Column(String(100))
    publication_date = Column(DateTime)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory = relationship("Inventory", back_populates="book", uselist=False)
    order_items = relationship("OrderItem", back_populates="book")


class Inventory(Base):
    __tablename__ = "inventory"

    book_id = Column(String(50), ForeignKey("books.book_id"), primary_key=True)
    available_stock = Column(Integer, nullable=False, default=0)
    reserved_stock = Column(Integer, nullable=False, default=0)
    reorder_point = Column(Integer, default=5)
    max_stock = Column(Integer, default=100)
    last_restocked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    book = relationship("Book", back_populates="inventory")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)
    customer_id = Column(
        String(50), ForeignKey("customers.customer_id"), nullable=False
    )
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    shipping_fee = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    customer = relationship("Customer", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    payment = relationship("Payment", back_populates="order", uselist=False)
    shipment = relationship("Shipment", back_populates="order", uselist=False)
    saga_instance = relationship("SagaInstance", back_populates="order", uselist=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    book_id = Column(String(50), ForeignKey("books.book_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="order_items")
    book = relationship("Book", back_populates="order_items")

    __table_args__ = (UniqueConstraint("order_id", "book_id", name="uk_order_book"),)


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    transaction_id = Column(String(100))
    gateway_response = Column(JSON)
    processed_at = Column(DateTime)
    failed_reason = Column(Text)
    refunded_amount = Column(Float, default=0)
    refunded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    order = relationship("Order", back_populates="payment")


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    carrier = Column(String(50), nullable=False)
    tracking_number = Column(String(100))
    status = Column(
        Enum(ShipmentStatus), nullable=False, default=ShipmentStatus.PENDING
    )
    shipping_address = Column(JSON, nullable=False)
    estimated_delivery = Column(DateTime)
    actual_delivery_date = Column(DateTime)
    shipping_cost = Column(Float, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)

    order = relationship("Order", back_populates="shipment")


class SagaInstance(Base):
    __tablename__ = "saga_instances"

    saga_id = Column(String(50), primary_key=True)
    saga_type = Column(String(50), nullable=False, default="ORDER_PROCESSING")
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=False)
    status = Column(Enum(SagaStatus), nullable=False, default=SagaStatus.STARTED)
    current_step = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=False)
    compensation_data = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)

    order = relationship("Order", back_populates="saga_instance")
    step_logs = relationship("SagaStepLog", back_populates="saga_instance")


class SagaStepLog(Base):
    __tablename__ = "saga_step_logs"

    step_log_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    saga_id = Column(String(50), ForeignKey("saga_instances.saga_id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    service_name = Column(String(50), nullable=False)
    command_type = Column(String(50), nullable=False)
    status = Column(Enum(StepStatus), nullable=False)
    request_payload = Column(JSON)
    response_payload = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)

    saga_instance = relationship("SagaInstance", back_populates="step_logs")

    __table_args__ = (UniqueConstraint("saga_id", "step_number", name="uk_saga_step"),)


class Event(Base):
    __tablename__ = "events"

    event_id = Column(String(36), primary_key=True)
    aggregate_id = Column(String(50), nullable=False)
    aggregate_type = Column(String(50), nullable=False, default="order")
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSON, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)

    __table_args__ = (
        Index("idx_events_aggregate_id", aggregate_id),
        Index("idx_events_event_type", event_type),
        Index("idx_events_created_at", created_at),
    )


# インデックスの作成
Index("idx_customers_email", Customer.email)
Index("idx_customers_created_at", Customer.created_at)
Index("idx_books_title", Book.title)
Index("idx_books_category", Book.category)
Index("idx_books_isbn", Book.isbn)
Index("idx_inventory_available_stock", Inventory.available_stock)
Index("idx_inventory_updated_at", Inventory.updated_at)
Index("idx_orders_customer_id", Order.customer_id)
Index("idx_orders_status", Order.status)
Index("idx_orders_created_at", Order.created_at, Order.created_at.desc())
Index("idx_order_items_order_id", OrderItem.order_id)
Index("idx_order_items_book_id", OrderItem.book_id)
Index("idx_payments_order_id", Payment.order_id)
Index("idx_payments_status", Payment.status)
Index("idx_payments_transaction_id", Payment.transaction_id)
Index("idx_payments_created_at", Payment.created_at, Payment.created_at.desc())
Index("idx_shipments_order_id", Shipment.order_id)
Index("idx_shipments_tracking_number", Shipment.tracking_number)
Index("idx_shipments_status", Shipment.status)
Index("idx_shipments_estimated_delivery", Shipment.estimated_delivery)
Index("idx_saga_instances_order_id", SagaInstance.order_id)
Index("idx_saga_instances_status", SagaInstance.status)
Index(
    "idx_saga_instances_created_at",
    SagaInstance.created_at,
    SagaInstance.created_at.desc(),
)
Index("idx_saga_step_logs_saga_id", SagaStepLog.saga_id)
Index("idx_saga_step_logs_status", SagaStepLog.status)


# Database session factory
def get_db_session():
    """Create and return a database session"""
    from shared.config import get_database_url

    engine = create_engine(get_database_url(), pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
