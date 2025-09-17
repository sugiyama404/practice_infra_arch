from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
import redis
import json
from datetime import datetime
from typing import Dict, Any
import sys
import os
import random
import uvicorn

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from shared.models import Payment, PaymentStatus
from shared.config import settings, get_database_url
from shared.utils import setup_logging, create_event, generate_payment_id

# Setup logging
logger = setup_logging("payment-service")

# FastAPI app
app = FastAPI(title="Payment Service", version="1.0.0")

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


def simulate_payment_processing(amount: float) -> bool:
    """Simulate payment processing - randomly succeed/fail for demo"""
    # For demo: 80% success rate, fail if amount > 5000
    if amount > 5000:
        return False
    return random.random() < 0.8


def handle_order_created(event_data: Dict[str, Any], db: Session):
    """Handle OrderCreated event - process payment"""
    order_id = event_data["aggregate_id"]
    total_amount = event_data["payload"]["total_amount"]

    logger.info(f"Processing payment for order: {order_id}, amount: {total_amount}")

    try:
        # Simulate payment processing
        payment_success = simulate_payment_processing(total_amount)

        if payment_success:
            # Create payment record
            payment_id = generate_payment_id()
            payment = Payment(
                payment_id=payment_id,
                order_id=order_id,
                amount=total_amount,
                payment_method="CREDIT_CARD",  # Default for demo
                status=PaymentStatus.COMPLETED,
                transaction_id=f"txn_{payment_id}",
                processed_at=datetime.utcnow(),
            )
            db.add(payment)
            db.commit()

            # Publish PaymentCompleted event
            event = create_event(
                event_type="PaymentCompleted",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "amount": total_amount,
                    "transaction_id": payment.transaction_id,
                },
            )
        else:
            # Payment failed
            payment = Payment(
                payment_id=generate_payment_id(),
                order_id=order_id,
                amount=total_amount,
                payment_method="CREDIT_CARD",
                status=PaymentStatus.FAILED,
                failed_reason="Payment processing failed",
            )
            db.add(payment)
            db.commit()

            # Publish PaymentFailed event
            event = create_event(
                event_type="PaymentFailed",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "amount": total_amount,
                    "reason": "Payment processing failed",
                },
            )

        event_channel = f"{settings.event_channel_prefix}.payment"
        redis_client.publish(event_channel, json.dumps(event))

        logger.info(
            f"Payment {'completed' if payment_success else 'failed'} for order: {order_id}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing payment: {str(e)}")


def handle_order_cancelled(event_data: Dict[str, Any], db: Session):
    """Handle OrderCancelled event - cancel/refund payment"""
    order_id = event_data["aggregate_id"]

    logger.info(f"Processing payment cancellation for order: {order_id}")

    try:
        # Get payment
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if payment and payment.status == PaymentStatus.COMPLETED:
            # Mark as cancelled/refunded
            payment.status = PaymentStatus.REFUNDED
            payment.refunded_at = datetime.utcnow()
            db.commit()

            # Publish PaymentRefunded event
            event = create_event(
                event_type="PaymentRefunded",
                aggregate_id=order_id,
                payload={
                    "order_id": order_id,
                    "payment_id": payment.payment_id,
                    "refunded_amount": payment.amount,
                },
            )
            event_channel = f"{settings.event_channel_prefix}.payment"
            redis_client.publish(event_channel, json.dumps(event))

            logger.info(f"Payment refunded for order: {order_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing payment cancellation: {str(e)}")


# Event listener
@app.on_event("startup")
async def startup_event():
    """Subscribe to events on startup"""
    import threading

    def event_listener():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(f"{settings.event_channel_prefix}.order")

        logger.info("Payment service listening for events...")

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


@app.post("/payments/process")
async def process_payment(payment_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Process payment for order"""
    try:
        # Handle both direct payload and command structure
        if "payload" in payment_data:
            payload = payment_data["payload"]
            order_id = payload["order_id"]
            amount = payload.get("amount") or payload.get(
                "price"
            )  # Handle both amount and price
        else:
            order_id = payment_data["order_id"]
            amount = payment_data.get("amount") or payment_data.get("price")

        logger.info(f"Processing payment for order: {order_id}, amount: {amount}")

        # Simulate payment processing
        payment_success = simulate_payment_processing(amount)

        if payment_success:
            # Create payment record
            payment_id = generate_payment_id()
            payment = Payment(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount,
                payment_method="CREDIT_CARD",  # Default for demo
                status=PaymentStatus.COMPLETED,
                transaction_id=f"txn_{payment_id}",
                processed_at=datetime.utcnow(),
            )
            db.add(payment)
            db.commit()

            return {
                "message": "Payment processed successfully",
                "payment_id": payment_id,
            }
        else:
            # Payment failed
            payment = Payment(
                payment_id=generate_payment_id(),
                order_id=order_id,
                amount=amount,
                payment_method="CREDIT_CARD",
                status=PaymentStatus.FAILED,
                failed_reason="Payment processing failed",
            )
            db.add(payment)
            db.commit()

            raise HTTPException(status_code=400, detail="Payment failed")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/payments/{order_id}")
async def get_payment(order_id: str, db: Session = Depends(get_db)):
    """Get payment details"""
    payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "payment_id": payment.payment_id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "status": payment.status.value,
        "transaction_id": payment.transaction_id,
        "processed_at": payment.processed_at.isoformat()
        if payment.processed_at
        else None,
    }


@app.post("/payments/cancel")
async def cancel_payment(cancel_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Cancel payment (compensation)"""
    try:
        # Handle both direct payload and command structure
        if "payload" in cancel_data:
            payload = cancel_data["payload"]
            order_id = payload["order_id"]
        else:
            order_id = cancel_data["order_id"]

        logger.info(f"Cancelling payment for order: {order_id}")

        # Find the payment
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
        if not payment:
            return {"message": "No payment found to cancel"}

        if payment.status == PaymentStatus.COMPLETED:
            # Mark as cancelled/refunded
            payment.status = PaymentStatus.CANCELLED
            payment.failed_reason = "Payment cancelled due to saga rollback"
            payment.processed_at = datetime.utcnow()
            db.commit()

            return {"message": "Payment cancelled successfully"}
        else:
            # Already cancelled or failed
            return {"message": "Payment already cancelled or not completed"}

    except Exception as e:
        logger.error(f"Error cancelling payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "payment-service"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)
