from fastapi import FastAPI, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import aio_pika
import json
from datetime import datetime
from typing import Dict, Any, List
import sys
import os
import asyncio

# Add shared module to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

from models import SagaInstance, SagaStatus, SagaStepLog, StepStatus
from config import settings, get_database_url, get_rabbitmq_url
from utils import setup_logging, create_command, create_response, generate_saga_id

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
            "service": "order",
            "command": "create_order",
            "compensation": "cancel_order",
            "endpoint": "/orders",
        },
        {
            "service": "inventory",
            "command": "reserve_stock",
            "compensation": "release_stock",
            "endpoint": "/inventory/reserve",
        },
        {
            "service": "payment",
            "command": "process_payment",
            "compensation": "cancel_payment",
            "endpoint": "/payments/process",
        },
        {
            "service": "shipping",
            "command": "arrange_shipping",
            "compensation": "cancel_shipping",
            "endpoint": "/shipping/arrange",
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
    import aiohttp

    service_urls = {
        "order": settings.order_service_url,
        "inventory": settings.inventory_service_url,
        "payment": settings.payment_service_url,
        "shipping": settings.shipping_service_url,
    }

    url = f"{service_urls[service]}{command['endpoint']}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=command["payload"]) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
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
        # Send command to service
        command = create_command(command_type, saga_id, payload)
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
    """Execute compensation for a failed step"""
    step_number = step.get("step_number", 0)
    service = step["service"]
    compensation_command = step["compensation"]
    endpoint = f"/{compensation_command.replace('_', '/')}"

    logger.info(
        f"Executing compensation for step {step_number} in saga {saga_id}: {service}.{compensation_command}"
    )

    try:
        # Send compensation command
        command = create_command(compensation_command, saga_id, payload)
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
                    compensation_step = ORDER_WORKFLOW["steps"][j]
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

        # Run saga in background
        background_tasks.add_task(run_saga, saga_id, order_data)

        return {
            "saga_id": saga_id,
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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
