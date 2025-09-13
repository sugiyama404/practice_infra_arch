import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
import aiohttp
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


# Configure logging
def setup_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Setup structured logging for services"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, level.upper()))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


# JSON utilities
def json_dumps(obj: Any) -> str:
    """Convert object to JSON string with datetime handling"""

    def default_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return json.dumps(obj, default=default_serializer, indent=2)


def json_loads(s: str) -> Any:
    """Parse JSON string"""
    return json.loads(s)


# ID generation
def generate_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix"""
    return f"{prefix}{uuid.uuid4().hex}"


def generate_order_id() -> str:
    """Generate order ID"""
    return generate_id("order-")


def generate_payment_id() -> str:
    """Generate payment ID"""
    return generate_id("payment-")


def generate_shipment_id() -> str:
    """Generate shipment ID"""
    return generate_id("shipment-")


def generate_saga_id() -> str:
    """Generate saga ID"""
    return generate_id("saga-")


# HTTP client utilities
class HTTPClient:
    """Async HTTP client with retry logic"""

    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def post(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """POST request with retry"""
        if not self.session:
            raise RuntimeError("HTTPClient must be used as async context manager")

        async with self.session.post(url, json=data, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def get(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """GET request with retry"""
        if not self.session:
            raise RuntimeError("HTTPClient must be used as async context manager")

        async with self.session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def put(
        self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """PUT request with retry"""
        if not self.session:
            raise RuntimeError("HTTPClient must be used as async context manager")

        async with self.session.put(url, json=data, headers=headers) as response:
            response.raise_for_status()
            return await response.json()


# Event utilities for Choreography
def create_event(
    event_type: str, aggregate_id: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Create event structure for Choreography pattern"""
    return {
        "event_id": generate_id("event-"),
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
        "version": 1,
    }


# Message utilities for Orchestration
def create_command(
    command_type: str, saga_id: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Create command structure for Orchestration pattern"""
    return {
        "command_id": generate_id("cmd-"),
        "command_type": command_type,
        "saga_id": saga_id,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
    }


def create_response(
    command_id: str, success: bool, result: Any = None, error: str = None
) -> Dict[str, Any]:
    """Create response structure for Orchestration pattern"""
    return {
        "command_id": command_id,
        "success": success,
        "result": result,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Validation utilities
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate required fields in data"""
    missing_fields = [
        field for field in required_fields if field not in data or data[field] is None
    ]
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")


def validate_positive_number(value: float, field_name: str) -> None:
    """Validate positive number"""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive")


# Database utilities
def get_db_session(engine):
    """Get database session (for synchronous operations)"""
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
