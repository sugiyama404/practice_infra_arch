from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.models import Inventory, OrderStatus
from shared.config import settings, get_database_url
from shared.utils import setup_logging, create_event

# Setup logging
logger = setup_logging("inventory-service")

# FastAPI app
app = FastAPI(title="Inventory Service", version="1.0.0")

# Database setup
from sqlalchemy import create_engine
from shared.models import get_db_session

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


# Subscribe to OrderCreated events
def handle_order_created(event_data: Dict[str, Any], db: Session):
    """Handle OrderCreated event - reserve stock"""
    order_id = event_data["aggregate_id"]
    items = event_data["payload"]["items"]

    logger.info(f"Processing OrderCreated event for order: {order_id}")

    try:
        # Check and reserve stock for each item
        for item in items:
            book_id = item["book_id"]
            quantity = item["quantity"]

            # Get inventory
            inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
            if not inventory:
                raise Exception(f"Book not found: {book_id}")

            if inventory.available_stock < quantity:
                # Publish StockUnavailable event
                event = create_event(
                    event_type="StockUnavailable",
                    aggregate_id=order_id,
                    payload={
                        "order_id": order_id,
                        "book_id": book_id,
                        "requested_quantity": quantity,
                        "available_stock": inventory.available_stock,
                    },
                    db_session=db,
                )
                event_channel = f"{settings.event_channel_prefix}.inventory"
                redis_client.publish(event_channel, json.dumps(event))
                logger.warning(
                    f"Insufficient stock for book {book_id}: requested {quantity}, available {inventory.available_stock}"
                )
                return

        # All items available - reserve stock
        for item in items:
            book_id = item["book_id"]
            quantity = item["quantity"]

            inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
            inventory.available_stock -= quantity
            inventory.reserved_stock += quantity
            inventory.updated_at = datetime.utcnow()

        db.commit()

        # Publish StockReserved event
        event = create_event(
            event_type="StockReserved",
            aggregate_id=order_id,
            payload={"order_id": order_id, "items": items},
            db_session=db,
        )
        event_channel = f"{settings.event_channel_prefix}.inventory"
        redis_client.publish(event_channel, json.dumps(event))

        logger.info(f"Stock reserved for order: {order_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing OrderCreated event: {str(e)}")


def handle_order_cancelled(event_data: Dict[str, Any], db: Session):
    """Handle OrderCancelled event - release reserved stock"""
    order_id = event_data["aggregate_id"]

    logger.info(f"Processing OrderCancelled event for order: {order_id}")

    try:
        # Get order items from database (simplified - in real app, query order_items)
        # For demo, assume we have the items in the event or query from DB
        # Here we'll simulate releasing stock

        # In real implementation, you'd query order_items table
        # For demo, we'll just log the event
        logger.info(f"Stock released for cancelled order: {order_id}")

        # Publish StockReleased event
        event = create_event(
            event_type="StockReleased",
            aggregate_id=order_id,
            payload={"order_id": order_id, "reason": "Order cancelled"},
            db_session=db,
        )
        event_channel = f"{settings.event_channel_prefix}.inventory"
        redis_client.publish(event_channel, json.dumps(event))

    except Exception as e:
        logger.error(f"Error processing OrderCancelled event: {str(e)}")


@app.post("/inventory/reserve")
async def reserve_stock(
    reservation_data: Dict[str, Any], db: Session = Depends(get_db)
):
    """Manually reserve stock (for testing)"""
    try:
        # Handle both direct payload and command structure
        if "payload" in reservation_data:
            # Command structure from saga orchestrator
            payload = reservation_data["payload"]
            book_id = payload.get("product_id") or payload.get("book_id")
            quantity = payload["quantity"]
        else:
            # Direct payload - check if it's already flattened
            book_id = reservation_data.get("product_id") or reservation_data.get(
                "book_id"
            )
            quantity = reservation_data["quantity"]

        inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
        if not inventory:
            raise HTTPException(status_code=404, detail="Book not found")

        if inventory.available_stock < quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        inventory.available_stock -= quantity
        inventory.reserved_stock += quantity
        inventory.updated_at = datetime.utcnow()
        db.commit()

        return {"message": "Stock reserved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inventory/release")
async def release_stock(release_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Release reserved stock (compensation)"""
    try:
        # Handle both direct payload and command structure
        if "payload" in release_data:
            # Command structure from saga orchestrator
            payload = release_data["payload"]
            book_id = payload.get("product_id") or payload.get("book_id")
            quantity = payload["quantity"]
        else:
            # Direct payload - check if it's already flattened
            book_id = release_data.get("product_id") or release_data.get("book_id")
            quantity = release_data["quantity"]

        inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
        if not inventory:
            raise HTTPException(status_code=404, detail="Book not found")

        if inventory.reserved_stock >= quantity:
            inventory.reserved_stock -= quantity
            inventory.available_stock += quantity
            inventory.updated_at = datetime.utcnow()
            db.commit()
            return {"message": "Stock released successfully"}
        else:
            # Already released or insufficient reserved stock
            return {"message": "No stock to release or already released"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/inventory/{book_id}")
async def get_inventory(book_id: str, db: Session = Depends(get_db)):
    """Get inventory details"""
    inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    return {
        "book_id": inventory.book_id,
        "available_stock": inventory.available_stock,
        "reserved_stock": inventory.reserved_stock,
        "total_stock": inventory.available_stock + inventory.reserved_stock,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "inventory-service"}


# Event listener
@app.on_event("startup")
async def startup_event():
    """Subscribe to events on startup"""
    import threading

    def event_listener():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"{settings.event_channel_prefix}.order")

        logger.info("Inventory service listening for events...")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    event_type = event_data["event_type"]

                    db = Session(engine)

                    if event_type == "OrderCreated":
                        handle_order_created(event_data, db)
                    elif event_type == "OrderCancelled":
                        handle_order_cancelled(event_data, db)

                    db.close()

                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    thread = threading.Thread(target=event_listener, daemon=True)
    thread.start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
