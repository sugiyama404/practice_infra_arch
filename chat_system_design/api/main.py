import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional
import uvicorn

import aioredis
import aio_pika
import asyncpg
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware

from config import config
from models import (
    SendMessageRequest,
    SendMessageResponse,
    SyncMessagesRequest,
    SyncMessagesResponse,
    MessageData,
    PresenceData,
    HealthResponse,
    ErrorResponse,
    MessageQueuePayload,
)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connections
redis_pool: Optional[aioredis.Redis] = None
rabbitmq_connection: Optional[aio_pika.Connection] = None
rabbitmq_channel: Optional[aio_pika.Channel] = None
db_pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup/shutdown)"""
    # Startup
    global redis_pool, rabbitmq_connection, rabbitmq_channel, db_pool

    logger.info("Starting API server...")

    try:
        # Redis connection
        redis_pool = aioredis.from_url(config.REDIS_URL)
        logger.info("Connected to Redis")

        # RabbitMQ connection
        rabbitmq_connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        rabbitmq_channel = await rabbitmq_connection.channel()
        await rabbitmq_channel.declare_queue("messages", durable=True)
        logger.info("Connected to RabbitMQ")

        # Database connection pool
        db_pool = await asyncpg.create_pool(
            config.DATABASE_URL, **config.get_database_config()
        )
        logger.info("Connected to PostgreSQL")

        logger.info("API server startup completed")

    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down API server...")

    if redis_pool:
        await redis_pool.close()
        logger.info("Closed Redis connection")

    if rabbitmq_connection:
        await rabbitmq_connection.close()
        logger.info("Closed RabbitMQ connection")

    if db_pool:
        await db_pool.close()
        logger.info("Closed PostgreSQL connection pool")

    logger.info("API server shutdown completed")


# FastAPI application
app = FastAPI(
    title=config.TITLE,
    description=config.DESCRIPTION,
    version=config.VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection
async def get_redis() -> aioredis.Redis:
    if redis_pool is None:
        raise HTTPException(status_code=503, detail="Redis connection not available")
    return redis_pool


async def get_rabbitmq_channel() -> aio_pika.Channel:
    if rabbitmq_channel is None:
        raise HTTPException(status_code=503, detail="RabbitMQ connection not available")
    return rabbitmq_channel


async def get_db() -> asyncpg.Pool:
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database connection not available")
    return db_pool


@app.post(f"{config.API_PREFIX}/messages/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    redis: aioredis.Redis = Depends(get_redis),
    channel: aio_pika.Channel = Depends(get_rabbitmq_channel),
):
    """
    Send message API (stateless)
    1. Generate message_id using Redis INCR
    2. Send message to RabbitMQ for async processing
    """
    try:
        # Generate unique message ID
        message_id = await redis.incr("msg_id_counter")
        timestamp = datetime.now()

        # Create message payload for queue
        payload = MessageQueuePayload(
            message_id=message_id,
            user_id=request.user_id,
            device_id=request.device_id,
            room_id=request.room_id,
            content=request.content,
            timestamp=timestamp.isoformat(),
        )

        # Send to RabbitMQ for async processing
        message_body = payload.model_dump_json()
        await channel.default_exchange.publish(
            aio_pika.Message(message_body.encode()), routing_key="messages"
        )

        logger.info(
            f"Message {message_id} queued for processing from user {request.user_id}"
        )

        return SendMessageResponse(
            message_id=message_id, status="sent", timestamp=timestamp
        )

    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@app.get(f"{config.API_PREFIX}/messages/sync", response_model=SyncMessagesResponse)
async def sync_messages(
    user_id: str = Query(..., description="User ID"),
    device_id: str = Query(..., description="Device ID"),
    room_id: str = Query(..., description="Room ID"),
    last_message_id: int = Query(0, ge=0, description="Last received message ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum messages to return"),
    db_pool: asyncpg.Pool = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Multi-device sync API
    1. Get messages after last_message_id
    2. Update device's cur_max_message_id in Redis
    """
    try:
        async with db_pool.acquire() as conn:
            # Get messages after last_message_id
            query = """
                SELECT message_id, user_id, room_id, content, message_type, created_at
                FROM messages
                WHERE room_id = $1 AND message_id > $2 AND is_deleted = FALSE
                ORDER BY message_id ASC
                LIMIT $3
            """
            rows = await conn.fetch(query, room_id, last_message_id, limit)

            messages = []
            max_message_id = last_message_id

            for row in rows:
                messages.append(
                    MessageData(
                        message_id=row["message_id"],
                        user_id=row["user_id"],
                        room_id=row["room_id"],
                        content=row["content"],
                        message_type=row["message_type"],
                        timestamp=row["created_at"],
                    )
                )
                max_message_id = max(max_message_id, row["message_id"])

            # Check if there are more messages
            has_more = len(rows) == limit

            # Update device's cur_max_message_id in Redis
            if max_message_id > last_message_id:
                device_key = f"device:{device_id}:cur_max_msg_id:{room_id}"
                await redis.set(device_key, max_message_id)
                logger.info(
                    f"Updated device {device_id} cur_max_msg_id to {max_message_id}"
                )

            return SyncMessagesResponse(
                messages=messages, cur_max_message_id=max_message_id, has_more=has_more
            )

    except Exception as e:
        logger.error(f"Failed to sync messages: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync messages")


@app.get(f"{config.API_PREFIX}/users/{{user_id}}/presence", response_model=PresenceData)
async def get_presence(user_id: str, redis: aioredis.Redis = Depends(get_redis)):
    """Get user presence information"""
    try:
        presence_data = await redis.get(f"presence:{user_id}")

        if presence_data:
            data = json.loads(presence_data)
            return PresenceData(
                user_id=data["user_id"],
                status=data["status"],
                last_seen=datetime.fromisoformat(data["last_seen"]),
                ws_server=data.get("ws_server"),
            )

        # Return offline if no presence data
        return PresenceData(
            user_id=user_id, status="offline", last_seen=datetime.now(), ws_server=None
        )

    except Exception as e:
        logger.error(f"Failed to get presence for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get presence")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="chat-api",
        version=config.VERSION,
        timestamp=datetime.now(),
    )


@app.get(f"{config.API_PREFIX}/stats")
async def get_stats(
    redis: aioredis.Redis = Depends(get_redis), db_pool: asyncpg.Pool = Depends(get_db)
):
    """Get system statistics"""
    try:
        # Get message count from database
        async with db_pool.acquire() as conn:
            total_messages = await conn.fetchval("SELECT COUNT(*) FROM messages")
            active_rooms = await conn.fetchval(
                "SELECT COUNT(DISTINCT room_id) FROM messages"
            )

        # Get current message ID counter
        current_msg_id = await redis.get("msg_id_counter")
        current_msg_id = int(current_msg_id) if current_msg_id else 0

        return {
            "service": "chat-api",
            "total_messages": total_messages,
            "active_rooms": active_rooms,
            "current_message_id": current_msg_id,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


if __name__ == "__main__":
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info", reload=True)
