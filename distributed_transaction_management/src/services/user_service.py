# src/services/user_service.py
from sqlalchemy import create_engine, Column, Integer, String, Decimal, DateTime, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserService:
    """ユーザー残高管理サービス"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # テーブル定義
        self.metadata = MetaData()
        self.users_table = Table(
            'users',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('username', String(80), unique=True, nullable=False),
            Column('balance', Decimal(10, 2), nullable=False, default=0.00),
            Column('reserved_balance', Decimal(10, 2), nullable=False, default=0.00),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.reservations_table = Table(
            'balance_reservations',
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('amount', Decimal(10, 2), nullable=False),
            Column('status', String(20), nullable=False, default='reserved'),
            Column('transaction_id', String(36), nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.metadata.create_all(self.engine)
        self._init_sample_data()
    
    def _init_sample_data(self):
        """サンプルデータを作成"""
        with self.SessionLocal() as session:
            # 既存データチェック
            existing_users = session.execute(self.users_table.select()).fetchall()
            if len(existing_users) == 0:
                # サンプルユーザー作成
                users_data = [
                    {'username': 'alice', 'balance': 1000.00},
                    {'username': 'bob', 'balance': 500.00},
                    {'username': 'charlie', 'balance': 2000.00}
                ]
                for user_data in users_data:
                    session.execute(self.users_table.insert().values(**user_data))
                session.commit()
                logger.info("Sample users created")
    
    def reserve_balance(self, user_id: int, amount: float, transaction_id: str) -> bool:
        """残高を予約（TCC Try phase）"""
        try:
            with self.SessionLocal() as session:
                # 既存の予約をチェック（冪等性）
                existing_reservation = session.execute(
                    self.reservations_table.select().where(
                        (self.reservations_table.c.user_id == user_id) &
                        (self.reservations_table.c.transaction_id == transaction_id)
                    )
                ).first()
                
                if existing_reservation:
                    if existing_reservation.status == 'reserved':
                        logger.info(f"Balance already reserved for user {user_id}, transaction {transaction_id}")
                        return True
                    else:
                        raise Exception(f"Reservation exists with status: {existing_reservation.status}")
                
                # ユーザー情報取得
                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                
                if not user:
                    raise Exception("User not found")
                
                # 残高チェック
                available_balance = user.balance - user.reserved_balance
                if available_balance < amount:
                    raise Exception("Insufficient balance")
                
                # 残高予約
                reservation_data = {
                    'id': transaction_id,
                    'user_id': user_id,
                    'amount': amount,
                    'status': 'reserved',
                    'transaction_id': transaction_id
                }
                session.execute(self.reservations_table.insert().values(**reservation_data))
                
                # 予約残高更新
                session.execute(
                    self.users_table.update().where(
                        self.users_table.c.id == user_id
                    ).values(reserved_balance=user.reserved_balance + amount)
                )
                
                session.commit()
                logger.info(f"Reserved {amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error reserving balance: {str(e)}")
            raise
    
    def confirm_balance(self, user_id: int, transaction_id: str) -> bool:
        """残高予約を確定（TCC Confirm phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約情報取得
                reservation = session.execute(
                    self.reservations_table.select().where(
                        (self.reservations_table.c.user_id == user_id) &
                        (self.reservations_table.c.transaction_id == transaction_id) &
                        (self.reservations_table.c.status == 'reserved')
                    )
                ).first()
                
                if not reservation:
                    # 既に確定済みかチェック
                    confirmed = session.execute(
                        self.reservations_table.select().where(
                            (self.reservations_table.c.user_id == user_id) &
                            (self.reservations_table.c.transaction_id == transaction_id) &
                            (self.reservations_table.c.status == 'confirmed')
                        )
                    ).first()
                    
                    if confirmed:
                        logger.info(f"Balance already confirmed for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No reservation found to confirm")
                
                # ユーザー情報取得
                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                
                # 残高から差し引き、予約残高から削除
                session.execute(
                    self.users_table.update().where(
                        self.users_table.c.id == user_id
                    ).values(
                        balance=user.balance - reservation.amount,
                        reserved_balance=user.reserved_balance - reservation.amount
                    )
                )
                
                # 予約ステータス更新
                session.execute(
                    self.reservations_table.update().where(
                        self.reservations_table.c.id == reservation.id
                    ).values(status='confirmed')
                )
                
                session.commit()
                logger.info(f"Confirmed {reservation.amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error confirming balance: {str(e)}")
            raise
    
    def cancel_balance(self, user_id: int, transaction_id: str) -> bool:
        """残高予約をキャンセル（TCC Cancel phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約情報取得
                reservation = session.execute(
                    self.reservations_table.select().where(
                        (self.reservations_table.c.user_id == user_id) &
                        (self.reservations_table.c.transaction_id == transaction_id) &
                        (self.reservations_table.c.status == 'reserved')
                    )
                ).first()
                
                if not reservation:
                    # 既にキャンセル済みかチェック
                    cancelled = session.execute(
                        self.reservations_table.select().where(
                            (self.reservations_table.c.user_id == user_id) &
                            (self.reservations_table.c.transaction_id == transaction_id) &
                            (self.reservations_table.c.status == 'cancelled')
                        )
                    ).first()
                    
                    if cancelled:
                        logger.info(f"Balance already cancelled for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No reservation found to cancel")
                
                # ユーザー情報取得
                user = session.execute(
                    self.users_table.select().where(self.users_table.c.id == user_id)
                ).first()
                
                # 予約残高から削除
                session.execute(
                    self.users_table.update().where(
                        self.users_table.c.id == user_id
                    ).values(reserved_balance=user.reserved_balance - reservation.amount)
                )
                
                # 予約ステータス更新
                session.execute(
                    self.reservations_table.update().where(
                        self.reservations_table.c.id == reservation.id
                    ).values(status='cancelled')
                )
                
                session.commit()
                logger.info(f"Cancelled {reservation.amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling balance: {str(e)}")
            raise


# src/services/payment_service.py
from sqlalchemy import create_engine, Column, Integer, String, Decimal, DateTime, Text, Boolean, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    """決済処理サービス"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # テーブル定義
        self.metadata = MetaData()
        self.payment_methods_table = Table(
            'payment_methods',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('user_id', Integer, nullable=False),
            Column('method_type', String(50), nullable=False),
            Column('method_details', Text),
            Column('is_active', Boolean, default=True),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.payment_transactions_table = Table(
            'payment_transactions',
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('payment_method_id', Integer, nullable=False),
            Column('amount', Decimal(10, 2), nullable=False),
            Column('status', String(20), nullable=False, default='reserved'),
            Column('transaction_id', String(36), nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.metadata.create_all(self.engine)
        self._init_sample_data()
    
    def _init_sample_data(self):
        """サンプルデータを作成"""
        with self.SessionLocal() as session:
            # 既存データチェック
            existing_methods = session.execute(self.payment_methods_table.select()).fetchall()
            if len(existing_methods) == 0:
                # サンプル決済方法作成
                payment_methods_data = [
                    {'user_id': 1, 'method_type': 'credit_card', 'method_details': '{"last4": "1234", "brand": "visa"}'},
                    {'user_id': 2, 'method_type': 'credit_card', 'method_details': '{"last4": "5678", "brand": "mastercard"}'},
                    {'user_id': 3, 'method_type': 'paypal', 'method_details': '{"email": "charlie@example.com"}'}
                ]
                for method_data in payment_methods_data:
                    session.execute(self.payment_methods_table.insert().values(**method_data))
                session.commit()
                logger.info("Sample payment methods created")
    
    def reserve_payment(self, user_id: int, payment_method_id: int, amount: float, transaction_id: str) -> bool:
        """決済を予約（TCC Try phase）"""
        try:
            with self.SessionLocal() as session:
                # 既存の予約をチェック（冪等性）
                existing_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id) &
                        (self.payment_transactions_table.c.transaction_id == transaction_id)
                    )
                ).first()
                
                if existing_transaction:
                    if existing_transaction.status == 'reserved':
                        logger.info(f"Payment already reserved for user {user_id}, transaction {transaction_id}")
                        return True
                    else:
                        raise Exception(f"Payment transaction exists with status: {existing_transaction.status}")
                
                # 決済方法の検証
                payment_method = session.execute(
                    self.payment_methods_table.select().where(
                        (self.payment_methods_table.c.id == payment_method_id) &
                        (self.payment_methods_table.c.user_id == user_id) &
                        (self.payment_methods_table.c.is_active == True)
                    )
                ).first()
                
                if not payment_method:
                    raise Exception("Invalid payment method")
                
                if amount <= 0:
                    raise Exception("Invalid amount")
                
                # 決済予約作成
                transaction_data = {
                    'id': transaction_id,
                    'user_id': user_id,
                    'payment_method_id': payment_method_id,
                    'amount': amount,
                    'status': 'reserved',
                    'transaction_id': transaction_id
                }
                session.execute(self.payment_transactions_table.insert().values(**transaction_data))
                
                session.commit()
                logger.info(f"Reserved payment {amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error reserving payment: {str(e)}")
            raise
    
    def charge_payment(self, user_id: int, transaction_id: str) -> bool:
        """決済を実行（TCC Confirm phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約済み決済取得
                payment_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id) &
                        (self.payment_transactions_table.c.transaction_id == transaction_id) &
                        (self.payment_transactions_table.c.status == 'reserved')
                    )
                ).first()
                
                if not payment_transaction:
                    # 既に実行済みかチェック
                    charged = session.execute(
                        self.payment_transactions_table.select().where(
                            (self.payment_transactions_table.c.user_id == user_id) &
                            (self.payment_transactions_table.c.transaction_id == transaction_id) &
                            (self.payment_transactions_table.c.status == 'charged')
                        )
                    ).first()
                    
                    if charged:
                        logger.info(f"Payment already charged for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No payment reservation found to charge")
                
                # 実際の決済処理をシミュレート（外部API呼び出しをシミュレート）
                # 実装では決済プロバイダーのAPIを呼び出す
                
                # 決済ステータス更新
                session.execute(
                    self.payment_transactions_table.update().where(
                        self.payment_transactions_table.c.id == payment_transaction.id
                    ).values(status='charged')
                )
                
                session.commit()
                logger.info(f"Charged payment {payment_transaction.amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error charging payment: {str(e)}")
            raise
    
    def cancel_payment(self, user_id: int, transaction_id: str) -> bool:
        """決済予約をキャンセル（TCC Cancel phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約済み決済取得
                payment_transaction = session.execute(
                    self.payment_transactions_table.select().where(
                        (self.payment_transactions_table.c.user_id == user_id) &
                        (self.payment_transactions_table.c.transaction_id == transaction_id) &
                        (self.payment_transactions_table.c.status == 'reserved')
                    )
                ).first()
                
                if not payment_transaction:
                    # 既にキャンセル済みかチェック
                    cancelled = session.execute(
                        self.payment_transactions_table.select().where(
                            (self.payment_transactions_table.c.user_id == user_id) &
                            (self.payment_transactions_table.c.transaction_id == transaction_id) &
                            (self.payment_transactions_table.c.status == 'cancelled')
                        )
                    ).first()
                    
                    if cancelled:
                        logger.info(f"Payment already cancelled for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No payment reservation found to cancel")
                
                # 決済予約キャンセル
                session.execute(
                    self.payment_transactions_table.update().where(
                        self.payment_transactions_table.c.id == payment_transaction.id
                    ).values(status='cancelled')
                )
                
                session.commit()
                logger.info(f"Cancelled payment {payment_transaction.amount} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling payment: {str(e)}")
            raise


# src/services/order_service.py
from sqlalchemy import create_engine, Column, Integer, String, Decimal, DateTime, MetaData, Table
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OrderService:
    """注文処理サービス"""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # テーブル定義
        self.metadata = MetaData()
        self.products_table = Table(
            'products',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('name', String(100), nullable=False),
            Column('price', Decimal(10, 2), nullable=False),
            Column('stock_quantity', Integer, nullable=False, default=0),
            Column('reserved_quantity', Integer, nullable=False, default=0),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.orders_table = Table(
            'orders',
            self.metadata,
            Column('id', String(36), primary_key=True),
            Column('user_id', Integer, nullable=False),
            Column('product_id', Integer, nullable=False),
            Column('quantity', Integer, nullable=False),
            Column('total_amount', Decimal(10, 2), nullable=False),
            Column('status', String(20), nullable=False, default='reserved'),
            Column('transaction_id', String(36), nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        self.metadata.create_all(self.engine)
        self._init_sample_data()
    
    def _init_sample_data(self):
        """サンプルデータを作成"""
        with self.SessionLocal() as session:
            # 既存データチェック
            existing_products = session.execute(self.products_table.select()).fetchall()
            if len(existing_products) == 0:
                # サンプル商品作成
                products_data = [
                    {'name': 'Bitcoin', 'price': 50000.00, 'stock_quantity': 10},
                    {'name': 'Ethereum', 'price': 3000.00, 'stock_quantity': 20},
                    {'name': 'Litecoin', 'price': 100.00, 'stock_quantity': 50}
                ]
                for product_data in products_data:
                    session.execute(self.products_table.insert().values(**product_data))
                session.commit()
                logger.info("Sample products created")
    
    def reserve_product(self, user_id: int, product_id: int, quantity: int, transaction_id: str) -> bool:
        """商品在庫を予約（TCC Try phase）"""
        try:
            with self.SessionLocal() as session:
                # 既存の予約をチェック（冪等性）
                existing_order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id) &
                        (self.orders_table.c.transaction_id == transaction_id)
                    )
                ).first()
                
                if existing_order:
                    if existing_order.status == 'reserved':
                        logger.info(f"Product already reserved for user {user_id}, transaction {transaction_id}")
                        return True
                    else:
                        raise Exception(f"Order exists with status: {existing_order.status}")
                
                # 商品情報取得
                product = session.execute(
                    self.products_table.select().where(self.products_table.c.id == product_id)
                ).first()
                
                if not product:
                    raise Exception("Product not found")
                
                # 在庫チェック
                available_quantity = product.stock_quantity - product.reserved_quantity
                if available_quantity < quantity:
                    raise Exception("Out of stock")
                
                # 注文作成
                total_amount = product.price * quantity
                order_data = {
                    'id': transaction_id,
                    'user_id': user_id,
                    'product_id': product_id,
                    'quantity': quantity,
                    'total_amount': total_amount,
                    'status': 'reserved',
                    'transaction_id': transaction_id
                }
                session.execute(self.orders_table.insert().values(**order_data))
                
                # 予約在庫更新
                session.execute(
                    self.products_table.update().where(
                        self.products_table.c.id == product_id
                    ).values(reserved_quantity=product.reserved_quantity + quantity)
                )
                
                session.commit()
                logger.info(f"Reserved {quantity} of product {product_id} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error reserving product: {str(e)}")
            raise
    
    def confirm_order(self, user_id: int, transaction_id: str) -> bool:
        """注文を確定（TCC Confirm phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約済み注文取得
                order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id) &
                        (self.orders_table.c.transaction_id == transaction_id) &
                        (self.orders_table.c.status == 'reserved')
                    )
                ).first()
                
                if not order:
                    # 既に確定済みかチェック
                    confirmed = session.execute(
                        self.orders_table.select().where(
                            (self.orders_table.c.user_id == user_id) &
                            (self.orders_table.c.transaction_id == transaction_id) &
                            (self.orders_table.c.status == 'confirmed')
                        )
                    ).first()
                    
                    if confirmed:
                        logger.info(f"Order already confirmed for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No order reservation found to confirm")
                
                # 商品情報取得
                product = session.execute(
                    self.products_table.select().where(self.products_table.c.id == order.product_id)
                ).first()
                
                # 在庫から差し引き、予約在庫から削除
                session.execute(
                    self.products_table.update().where(
                        self.products_table.c.id == order.product_id
                    ).values(
                        stock_quantity=product.stock_quantity - order.quantity,
                        reserved_quantity=product.reserved_quantity - order.quantity
                    )
                )
                
                # 注文ステータス更新
                session.execute(
                    self.orders_table.update().where(
                        self.orders_table.c.id == order.id
                    ).values(status='confirmed')
                )
                
                session.commit()
                logger.info(f"Confirmed order {order.quantity} of product {order.product_id} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error confirming order: {str(e)}")
            raise
    
    def cancel_order(self, user_id: int, transaction_id: str) -> bool:
        """注文予約をキャンセル（TCC Cancel phase）"""
        try:
            with self.SessionLocal() as session:
                # 予約済み注文取得
                order = session.execute(
                    self.orders_table.select().where(
                        (self.orders_table.c.user_id == user_id) &
                        (self.orders_table.c.transaction_id == transaction_id) &
                        (self.orders_table.c.status == 'reserved')
                    )
                ).first()
                
                if not order:
                    # 既にキャンセル済みかチェック
                    cancelled = session.execute(
                        self.orders_table.select().where(
                            (self.orders_table.c.user_id == user_id) &
                            (self.orders_table.c.transaction_id == transaction_id) &
                            (self.orders_table.c.status == 'cancelled')
                        )
                    ).first()
                    
                    if cancelled:
                        logger.info(f"Order already cancelled for user {user_id}, transaction {transaction_id}")
                        return True
                    
                    raise Exception("No order reservation found to cancel")
                
                # 商品情報取得
                product = session.execute(
                    self.products_table.select().where(self.products_table.c.id == order.product_id)
                ).first()
                
                # 予約在庫から削除
                session.execute(
                    self.products_table.update().where(
                        self.products_table.c.id == order.product_id
                    ).values(reserved_quantity=product.reserved_quantity - order.quantity)
                )
                
                # 注文ステータス更新
                session.execute(
                    self.orders_table.update().where(
                        self.orders_table.c.id == order.id
                    ).values(status='cancelled')
                )
                
                session.commit()
                logger.info(f"Cancelled order {order.quantity} of product {order.product_id} for user {user_id}, transaction {transaction_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            raise