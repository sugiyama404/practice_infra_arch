from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from typing import Dict, Any
import sys
import os
from contextlib import asynccontextmanager

# Add shared module to path
sys.path.append("/app")

from shared.models import Inventory, OrderStatus, get_db_session, Event, EventType
from shared.config import settings, get_database_url
from shared.utils import setup_logging, create_event

# Setup logging
logger = setup_logging("inventory-service")


# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting inventory service...")

    # Start event listener
    event_thread = start_event_listener()
    logger.info(f"Event listener thread started: {event_thread}")

    yield

    # Shutdown
    logger.info("Shutting down inventory service...")


app = FastAPI(title="Inventory Service", version="1.0.0", lifespan=lifespan)

# Database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(get_database_url())
Session = sessionmaker(bind=engine)

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
        )
        event_channel = f"{settings.event_channel_prefix}.inventory"
        redis_client.publish(event_channel, json.dumps(event))

        logger.info(f"Stock reserved for order: {order_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing OrderCreated event: {str(e)}")


def handle_order_cancelled(event_data: Dict[str, Any], db: Session):
    """
    Handle OrderCancelled event - release reserved stock (Compensating Action).
    This is a compensating action for the 'reserve_stock' step.
    """
    order_id = event_data["aggregate_id"]
    payload = event_data.get("payload", {})
    items_to_release = payload.get("items", [])

    logger.info(f"Processing OrderCancelled event for order: {order_id}")

    try:
        # If items are not in the event, we would need to fetch them.
        # This requires the order_id to be linked to order_items.
        # For this demo, we assume the compensating event contains necessary data.
        if not items_to_release:
            logger.warning(
                f"No items found in OrderCancelled event for order {order_id}. Cannot release stock."
            )
            # In a real-world scenario, you might query the order service or a shared DB
            # to get the items associated with the order.
            return

        for item in items_to_release:
            book_id = item.get("book_id")
            quantity = item.get("quantity")

            if not book_id or not quantity:
                continue

            inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
            if inventory and inventory.reserved_stock >= quantity:
                inventory.reserved_stock -= quantity
                inventory.available_stock += quantity
                inventory.updated_at = datetime.utcnow()
                logger.info(
                    f"Released {quantity} of book {book_id} back to available stock."
                )
            else:
                logger.warning(
                    f"Could not release stock for book {book_id}. Reserved stock might be insufficient or item not found."
                )

        db.commit()

        # Publish StockReleased event
        event = create_event(
            event_type="StockReleased",
            aggregate_id=order_id,
            payload={"order_id": order_id, "reason": "Order cancelled"},
        )
        event_channel = f"{settings.event_channel_prefix}.inventory"
        redis_client.publish(event_channel, json.dumps(event))
        logger.info(f"Stock released for cancelled order: {order_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing OrderCancelled event: {str(e)}")


# Event listener (simplified - in production, use proper message queue consumer)
def start_event_listener():
    """Start event listener in separate thread"""
    import threading

    def event_listener():
        logger.info("Starting event listener thread...")
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"{settings.event_channel_prefix}.order")

        logger.info("Inventory service listening for events...")

        for message in pubsub.listen():
            logger.info(f"Received raw message: {message}")
            if message["type"] == "message":
                logger.info("Processing message...")
                try:
                    event_data = json.loads(message["data"])
                    event_type = event_data["event_type"]

                    logger.info(
                        f"Processing event: {event_type} for order: {event_data.get('aggregate_id', 'unknown')}"
                    )

                    # Get database session
                    db = Session()

                    # Save event to database for analysis
                    logger.info(
                        f"Attempting to save event: {event_type} with ID: {event_data['event_id']}"
                    )
                    try:
                        # Convert camelCase to UPPER_SNAKE_CASE
                        def camel_to_snake(name):
                            import re

                            name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
                            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).upper()

                        event_type_enum = camel_to_snake(event_type)
                        logger.info(
                            f"Converted event type: {event_type} -> {event_type_enum}"
                        )

                        event_record = Event(
                            event_id=event_data["event_id"],
                            event_type=EventType(event_type_enum),
                            aggregate_id=event_data["aggregate_id"],
                            aggregate_type="order",
                            version=event_data.get("version", 1),
                            event_data=event_data["payload"],
                            # event_metadata argument removed
                            processed_at=datetime.utcnow(),
                        )
                        logger.info("Created event record object")
                        db.add(event_record)
                        logger.info("Added event record to session")
                        db.commit()
                        logger.info(
                            f"Event saved to database successfully: {event_type} -> {event_type_enum} - {event_data['event_id']}"
                        )
                    except Exception as save_error:
                        logger.error(f"Failed to save event to database: {save_error}")
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")
                        db.rollback()

                    # Process the event
                    try:
                        if event_type == "OrderCreated":
                            handle_order_created(event_data, db)
                        elif event_type == "OrderCancelled":
                            handle_order_cancelled(event_data, db)
                    except Exception as process_error:
                        logger.error(f"Failed to process event: {process_error}")
                        db.rollback()

                    db.close()

                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    # Start event listener in background thread
    thread = threading.Thread(target=event_listener, daemon=True)
    thread.start()
    return thread


app = FastAPI(title="Inventory Service", version="1.0.0", lifespan=lifespan)


@app.post("/inventory/reserve")
async def reserve_stock(
    reservation_data: Dict[str, Any], db: Session = Depends(get_db)
):
    """Manually reserve stock (for testing)"""
    try:
        book_id = reservation_data["book_id"]
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

        # Publish StockReserved event
        order_id = reservation_data.get("order_id")
        event_data = {
            "order_id": order_id,
            "book_id": book_id,
            "quantity": quantity,
            "reserved_at": datetime.utcnow().isoformat(),
        }
        event = create_event(
            event_type="StockReserved",
            aggregate_id=order_id,
            payload=event_data,
            db_session=db,
        )
        event_channel = f"{settings.event_channel_prefix}.inventory"
        redis_client.publish(event_channel, json.dumps(event))

        return {"message": "Stock reserved successfully"}

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.app:app", host="0.0.0.0", port=8002, reload=True)
