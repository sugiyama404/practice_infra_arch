from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add shared module to path
sys.path.append("/app")

from shared.models import Order, OrderItem, OrderStatus, get_db_session
from shared.config import settings, get_database_url
from shared.utils import setup_logging, create_event, json_dumps, generate_order_id

# Setup logging
logger = setup_logging("order-service")

# FastAPI app
app = FastAPI(title="Order Service", version="1.0.0")

# Database setup
from sqlalchemy import create_engine

engine = create_engine(get_database_url())

# Redis setup
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    decode_responses=True,
)


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@app.post("/orders")
async def create_order(order_data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Create a new order and initiate the order processing saga
    by publishing an 'OrderCreated' event.
    """
    try:
        # Validate required fields
        required_fields = ["customer_id", "items"]
        for field in required_fields:
            if field not in order_data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        # Generate order ID
        order_id = generate_order_id()

        # Calculate total amount
        total_amount = 0
        order_items = []

        for item in order_data["items"]:
            # Get book price from database (simplified - in real app, call inventory service)
            book_id = item["book_id"]
            quantity = item["quantity"]

            # For demo, use fixed price - in real app, get from inventory service
            unit_price = 3500.00  # Fixed price for demo
            total_amount += unit_price * quantity

            order_items.append(
                {"book_id": book_id, "quantity": quantity, "unit_price": unit_price}
            )

        # Create order in database
        order = Order(
            order_id=order_id,
            customer_id=order_data["customer_id"],
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            notes=order_data.get("notes"),
        )
        db.add(order)

        # Create order items
        for item in order_items:
            order_item = OrderItem(
                order_id=order_id,
                book_id=item["book_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
            )
            db.add(order_item)

        db.commit()

        # Publish OrderCreated event
        event = create_event(
            event_type="OrderCreated",
            aggregate_id=order_id,
            payload={
                "order_id": order_id,
                "customer_id": order_data["customer_id"],
                "items": order_items,
                "total_amount": total_amount,
            },
        )

        event_channel = f"{settings.event_channel_prefix}.order"
        redis_client.publish(event_channel, json.dumps(event))

        logger.info(f"Order created and event published: {order_id}")

        return {
            "order_id": order_id,
            "status": "created",
            "total_amount": total_amount,
            "message": "Order created successfully",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{order_id}")
async def get_order(order_id: str, db: Session = Depends(get_db)):
    """Get order details"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "status": order.status.value,
        "total_amount": order.total_amount,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


@app.put("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """Cancel order and publish OrderCancelled event"""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatus.CANCELLED:
        return {"message": "Order already cancelled"}

    # Update order status
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = datetime.utcnow()
    db.commit()

    # Publish OrderCancelled event with item details for compensation
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    items_payload = [
        {"book_id": item.book_id, "quantity": item.quantity} for item in order_items
    ]

    event = create_event(
        event_type="OrderCancelled",
        aggregate_id=order_id,
        payload={
            "order_id": order_id,
            "reason": "User cancelled",
            "items": items_payload,
        },
    )

    event_channel = f"{settings.event_channel_prefix}.order"
    redis_client.publish(event_channel, json.dumps(event))

    logger.info(f"Order cancelled: {order_id}")

    return {"message": "Order cancelled successfully"}


@app.put("/orders/{order_id}/confirm")
async def confirm_order(order_id: str, db: Session = Depends(get_db)):
    """Confirm an order and update its status"""
    try:
        # Get order
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400, detail=f"Order is already {order.status}"
            )

        # Update order status and confirmed timestamp
        order.status = OrderStatus.CONFIRMED
        order.confirmed_at = datetime.now()
        order.updated_at = datetime.now()

        db.commit()

        # Publish order confirmed event
        event_data = {
            "order_id": order_id,
            "customer_id": order.customer_id,
            "total_amount": float(order.total_amount),
            "confirmed_at": order.confirmed_at.isoformat(),
        }

        # Save OrderConfirmed event to database
        create_event(
            event_type="OrderConfirmed",
            aggregate_id=order_id,
            payload=event_data,
            db_session=db,
        )

        return {"message": "Order confirmed successfully", "order_id": order_id}

    except HTTPException:
        # Propagate HTTP errors as-is
        raise
    except Exception as e:
        logger.error(f"Error confirming order {order_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "order-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
