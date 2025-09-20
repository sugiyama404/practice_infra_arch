from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError
import sqlalchemy
import os
import uuid
from datetime import datetime
import time
import random
import logging

from models import Base, Order, OrderItem, Inventory, Book, Event

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Database connection
DB_USER = os.getenv("MYSQL_USER", "cloudmart_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "cloudmart_pass")
DB_HOST = os.getenv("MYSQL_HOST", "db")
DB_NAME = os.getenv("MYSQL_DATABASE", "cloudmart_saga")
CONN_STR = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create engine with robust connection pool settings to avoid stale connections
# - pool_pre_ping: validate connections before using them, recycling dead ones
# - pool_recycle: proactively recycle connections before MySQL wait_timeout
# - pool_size/max_overflow: small defaults suitable for a demo app
engine = sqlalchemy.create_engine(
    CONN_STR,
    pool_pre_ping=True,
    pool_recycle=1800,  # recycle every 30 minutes
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Item(BaseModel):
    book_id: str
    quantity: int


class OrderPayload(BaseModel):
    customer_id: str
    items: list[Item]


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/books")
def list_books(db: Session = Depends(get_db)):
    books = (
        db.query(Book.book_id, Book.title, Book.price, Inventory.available_stock)
        .join(Inventory, Inventory.book_id == Book.book_id)
        .all()
    )
    return [
        {
            "book_id": b[0],
            "title": b[1],
            "price": float(b[2]) if b[2] is not None else None,
            "available_stock": b[3],
        }
        for b in books
    ]


@app.post("/orders")
def create_order(payload: OrderPayload, db: Session = Depends(get_db)):
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    total_amount = 0

    logger.info(f"Creating order {order_id} for customer {payload.customer_id}")

    # Retry logic for transient errors (deadlocks, lost connections)
    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        try:
            with db.begin_nested():  # Use nested transaction
                logger.info(f"Attempt {attempt + 1} for order {order_id}")

                # 1. Calculate total amount and lock inventory items
                order_items_to_create = []
                for item in payload.items:
                    logger.info(
                        f"Processing item: {item.book_id}, quantity: {item.quantity}"
                    )

                    book = db.query(Book).filter(Book.book_id == item.book_id).first()
                    if not book:
                        logger.error(f"Book {item.book_id} not found")
                        raise HTTPException(
                            status_code=400, detail=f"Book {item.book_id} not found"
                        )

                    inventory_item = (
                        db.query(Inventory)
                        .filter(Inventory.book_id == item.book_id)
                        .with_for_update()
                        .one()
                    )

                    if inventory_item.available_stock < item.quantity:
                        logger.warning(
                            f"Not enough stock for book {item.book_id}: available {inventory_item.available_stock}, requested {item.quantity}"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"Not enough stock for book {item.book_id}",
                        )

                    inventory_item.available_stock -= item.quantity
                    logger.info(
                        f"Updated stock for {item.book_id}: {inventory_item.available_stock + item.quantity} -> {inventory_item.available_stock}"
                    )

                    item_total = book.price * item.quantity
                    total_amount += item_total

                    order_items_to_create.append(
                        OrderItem(
                            order_id=order_id,
                            book_id=item.book_id,
                            quantity=item.quantity,
                            unit_price=book.price,
                        )
                    )

                # 2. Simulate payment (can fail)
                logger.info(f"Total amount for order {order_id}: {total_amount}")
                if total_amount > 5000:  # Simulate payment failure for high amounts
                    logger.warning(
                        f"Payment failed for order {order_id}: amount {total_amount} > 5000"
                    )
                    new_order = Order(
                        order_id=order_id,
                        customer_id=payload.customer_id,
                        status="FAILED",
                        total_amount=total_amount,
                        cancelled_at=datetime.utcnow(),
                    )
                    db.add(new_order)
                    db.add(
                        Event(
                            event_id=str(uuid.uuid4()),
                            aggregate_id=order_id,
                            aggregate_type="Order",
                            event_type="OrderCreationFailed",
                            event_data={"reason": "Payment failed"},
                        )
                    )
                    db.commit()
                    raise HTTPException(status_code=400, detail="Payment failed")

                # 3. Create order and items
                new_order = Order(
                    order_id=order_id,
                    customer_id=payload.customer_id,
                    status="CONFIRMED",
                    total_amount=total_amount,
                    confirmed_at=datetime.utcnow(),
                )
                db.add(new_order)
                db.add_all(order_items_to_create)

                db.add(
                    Event(
                        event_id=str(uuid.uuid4()),
                        aggregate_id=order_id,
                        aggregate_type="Order",
                        event_type="OrderCreated",
                        event_data=payload.dict(),
                    )
                )

            db.commit()
            return {"message": "Order created successfully", "order_id": order_id}

        except OperationalError as e:
            message = str(e).lower()
            # Handle common transient errors: deadlocks and lost connections
            if "deadlock" in message:
                db.rollback()
                if attempt < MAX_RETRIES - 1:
                    time.sleep(random.uniform(0.2, 0.8))
                    continue
                else:
                    raise HTTPException(
                        status_code=503, detail="Service busy, please try again later."
                    )
            # MySQL lost connection / server has gone away
            # pymysql error codes: 2013 (lost connection), 2006 (server has gone away)
            if (
                "2013" in message
                or "2006" in message
                or "lost connection" in message
                or "server has gone away" in message
            ):
                db.rollback()
                # Dispose the pool to force new connections on next attempt
                try:
                    engine.dispose()
                except Exception:
                    pass
                if attempt < MAX_RETRIES - 1:
                    time.sleep(random.uniform(0.2, 0.8))
                    continue
                else:
                    raise HTTPException(
                        status_code=503,
                        detail="Database connection issue, please try again later.",
                    )
            else:
                db.rollback()
                raise
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Internal server error")

    return {
        "message": "Failed to create order after multiple attempts",
        "order_id": order_id,
    }
