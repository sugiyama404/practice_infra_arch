from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    MetaData,
    Table,
)
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OrderService:
    """注文処理サービス"""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # テーブル定義
        self.metadata = MetaData()
        self.products_table = Table(
            "products",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(100), nullable=False),
            Column("price", Numeric(10, 2), nullable=False),
            Column("stock_quantity", Integer, nullable=False, default=0),
            Column("reserved_quantity", Integer, nullable=False, default=0),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        self.orders_table = Table(
            "orders",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column("user_id", Integer, nullable=False),
            Column("product_id", Integer, nullable=False),
            Column("quantity", Integer, nullable=False),
            Column("total_amount", Numeric(10, 2), nullable=False),
            Column("status", String(20), nullable=False, default="reserved"),
            Column("transaction_id", String(36), nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        self.metadata.create_all(self.engine)
        self._init_sample_data()

    def _init_sample_data(self):
        with self.SessionLocal() as session:
            existing_products = session.execute(self.products_table.select()).fetchall()
            if len(existing_products) == 0:
                products_data = [
                    {"name": "Bitcoin", "price": 50000.00, "stock_quantity": 10},
                    {"name": "Ethereum", "price": 3000.00, "stock_quantity": 20},
                    {"name": "Litecoin", "price": 100.00, "stock_quantity": 50},
                ]
                for product_data in products_data:
                    session.execute(self.products_table.insert().values(**product_data))
                session.commit()
                logger.info("Sample products created")

    def reserve_product(
        self, user_id: int, product_id: int, quantity: int, transaction_id: str
    ) -> bool:
        try:
            with self.SessionLocal() as session:
                existing_order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id)
                        & (self.orders_table.c.transaction_id == transaction_id)
                    )
                ).first()

                if existing_order:
                    if existing_order.status == "reserved":
                        logger.info(
                            f"Product already reserved for user {user_id}, transaction {transaction_id}"
                        )
                        return True
                    else:
                        raise Exception(
                            f"Order exists with status: {existing_order.status}"
                        )

                product = session.execute(
                    self.products_table.select().where(
                        self.products_table.c.id == product_id
                    )
                ).first()

                if not product:
                    raise Exception("Product not found")

                available_quantity = product.stock_quantity - product.reserved_quantity
                if available_quantity < quantity:
                    raise Exception("Out of stock")

                total_amount = product.price * quantity
                order_data = {
                    "id": transaction_id,
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "total_amount": total_amount,
                    "status": "reserved",
                    "transaction_id": transaction_id,
                }
                session.execute(self.orders_table.insert().values(**order_data))

                session.execute(
                    self.products_table.update()
                    .where(self.products_table.c.id == product_id)
                    .values(reserved_quantity=product.reserved_quantity + quantity)
                )

                session.commit()
                logger.info(
                    f"Reserved {quantity} of product {product_id} for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error reserving product")
            raise

    def confirm_order(self, user_id: int, transaction_id: str) -> bool:
        try:
            with self.SessionLocal() as session:
                order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id)
                        & (self.orders_table.c.transaction_id == transaction_id)
                        & (self.orders_table.c.status == "reserved")
                    )
                ).first()

                if not order:
                    confirmed = session.execute(
                        self.orders_table.select().where(
                            (self.orders_table.c.user_id == user_id)
                            & (self.orders_table.c.transaction_id == transaction_id)
                            & (self.orders_table.c.status == "confirmed")
                        )
                    ).first()

                    if confirmed:
                        logger.info(
                            f"Order already confirmed for user {user_id}, transaction {transaction_id}"
                        )
                        return True

                    raise Exception("No order reservation found to confirm")

                product = session.execute(
                    self.products_table.select().where(
                        self.products_table.c.id == order.product_id
                    )
                ).first()

                session.execute(
                    self.products_table.update()
                    .where(self.products_table.c.id == order.product_id)
                    .values(
                        stock_quantity=product.stock_quantity - order.quantity,
                        reserved_quantity=product.reserved_quantity - order.quantity,
                    )
                )

                session.execute(
                    self.orders_table.update()
                    .where(self.orders_table.c.id == order.id)
                    .values(status="confirmed")
                )

                session.commit()
                logger.info(
                    f"Confirmed order {order.quantity} of product {order.product_id} for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error confirming order")
            raise

    def cancel_order(self, user_id: int, transaction_id: str) -> bool:
        try:
            with self.SessionLocal() as session:
                order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id)
                        & (self.orders_table.c.transaction_id == transaction_id)
                        & (self.orders_table.c.status == "reserved")
                    )
                ).first()

                if not order:
                    cancelled = session.execute(
                        self.orders_table.select().where(
                            (self.orders_table.c.user_id == user_id)
                            & (self.orders_table.c.transaction_id == transaction_id)
                            & (self.orders_table.c.status == "cancelled")
                        )
                    ).first()

                    if cancelled:
                        logger.info(
                            f"Order already cancelled for user {user_id}, transaction {transaction_id}"
                        )
                        return True

                    raise Exception("No order reservation found to cancel")

                product = session.execute(
                    self.products_table.select().where(
                        self.products_table.c.id == order.product_id
                    )
                ).first()

                session.execute(
                    self.products_table.update()
                    .where(self.products_table.c.id == order.product_id)
                    .values(
                        reserved_quantity=product.reserved_quantity - order.quantity
                    )
                )

                session.execute(
                    self.orders_table.update()
                    .where(self.orders_table.c.id == order.id)
                    .values(status="cancelled")
                )

                session.commit()
                logger.info(
                    f"Cancelled order {order.quantity} of product {order.product_id} for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error cancelling order")
            raise
