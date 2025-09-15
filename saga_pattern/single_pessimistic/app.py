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

from models import Base, Order, OrderItem, Inventory, Book, Event

app = FastAPI()

# Database connection
DB_USER = os.getenv("MYSQL_USER", "cloudmart_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "cloudmart_pass")
DB_HOST = os.getenv("MYSQL_HOST", "db")
DB_NAME = os.getenv("MYSQL_DATABASE", "cloudmart_saga")
CONN_STR = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = sqlalchemy.create_engine(CONN_STR)
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


@app.post("/orders")
def create_order(payload: OrderPayload, db: Session = Depends(get_db)):
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    total_amount = 0

    # Retry logic for deadlocks
    for attempt in range(3):
        try:
            with db.begin_nested():  # Use nested transaction
                # 1. Calculate total amount and lock inventory items
                order_items_to_create = []
                for item in payload.items:
                    book = db.query(Book).filter(Book.book_id == item.book_id).first()
                    if not book:
                        raise HTTPException(
                            status_code=404, detail=f"Book {item.book_id} not found"
                        )

                    inventory_item = (
                        db.query(Inventory)
                        .filter(Inventory.book_id == item.book_id)
                        .with_for_update()
                        .one()
                    )

                    if inventory_item.available_stock < item.quantity:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Not enough stock for book {item.book_id}",
                        )

                    inventory_item.available_stock -= item.quantity

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
                if total_amount > 5000:  # Simulate payment failure for high amounts
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
            if "deadlock" in str(e).lower():
                db.rollback()
                if attempt < 2:
                    time.sleep(random.uniform(0.1, 0.5))
                    continue
                else:
                    raise HTTPException(
                        status_code=503, detail="Service busy, please try again later."
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
