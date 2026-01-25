from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add shared module to path
sys.path.append("/app")

from shared.models import Inventory, get_db_session
from shared.utils import setup_logging

# Setup logging
logger = setup_logging("inventory-service")

# FastAPI app
app = FastAPI(title="Inventory Service", version="1.0.0")


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@app.post("/inventory/reserve")
async def reserve_stock(
    reservation_data: Dict[str, Any], db: Session = Depends(get_db)
):
    """Reserve stock for order"""
    try:
        book_id = reservation_data["book_id"]
        quantity = reservation_data["quantity"]
        order_id = reservation_data.get("order_id")
        saga_id = reservation_data.get("saga_id")

        logger.info(
            f"Reserving stock for book {book_id}, quantity {quantity}, order {order_id}"
        )

        inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
        if not inventory:
            raise HTTPException(status_code=404, detail="Book not found")

        if inventory.available_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available: {inventory.available_stock}, Requested: {quantity}",
            )

        # Reserve stock
        inventory.available_stock -= quantity
        inventory.reserved_stock += quantity
        inventory.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Stock reserved successfully for book {book_id}")

        return {
            "success": True,
            "message": "Stock reserved successfully",
            "book_id": book_id,
            "quantity": quantity,
            "order_id": order_id,
            "saga_id": saga_id,
            "reserved_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error reserving stock: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/inventory/release")
async def release_stock(release_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Release reserved stock (compensation action)"""
    try:
        book_id = release_data["book_id"]
        quantity = release_data["quantity"]
        order_id = release_data.get("order_id")
        saga_id = release_data.get("saga_id")

        logger.info(
            f"Releasing stock for book {book_id}, quantity {quantity}, order {order_id}"
        )

        inventory = db.query(Inventory).filter(Inventory.book_id == book_id).first()
        if not inventory:
            raise HTTPException(status_code=404, detail="Book not found")

        if inventory.reserved_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient reserved stock. Reserved: {inventory.reserved_stock}, Requested to release: {quantity}",
            )

        # Release stock back to available
        inventory.reserved_stock -= quantity
        inventory.available_stock += quantity
        inventory.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"Stock released successfully for book {book_id}")

        return {
            "success": True,
            "message": "Stock released successfully",
            "book_id": book_id,
            "quantity": quantity,
            "order_id": order_id,
            "saga_id": saga_id,
            "released_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error releasing stock: {str(e)}")
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

    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)
