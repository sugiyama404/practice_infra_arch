import json
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from random import randint

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import config

# Logging setup
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Pydantic Models
class PushNotificationRequest(BaseModel):
    type: str = Field(..., description="Notification type")
    message_id: int = Field(..., description="Message ID")
    room_id: str = Field(..., description="Room ID")
    sender: str = Field(..., description="Sender user ID")
    content: str = Field(
        ..., max_length=config.CONTENT_MAX_LENGTH, description="Message content"
    )
    timestamp: str = Field(..., description="Message timestamp")
    recipients: List[str] = Field(
        ..., max_items=config.MAX_RECIPIENTS, description="List of recipient user IDs"
    )
    priority: Optional[str] = Field("normal", description="Notification priority")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class PushNotificationResponse(BaseModel):
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    recipients_count: int = Field(..., description="Number of recipients")
    timestamp: str = Field(..., description="Response timestamp")
    delivery_id: Optional[str] = Field(None, description="Delivery tracking ID")


class NotificationStats(BaseModel):
    total_sent: int = Field(..., description="Total notifications sent")
    success_rate: float = Field(..., description="Success rate percentage")
    average_recipients: float = Field(
        ..., description="Average recipients per notification"
    )
    last_sent: Optional[str] = Field(None, description="Last notification timestamp")


# Global statistics (in production, use proper storage)
stats = {
    "total_notifications": 0,
    "total_recipients": 0,
    "successful_deliveries": 0,
    "failed_deliveries": 0,
    "last_sent": None,
}

# FastAPI application
app = FastAPI(
    title="Chat Push Notification Service (Mock)",
    description="Mock push notification server for chat system testing",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def simulate_delivery_delay():
    """Simulate network delay for realistic testing"""
    if config.SIMULATE_DELAY:
        delay_ms = randint(config.MIN_DELAY_MS, config.MAX_DELAY_MS)
        await asyncio.sleep(delay_ms / 1000)


def generate_delivery_id() -> str:
    """Generate a mock delivery ID"""
    return (
        f"mock_delivery_{datetime.now().strftime('%Y%m%d%H%M%S')}_{randint(1000, 9999)}"
    )


def log_notification_details(request: PushNotificationRequest, delivery_id: str):
    """Log detailed notification information"""
    if not config.ENABLE_DETAILED_LOGS:
        return

    logger.info("=" * 80)
    logger.info("📱 PUSH NOTIFICATION MOCK SERVICE")
    logger.info("=" * 80)
    logger.info(f"🆔 Delivery ID: {delivery_id}")
    logger.info(f"📝 Type: {request.type}")
    logger.info(f"💬 Message ID: {request.message_id}")
    logger.info(f"🏠 Room ID: {request.room_id}")
    logger.info(f"👤 Sender: {request.sender}")
    logger.info(
        f"📄 Content: {request.content[:100]}{'...' if len(request.content) > 100 else ''}"
    )
    logger.info(f"⏰ Timestamp: {request.timestamp}")
    logger.info(f"📊 Recipients: {len(request.recipients)} users")
    logger.info(f"⚡ Priority: {request.priority}")

    # Log individual recipient notifications
    for i, recipient in enumerate(request.recipients, 1):
        logger.info(f"📱 [{i}/{len(request.recipients)}] Sending to user: {recipient}")

        # Simulate different platform notifications
        _log_platform_notifications(request, recipient, delivery_id)

    logger.info("=" * 80)


def _log_platform_notifications(
    request: PushNotificationRequest, recipient: str, delivery_id: str
):
    """Log platform-specific notification formats"""

    # Mock Firebase Cloud Messaging (FCM) for Android
    logger.info(f"🤖 [FCM/Android] Notification for {recipient}:")
    fcm_payload = {
        "to": f"mock_fcm_token_{recipient}",
        "notification": {
            "title": f"New message from {request.sender}",
            "body": request.content[:100],
            "icon": "chat_notification_icon",
            "color": "#FF5722",
            "sound": "default",
            "click_action": f"OPEN_ROOM_{request.room_id}",
        },
        "data": {
            "room_id": request.room_id,
            "message_id": str(request.message_id),
            "sender": request.sender,
            "type": request.type,
            "delivery_id": delivery_id,
        },
    }
    logger.info(f"   FCM Payload: {json.dumps(fcm_payload, indent=6)}")

    # Mock Apple Push Notification Service (APNs) for iOS
    logger.info(f"🍎 [APNs/iOS] Notification for {recipient}:")
    apns_payload = {
        "aps": {
            "alert": {
                "title": f"New message from {request.sender}",
                "body": request.content[:100],
                "subtitle": f"Room: {request.room_id}",
            },
            "badge": 1,
            "sound": "default",
            "category": "CHAT_MESSAGE",
            "mutable-content": 1,
        },
        "room_id": request.room_id,
        "message_id": request.message_id,
        "sender": request.sender,
        "delivery_id": delivery_id,
    }
    logger.info(f"   APNs Payload: {json.dumps(apns_payload, indent=6)}")

    # Mock Web Push Notification
    logger.info(f"🌐 [Web Push] Notification for {recipient}:")
    web_push_payload = {
        "title": f"New message from {request.sender}",
        "body": request.content[:100],
        "icon": "/icons/chat-icon-192.png",
        "badge": "/icons/badge-72.png",
        "tag": f"chat_message_{request.message_id}",
        "data": {
            "room_id": request.room_id,
            "message_id": request.message_id,
            "sender": request.sender,
            "url": f"/chat/{request.room_id}",
        },
        "actions": [
            {"action": "reply", "title": "Reply"},
            {"action": "view", "title": "View"},
        ],
    }
    logger.info(f"   Web Push Payload: {json.dumps(web_push_payload, indent=6)}")


@app.post("/push/send", response_model=PushNotificationResponse)
async def send_push_notification(request: PushNotificationRequest):
    """
    Mock push notification endpoint
    Simulates sending notifications and logs detailed information
    """
    try:
        # Generate delivery ID
        delivery_id = generate_delivery_id()

        # Simulate processing delay
        await simulate_delivery_delay()

        # Log notification details
        log_notification_details(request, delivery_id)

        # Update statistics
        if config.ENABLE_STATS:
            stats["total_notifications"] += 1
            stats["total_recipients"] += len(request.recipients)
            stats["successful_deliveries"] += len(request.recipients)
            stats["last_sent"] = datetime.now().isoformat()

        # Simple logging for non-detailed mode
        if not config.ENABLE_DETAILED_LOGS:
            logger.info(
                f"📱 Mock notification sent: {request.message_id} -> {len(request.recipients)} users"
            )

        return PushNotificationResponse(
            status="success",
            message=f"Mock notifications sent to {len(request.recipients)} recipients",
            recipients_count=len(request.recipients),
            timestamp=datetime.now().isoformat(),
            delivery_id=delivery_id,
        )

    except Exception as e:
        # Update failure statistics
        if config.ENABLE_STATS:
            stats["failed_deliveries"] += len(request.recipients)

        logger.error(f"❌ Mock notification failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process push notification: {str(e)}"
        )


@app.get("/push/stats", response_model=NotificationStats)
async def get_notification_stats():
    """Get push notification statistics"""
    if not config.ENABLE_STATS:
        raise HTTPException(status_code=404, detail="Statistics disabled")

    total_attempts = stats["successful_deliveries"] + stats["failed_deliveries"]
    success_rate = (
        (stats["successful_deliveries"] / total_attempts * 100)
        if total_attempts > 0
        else 100.0
    )
    avg_recipients = (
        (stats["total_recipients"] / stats["total_notifications"])
        if stats["total_notifications"] > 0
        else 0.0
    )

    return NotificationStats(
        total_sent=stats["total_notifications"],
        success_rate=round(success_rate, 2),
        average_recipients=round(avg_recipients, 2),
        last_sent=stats["last_sent"],
    )


@app.post("/push/test")
async def test_notification():
    """Send a test notification for system verification"""
    test_request = PushNotificationRequest(
        type="test",
        message_id=99999,
        room_id="test_room",
        sender="system",
        content="This is a test notification from the mock push service. Everything is working correctly! 🚀",
        timestamp=datetime.now().isoformat(),
        recipients=["test_user_1", "test_user_2", "test_user_3"],
        priority="high",
        metadata={"test": True, "environment": "mock"},
    )

    return await send_push_notification(test_request)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "push_notification_mock",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "stats_enabled": config.ENABLE_STATS,
        "detailed_logs": config.ENABLE_DETAILED_LOGS,
    }


@app.get("/config")
async def get_config():
    """Get current mock service configuration"""
    return {
        "max_recipients": config.MAX_RECIPIENTS,
        "content_max_length": config.CONTENT_MAX_LENGTH,
        "simulate_delay": config.SIMULATE_DELAY,
        "delay_range_ms": f"{config.MIN_DELAY_MS}-{config.MAX_DELAY_MS}",
        "log_level": config.LOG_LEVEL,
        "detailed_logs": config.ENABLE_DETAILED_LOGS,
        "stats_enabled": config.ENABLE_STATS,
    }


@app.post("/push/reset-stats")
async def reset_stats():
    """Reset notification statistics"""
    if not config.ENABLE_STATS:
        raise HTTPException(status_code=404, detail="Statistics disabled")

    global stats
    stats = {
        "total_notifications": 0,
        "total_recipients": 0,
        "successful_deliveries": 0,
        "failed_deliveries": 0,
        "last_sent": None,
    }

    logger.info("📊 Push notification statistics reset")
    return {"status": "success", "message": "Statistics reset"}
