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


class PaymentService:
    """決済処理サービス"""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # テーブル定義
        self.metadata = MetaData()
        self.payment_methods_table = Table(
            "payment_methods",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_id", Integer, nullable=False),
            Column("method_type", String(50), nullable=False),
            Column("method_details", String(255)),
            Column("is_active", Integer, default=1),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        self.payment_transactions_table = Table(
            "payment_transactions",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column("user_id", Integer, nullable=False),
            Column("payment_method_id", Integer, nullable=False),
            Column("amount", Numeric(10, 2), nullable=False),
            Column("status", String(20), nullable=False, default="reserved"),
            Column("transaction_id", String(36), nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        self.metadata.create_all(self.engine)
        self._init_sample_data()

    def _init_sample_data(self):
        with self.SessionLocal() as session:
            existing_methods = session.execute(
                self.payment_methods_table.select()
            ).fetchall()
            if len(existing_methods) == 0:
                payment_methods_data = [
                    {
                        "user_id": 1,
                        "method_type": "credit_card",
                        "method_details": '{"last4": "1234", "brand": "visa"}',
                    },
                    {
                        "user_id": 2,
                        "method_type": "credit_card",
                        "method_details": '{"last4": "5678", "brand": "mastercard"}',
                    },
                    {
                        "user_id": 3,
                        "method_type": "paypal",
                        "method_details": '{"email": "charlie@example.com"}',
                    },
                ]
                for method_data in payment_methods_data:
                    session.execute(
                        self.payment_methods_table.insert().values(**method_data)
                    )
                session.commit()

    def reserve_payment(
        self, user_id: int, payment_method_id: int, amount: float, transaction_id: str
    ) -> bool:
        try:
            with self.SessionLocal() as session:
                existing_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id)
                        & (
                            self.payment_transactions_table.c.transaction_id
                            == transaction_id
                        )
                    )
                ).first()

                if existing_transaction:
                    if existing_transaction.status == "reserved":
                        logger.info(
                            f"Payment already reserved for user {user_id}, transaction {transaction_id}"
                        )
                        return True
                    else:
                        raise Exception(
                            f"Payment transaction exists with status: {existing_transaction.status}"
                        )

                payment_method = session.execute(
                    self.payment_methods_table.select().where(
                        (self.payment_methods_table.c.id == payment_method_id)
                        & (self.payment_methods_table.c.user_id == user_id)
                        & (self.payment_methods_table.c.is_active == 1)
                    )
                ).first()

                if not payment_method:
                    raise Exception("Invalid payment method")

                if amount <= 0:
                    raise Exception("Invalid amount")

                transaction_data = {
                    "id": transaction_id,
                    "user_id": user_id,
                    "payment_method_id": payment_method_id,
                    "amount": amount,
                    "status": "reserved",
                    "transaction_id": transaction_id,
                }
                session.execute(
                    self.payment_transactions_table.insert().values(**transaction_data)
                )
                session.commit()
                logger.info(
                    f"Reserved payment {amount} for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error reserving payment")
            raise

    def charge_payment(self, user_id: int, transaction_id: str) -> bool:
        try:
            with self.SessionLocal() as session:
                payment_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id)
                        & (
                            self.payment_transactions_table.c.transaction_id
                            == transaction_id
                        )
                        & (self.payment_transactions_table.c.status == "reserved")
                    )
                ).first()

                if not payment_transaction:
                    charged = session.execute(
                        self.payment_transactions_table.select().where(
                            (self.payment_transactions_table.c.user_id == user_id)
                            & (
                                self.payment_transactions_table.c.transaction_id
                                == transaction_id
                            )
                            & (self.payment_transactions_table.c.status == "charged")
                        )
                    ).first()

                    if charged:
                        logger.info(
                            f"Payment already charged for user {user_id}, transaction {transaction_id}"
                        )
                        return True

                    raise Exception("No payment reservation found to charge")

                session.execute(
                    self.payment_transactions_table.update()
                    .where(
                        self.payment_transactions_table.c.id == payment_transaction.id
                    )
                    .values(status="charged")
                )

                session.commit()
                logger.info(
                    f"Charged payment for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error charging payment")
            raise

    def cancel_payment(self, user_id: int, transaction_id: str) -> bool:
        try:
            with self.SessionLocal() as session:
                payment_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id)
                        & (
                            self.payment_transactions_table.c.transaction_id
                            == transaction_id
                        )
                        & (self.payment_transactions_table.c.status == "reserved")
                    )
                ).first()

                if not payment_transaction:
                    cancelled = session.execute(
                        self.payment_transactions_table.select().where(
                            (self.payment_transactions_table.c.user_id == user_id)
                            & (
                                self.payment_transactions_table.c.transaction_id
                                == transaction_id
                            )
                            & (self.payment_transactions_table.c.status == "cancelled")
                        )
                    ).first()

                    if cancelled:
                        logger.info(
                            f"Payment already cancelled for user {user_id}, transaction {transaction_id}"
                        )
                        return True

                    raise Exception("No payment reservation found to cancel")

                session.execute(
                    self.payment_transactions_table.update()
                    .where(
                        self.payment_transactions_table.c.id == payment_transaction.id
                    )
                    .values(status="cancelled")
                )

                session.commit()
                logger.info(
                    f"Cancelled payment for user {user_id}, transaction {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error cancelling payment")
            raise
