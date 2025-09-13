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


class UserService:
    """ユーザー残高管理サービス（シンプルなTCCサンプル実装）"""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        self.metadata = MetaData()
        # usersテーブル: 残高と予約残高を保持
        self.users_table = Table(
            "users",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(100), nullable=False),
            Column("balance", Numeric(12, 2), nullable=False, default=0),
            Column("reserved", Numeric(12, 2), nullable=False, default=0),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        # balance_transactions: トランザクション単位での予約/確定/キャンセルを記録
        self.balance_transactions_table = Table(
            "balance_transactions",
            self.metadata,
            Column("id", String(36), primary_key=True),
            Column("user_id", Integer, nullable=False),
            Column("amount", Numeric(12, 2), nullable=False),
            Column("status", String(20), nullable=False),
            Column("created_at", DateTime, default=datetime.utcnow),
        )

        self.metadata.create_all(self.engine)
        self._init_sample_data()

    def _init_sample_data(self):
        with self.SessionLocal() as session:
            existing = session.execute(self.users_table.select()).fetchall()
            if len(existing) == 0:
                users = [
                    {"name": "alice", "balance": 1000.0, "reserved": 0},
                    {"name": "bob", "balance": 500.0, "reserved": 0},
                    {"name": "charlie", "balance": 2000.0, "reserved": 0},
                ]
                for u in users:
                    session.execute(self.users_table.insert().values(**u))
                session.commit()

    def reserve_balance(self, user_id: int, amount: float, transaction_id: str) -> bool:
        """残高を予約（TCC Try）"""
        try:
            with self.SessionLocal() as session:
                # 冪等性: 既にトランザクションがあるか
                existing = session.execute(
                    self.balance_transactions_table.select().where(
                        self.balance_transactions_table.c.id == transaction_id
                    )
                ).first()
                if existing:
                    if existing.status == "reserved":
                        logger.info("Balance already reserved")
                        return True
                    else:
                        raise Exception(
                            f"Transaction exists with status {existing.status}"
                        )

                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                if not user:
                    raise Exception("User not found")

                available = user.balance - user.reserved
                if available < amount:
                    raise Exception("Insufficient funds")

                # 予約を追加
                session.execute(
                    self.users_table.update()
                    .where(self.users_table.c.id == user_id)
                    .values(reserved=user.reserved + amount)
                )

                session.execute(
                    self.balance_transactions_table.insert().values(
                        id=transaction_id,
                        user_id=user_id,
                        amount=amount,
                        status="reserved",
                    )
                )

                session.commit()
                logger.info(f"Reserved {amount} for user {user_id}")
                return True
        except Exception:
            logger.exception("Error reserving balance")
            raise

    def confirm_balance(self, user_id: int, transaction_id: str) -> bool:
        """残高を確定（TCC Confirm）"""
        try:
            with self.SessionLocal() as session:
                tx = session.execute(
                    self.balance_transactions_table.select().where(
                        self.balance_transactions_table.c.id == transaction_id
                    )
                ).first()
                if not tx:
                    raise Exception("Transaction not found")
                if tx.status == "confirmed":
                    logger.info("Transaction already confirmed")
                    return True

                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                if not user:
                    raise Exception("User not found")

                # reservedから差し引き、balanceから引く
                session.execute(
                    self.users_table.update()
                    .where(self.users_table.c.id == user_id)
                    .values(
                        balance=user.balance - tx.amount,
                        reserved=user.reserved - tx.amount,
                    )
                )

                session.execute(
                    self.balance_transactions_table.update()
                    .where(self.balance_transactions_table.c.id == transaction_id)
                    .values(status="confirmed")
                )

                session.commit()
                logger.info(
                    f"Confirmed balance for user {user_id}, tx {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error confirming balance")
            raise

    def cancel_balance(self, user_id: int, transaction_id: str) -> bool:
        """残高予約をキャンセル（TCC Cancel）"""
        try:
            with self.SessionLocal() as session:
                tx = session.execute(
                    self.balance_transactions_table.select().where(
                        self.balance_transactions_table.c.id == transaction_id
                    )
                ).first()
                if not tx:
                    logger.info("No transaction found to cancel")
                    return True
                if tx.status == "cancelled":
                    logger.info("Transaction already cancelled")
                    return True

                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                if not user:
                    raise Exception("User not found")

                # 予約分を戻す
                session.execute(
                    self.users_table.update()
                    .where(self.users_table.c.id == user_id)
                    .values(reserved=user.reserved - tx.amount)
                )

                session.execute(
                    self.balance_transactions_table.update()
                    .where(self.balance_transactions_table.c.id == transaction_id)
                    .values(status="cancelled")
                )

                session.commit()
                logger.info(
                    f"Cancelled balance for user {user_id}, tx {transaction_id}"
                )
                return True
        except Exception:
            logger.exception("Error cancelling balance")
            raise
