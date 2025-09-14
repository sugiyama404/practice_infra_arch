from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
import os
import random

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.models import Shipment, ShipmentStatus
from shared.config import settings, get_database_url
from shared.utils import setup_logging, create_event, generate_shipment_id

# Setup logging
logger = setup_logging("shipping-service")

# FastAPI app
app = FastAPI(title="Shipping Service", version="1.0.0")

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
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def simulate_shipping_arrangement() -> bool:
    """Simulate shipping arrangement - randomly succeed/fail for demo"""
    # For demo: 90% success rate
    return random.random() < 0.9


def handle_payment_completed_and_stock_reserved(
    event_data: Dict[str, Any], db: Session
):
    """Handle combined events - arrange shipping"""
    # This is a simplified version. In real implementation, you'd listen to both events
    # and only proceed when both are received
    order_id = event_data["aggregate_id"]

    logger.info(f"Arranging shipping for order: {order_id}")

    try:
        # Simulate shipping arrangement
        shipping_success = simulate_shipping_arrangement()

        if shipping_success:
            # Create shipment record
            shipment_id = generate_shipment_id()
            shipment = Shipment(
                shipment_id=shipment_id,
                order_id=order_id,
                carrier="Demo Shipping Co.",
                tracking_number=f"TRK{shipment_id[-8:]}",
                status=ShipmentStatus.ARRANGED,
                shipping_address={
                    "name": "Demo Customer",
                    "address": "123 Demo Street, Demo City, 12345",
                    "phone": "555-0123",
                },
                estimated_delivery=datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                ),  # Next day
                shipping_cost=500.00,
            )
            db.add(shipment)
            db.commit()

            # Publish ShippingArranged event
            event = create_event(
                event_type="ShippingArranged",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "shipment_id": shipment_id,
                    "tracking_number": shipment.tracking_number,
                    "carrier": shipment.carrier,
                    "estimated_delivery": shipment.estimated_delivery.isoformat(),
                },
            )
        else:
            # Shipping failed
            # Publish ShippingFailed event
            event = create_event(
                event_type="ShippingFailed",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "reason": "Shipping service unavailable",
                },
            )

        event_channel = f"{settings.event_channel_prefix}.shipping"
        redis_client.publish(event_channel, json.dumps(event))

        logger.info(
            f"Shipping {'arranged' if shipping_success else 'failed'} for order: {order_id}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error arranging shipping: {str(e)}")


def handle_order_cancelled(event_data: Dict[str, Any], db: Session):
    """Handle OrderCancelled event - cancel shipping"""
    order_id = event_data["aggregate_id"]

    logger.info(f"Cancelling shipping for order: {order_id}")

    try:
        # Get shipment
        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if shipment and shipment.status == ShipmentStatus.ARRANGED:
            # Mark as cancelled
            shipment.status = ShipmentStatus.FAILED
            shipment.notes = "Cancelled due to order cancellation"
            db.commit()

            # Publish ShippingCancelled event
            event = create_event(
                event_type="ShippingCancelled",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "shipment_id": shipment.shipment_id,
                    "reason": "Order cancelled",
                },
            )
            event_channel = f"{settings.event_channel_prefix}.shipping"
            redis_client.publish(event_channel, json.dumps(event))

            logger.info(f"Shipping cancelled for order: {order_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling shipping: {str(e)}")


# Event listener
@app.on_event("startup")
async def startup_event():
    """Subscribe to events on startup"""
    import threading

    def event_listener():
        pubsub = redis_client.pubsub()
        # Listen to both payment and inventory events
        pubsub.subscribe(
            [
                f"{settings.event_channel_prefix}.payment",
                f"{settings.event_channel_prefix}.inventory",
                f"{settings.event_channel_prefix}.order",
            ]
        )

        logger.info("Shipping service listening for events...")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    event_type = event_data["event_type"]

                    db = Session(engine)

                    if event_type in ["PaymentCompleted", "StockReserved"]:
                        # Simplified: treat any of these events as trigger for shipping
                        # In real implementation, you'd track both events per order
                        handle_payment_completed_and_stock_reserved(event_data, db)
                    elif event_type == "OrderCancelled":
                        handle_order_cancelled(event_data, db)

                    db.close()

                except Exception as e:
                    logger.error(f"Error processing event: {str(e)}")

    thread = threading.Thread(target=event_listener, daemon=True)
    thread.start()


@app.post("/shipping/arrange")
async def arrange_shipping(
    shipping_data: Dict[str, Any], db: Session = Depends(get_db)
):
    """Arrange shipping for order"""
    try:
        # Handle both direct payload and command structure
        if "payload" in shipping_data:
            payload = shipping_data["payload"]
            order_id = payload["order_id"]
        else:
            order_id = shipping_data["order_id"]

        logger.info(f"Arranging shipping for order: {order_id}")

        # Simulate shipping arrangement
        shipping_success = simulate_shipping_arrangement()

        if shipping_success:
            # Create shipment record
            shipment_id = generate_shipment_id()
            shipment = Shipment(
                shipment_id=shipment_id,
                order_id=order_id,
                carrier="Demo Carrier",
                tracking_number=f"TRK{shipment_id[-8:]}",
                status=ShipmentStatus.ARRANGED,
                shipping_address={
                    "name": "Demo Customer",
                    "address": "123 Demo Street, Demo City, 12345",
                    "phone": "555-0123",
                },
                estimated_delivery=datetime.utcnow().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                + timedelta(days=3),
                shipping_cost=500.00,  # Fixed shipping cost for demo
            )
            db.add(shipment)
            db.commit()

            return {
                "message": "Shipping arranged successfully",
                "shipment_id": shipment_id,
            }
        else:
            # Shipping arrangement failed
            raise HTTPException(status_code=400, detail="Shipping arrangement failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error arranging shipping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shipping/{order_id}")
async def get_shipment(order_id: str, db: Session = Depends(get_db)):
    """Get shipment details"""
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    return {
        "shipment_id": shipment.shipment_id,
        "order_id": shipment.order_id,
        "carrier": shipment.carrier,
        "tracking_number": shipment.tracking_number,
        "status": shipment.status.value,
        "estimated_delivery": shipment.estimated_delivery.isoformat()
        if shipment.estimated_delivery
        else None,
        "shipping_cost": shipment.shipping_cost,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "shipping-service"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
