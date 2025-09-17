from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import aio_pika
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, List
import sys
import os
import asyncio
import uvicorn

from shared.models import SagaInstance, SagaStatus, SagaStepLog, StepStatus
from shared.config import settings, get_database_url, get_rabbitmq_url
from shared.utils import (
    setup_logging,
    create_command,
    create_response,
    generate_saga_id,
)

# Setup logging
logger = setup_logging("saga-orchestrator")

# FastAPI app
app = FastAPI(title="Saga Orchestrator", version="1.0.0")

# Database setup
from sqlalchemy import create_engine

engine = create_engine(get_database_url())

# Order workflow definition
ORDER_WORKFLOW = {
    "steps": [
        {
            "service": "inventory",
            "command": "reserve_stock",
            "compensation": "release_stock",
            "endpoint": "/inventory/reserve",
            "compensation_endpoint": "/inventory/release",
        },
        {
            "service": "payment",
            "command": "process_payment",
            "compensation": "cancel_payment",
            "endpoint": "/payments/process",
            "compensation_endpoint": "/payments/cancel",
        },
        {
            "service": "shipping",
            "command": "arrange_shipping",
            "compensation": "cancel_shipping",
            "endpoint": "/shipping/arrange",
            "compensation_endpoint": "/shipping/cancel",
        },
    ]
}


def get_db():
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


async def send_command(service: str, command: Dict[str, Any]) -> Dict[str, Any]:
    """Send command to service via HTTP"""

    service_urls = {
        "order": settings.order_service_url,
        "inventory": settings.inventory_service_url,
        "payment": settings.payment_service_url,
        "shipping": settings.shipping_service_url,
    }

    url = f"{service_urls[service]}{command['endpoint']}"

    logger.info(f"Sending command to {service} at {url}")
    logger.info(f"Command payload: {command}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=command["payload"]) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Command successful, response: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Command failed with status {response.status}: {error_text}"
                    )
                    raise Exception(f"Service error: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Error sending command to {service}: {str(e)}")
            raise


async def execute_step(
    saga_id: str, step: Dict[str, Any], payload: Dict[str, Any], db: Session
) -> bool:
    """Execute a single step in the saga"""
    step_number = step.get("step_number", 0)
    service = step["service"]
    command_type = step["command"]
    endpoint = step["endpoint"]

    logger.info(
        f"Executing step {step_number} for saga {saga_id}: {service}.{command_type}"
    )

    # Create step log
    step_log = SagaStepLog(
        saga_id=saga_id,
        step_number=step_number,
        step_name=f"{service}.{command_type}",
        service_name=service,
        command_type=command_type,
        status=StepStatus.STARTED,
        request_payload=payload,
    )
    db.add(step_log)
    db.commit()

    try:
        # Prepare payload based on service
        if service == "inventory":
            # Extract first item for inventory service
            if "items" in payload and len(payload["items"]) > 0:
                first_item = payload["items"][0]
                command_payload = {
                    "book_id": first_item["book_id"],
                    "quantity": first_item["quantity"],
                    "order_id": payload.get("order_id"),
                    "saga_id": saga_id,
                }
            else:
                command_payload = payload
        elif service == "payment":
            # Extract payment info for payment service
            if "items" in payload and len(payload["items"]) > 0:
                first_item = payload["items"][0]
                # Calculate amount based on quantity and a default price since unit_price is not in payload
                amount = first_item["quantity"] * 3500.00  # Default price
                command_payload = {
                    "order_id": payload.get("order_id"),
                    "amount": amount,
                    "saga_id": saga_id,
                }
            else:
                command_payload = payload
        elif service == "shipping":
            # Shipping service needs order_id
            command_payload = {
                "order_id": payload.get("order_id"),
                "saga_id": saga_id,
            }
        else:
            command_payload = payload

        # Send command to service
        command = create_command(command_type, saga_id, command_payload)
        command["endpoint"] = endpoint

        response = await send_command(service, command)

        # Update step log
        step_log.status = StepStatus.COMPLETED
        step_log.response_payload = response
        step_log.completed_at = datetime.utcnow()
        step_log.duration_ms = int(
            (datetime.utcnow() - step_log.started_at).total_seconds() * 1000
        )
        db.commit()

        logger.info(f"Step {step_number} completed successfully for saga {saga_id}")
        return True

    except Exception as e:
        # Update step log with error
        step_log.status = StepStatus.FAILED
        step_log.error_message = str(e)
        step_log.completed_at = datetime.utcnow()
        step_log.duration_ms = int(
            (datetime.utcnow() - step_log.started_at).total_seconds() * 1000
        )
        db.commit()

        logger.error(f"Step {step_number} failed for saga {saga_id}: {str(e)}")
        return False


async def execute_compensation(
    saga_id: str, step: Dict[str, Any], payload: Dict[str, Any], db: Session
) -> bool:
    """
    Execute compensation for a failed step.
    This is the rollback mechanism for the saga.
    """
    step_number = step.get("step_number", 0)
    service = step["service"]
    compensation_command = step["compensation"]
    # Use the explicitly defined compensation endpoint from the workflow
    endpoint = step["compensation_endpoint"]

    logger.info(f"Step data: {step}")
    logger.info(f"Using endpoint: {endpoint}")

    logger.info(
        f"Executing compensation for step {step_number} in saga {saga_id}: {service}.{compensation_command}"
    )

    try:
        # Prepare compensation payload based on service
        if service == "inventory":
            # Extract first item for inventory compensation
            if "items" in payload and len(payload["items"]) > 0:
                first_item = payload["items"][0]
                compensation_payload = {
                    "book_id": first_item["book_id"],
                    "quantity": first_item["quantity"],
                    "order_id": payload.get("order_id"),
                    "saga_id": saga_id,
                }
            else:
                compensation_payload = payload
        elif service == "payment":
            # Payment compensation needs order_id
            compensation_payload = {
                "order_id": payload.get("order_id"),
                "saga_id": saga_id,
            }
        elif service == "shipping":
            # Shipping compensation needs order_id
            compensation_payload = {
                "order_id": payload.get("order_id"),
                "saga_id": saga_id,
            }
        else:
            compensation_payload = payload

        # Send compensation command
        command = create_command(compensation_command, saga_id, compensation_payload)
        command["endpoint"] = endpoint

        response = await send_command(service, command)

        # Update step log
        step_log = (
            db.query(SagaStepLog)
            .filter(
                SagaStepLog.saga_id == saga_id, SagaStepLog.step_number == step_number
            )
            .first()
        )

        if step_log:
            step_log.status = StepStatus.COMPENSATED
            step_log.completed_at = datetime.utcnow()
            db.commit()

        logger.info(f"Compensation completed for step {step_number} in saga {saga_id}")
        return True

    except Exception as e:
        logger.error(
            f"Compensation failed for step {step_number} in saga {saga_id}: {str(e)}"
        )
        return False


async def run_saga(saga_id: str, order_data: Dict[str, Any]):
    """Execute the complete saga workflow"""
    db = Session(engine)

    try:
        # Create saga instance
        saga = SagaInstance(
            saga_id=saga_id,
            saga_type="ORDER_PROCESSING",
            order_id=order_data.get("order_id", saga_id),
            status=SagaStatus.STARTED,
            payload=order_data,
        )
        db.add(saga)
        db.commit()

        logger.info(f"Started saga {saga_id}")

        # Execute each step
        for i, step in enumerate(ORDER_WORKFLOW["steps"]):
            step["step_number"] = i + 1

            # Update saga status
            if i == 0:
                saga.status = SagaStatus.ORDER_CREATED
            elif i == 1:
                saga.status = SagaStatus.STOCK_RESERVED
            elif i == 2:
                saga.status = SagaStatus.PAYMENT_COMPLETED
            elif i == 3:
                saga.status = SagaStatus.SHIPPING_ARRANGED
            db.commit()

            # Execute step
            success = await execute_step(saga_id, step, order_data, db)

            if not success:
                # Start compensation
                logger.warning(
                    f"Saga {saga_id} failed at step {i + 1}, starting compensation"
                )
                saga.status = SagaStatus.COMPENSATION_STARTED
                db.commit()

                # Execute compensations in reverse order
                for j in range(i, -1, -1):
                    compensation_step = ORDER_WORKFLOW["steps"][j].copy()
                    compensation_step["step_number"] = j + 1
                    await execute_compensation(
                        saga_id, compensation_step, order_data, db
                    )

                # Mark saga as failed
                saga.status = SagaStatus.FAILED
                saga.failed_at = datetime.utcnow()
                db.commit()

                logger.error(f"Saga {saga_id} failed and compensation completed")
                return

        # All steps completed successfully
        saga.status = SagaStatus.COMPLETED
        saga.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Saga {saga_id} completed successfully")

    except Exception as e:
        logger.error(f"Error running saga {saga_id}: {str(e)}")
        if saga:
            saga.status = SagaStatus.FAILED
            saga.error_message = str(e)
            saga.failed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@app.post("/saga/start")
async def start_saga(
    order_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start a new saga"""
    try:
        saga_id = generate_saga_id()

        # Add saga_id to order_data
        order_data["saga_id"] = saga_id

        # First, create the order to get the actual order_id
        # Extract first item for order creation
        if "items" in order_data and len(order_data["items"]) > 0:
            first_item = order_data["items"][0]
            order_payload = {
                "customer_id": order_data["customer_id"],
                "items": [
                    {
                        "book_id": first_item["book_id"],
                        "quantity": first_item["quantity"],
                    }
                ],
                "saga_id": saga_id,
            }
        else:
            # Fallback for old format - convert to new format
            order_payload = {
                "customer_id": order_data["customer_id"],
                "items": [
                    {
                        "book_id": order_data.get("book_id")
                        or order_data.get("product_id"),
                        "quantity": order_data.get("quantity", 1),
                    }
                ],
                "saga_id": saga_id,
            }

        async with aiohttp.ClientSession() as session:
            try:
                url = f"{settings.order_service_url}/orders"
                async with session.post(url, json=order_payload) as response:
                    if response.status == 200:
                        order_response = await response.json()
                        actual_order_id = order_response.get("order_id")
                        order_data["order_id"] = actual_order_id
                        logger.info(
                            f"Created order {actual_order_id} for saga {saga_id}"
                        )
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Failed to create order: {response.status} - {error_text}"
                        )
            except Exception as e:
                logger.error(f"Error creating order for saga {saga_id}: {str(e)}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to create order: {str(e)}"
                )

        # Now run the saga with the actual order_id
        background_tasks.add_task(run_saga, saga_id, order_data)

        return {
            "saga_id": saga_id,
            "order_id": actual_order_id,
            "status": "started",
            "message": "Saga started successfully",
        }

    except Exception as e:
        logger.error(f"Error starting saga: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/saga/{saga_id}/status")
async def get_saga_status(saga_id: str, db: Session = Depends(get_db)):
    """Get saga status"""
    saga = db.query(SagaInstance).filter(SagaInstance.saga_id == saga_id).first()
    if not saga:
        raise HTTPException(status_code=404, detail="Saga not found")

    # Get step logs
    step_logs = (
        db.query(SagaStepLog)
        .filter(SagaStepLog.saga_id == saga_id)
        .order_by(SagaStepLog.step_number)
        .all()
    )

    return {
        "saga_id": saga.saga_id,
        "status": saga.status.value,
        "current_step": saga.current_step,
        "created_at": saga.created_at.isoformat(),
        "completed_at": saga.completed_at.isoformat() if saga.completed_at else None,
        "failed_at": saga.failed_at.isoformat() if saga.failed_at else None,
        "error_message": saga.error_message,
        "steps": [
            {
                "step_number": log.step_number,
                "step_name": log.step_name,
                "service_name": log.service_name,
                "status": log.status.value,
                "started_at": log.started_at.isoformat(),
                "completed_at": log.completed_at.isoformat()
                if log.completed_at
                else None,
                "duration_ms": log.duration_ms,
                "error_message": log.error_message,
            }
            for log in step_logs
        ],
    }


@app.post("/saga/{saga_id}/cancel")
async def cancel_saga(saga_id: str, db: Session = Depends(get_db)):
    """Manually cancel a saga"""
    saga = db.query(SagaInstance).filter(SagaInstance.saga_id == saga_id).first()
    if not saga:
        raise HTTPException(status_code=404, detail="Saga not found")

    if saga.status in [SagaStatus.COMPLETED, SagaStatus.FAILED]:
        return {"message": "Saga already finished"}

    # Mark as failed (simplified cancellation)
    saga.status = SagaStatus.FAILED
    saga.error_message = "Manually cancelled"
    saga.failed_at = datetime.utcnow()
    db.commit()

    return {"message": "Saga cancelled successfully"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "saga-orchestrator"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
