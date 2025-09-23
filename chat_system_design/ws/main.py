import json
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional


import redis.asyncio as redis
import aio_pika
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import config
from connection_manager import ConnectionManager

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connections
redis_pool: Optional[redis.Redis] = None
rabbitmq_connection: Optional[aio_pika.Connection] = None
manager: Optional[ConnectionManager] = None


async def message_consumer():
    """RabbitMQ consumer to receive messages for WebSocket delivery"""
    try:
        connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        channel = await connection.channel()

        # Declare exchange for WebSocket message distribution
        ws_exchange = await channel.declare_exchange(
            "ws_messages", aio_pika.ExchangeType.FANOUT
        )

        # Create queue for this WebSocket server instance
        queue = await channel.declare_queue(f"ws_{config.WS_SERVER_ID}", exclusive=True)
        await queue.bind(ws_exchange)

        async def process_message(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    message_type = data.get("type")

                    if message_type == "new_message":
                        # Broadcast new message to room
                        websocket_message = {
                            "type": "message",
                            "message_id": data["message_id"],
                            "user_id": data["user_id"],
                            "room_id": data["room_id"],
                            "content": data["content"],
                            "timestamp": data["timestamp"],
                            "message_type": data.get("message_type", "text"),
                        }

                        sent_count = await manager.send_to_room(
                            data["room_id"],
                            websocket_message,
                            exclude_user=data.get("sender_user_id"),
                        )

                        logger.info(
                            f"Broadcasted message {data['message_id']} to {sent_count} connections in room {data['room_id']}"
                        )

                    elif message_type == "presence_update":
                        # Broadcast presence update to user's rooms
                        presence_message = {
                            "type": "presence",
                            "user_id": data["user_id"],
                            "status": data["status"],
                            "timestamp": data["timestamp"],
                        }

                        # Send to all rooms where user is present (simplified)
                        for room_id in data.get("rooms", []):
                            await manager.send_to_room(room_id, presence_message)

                        logger.info(
                            f"Broadcasted presence update for {data['user_id']}: {data['status']}"
                        )

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        await queue.consume(process_message)
        logger.info(f"Started message consumer for {config.WS_SERVER_ID}")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Failed to start message consumer: {e}")


async def connection_cleanup_task():
    """Periodic task to clean up stale connections"""
    while True:
        try:
            await asyncio.sleep(config.PING_INTERVAL)
            await manager.cleanup_stale_connections()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global redis_pool, rabbitmq_connection, manager

    logger.info(f"Starting WebSocket server {config.WS_SERVER_ID}...")

    try:
        # Redis connection
        redis_pool = redis.from_url(config.REDIS_URL)
        logger.info("Connected to Redis")

        # Initialize connection manager
        manager = ConnectionManager(redis_pool)
        logger.info("Connection manager initialized")

        # Start background tasks
        consumer_task = asyncio.create_task(message_consumer())
        cleanup_task = asyncio.create_task(connection_cleanup_task())

        logger.info(f"WebSocket server {config.WS_SERVER_ID} startup completed")

    except Exception as e:
        logger.error(f"Failed to initialize WebSocket server: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"Shutting down WebSocket server {config.WS_SERVER_ID}...")

    consumer_task.cancel()
    cleanup_task.cancel()

    if redis_pool:
        await redis_pool.close()
        logger.info("Closed Redis connection")

    logger.info("WebSocket server shutdown completed")


# FastAPI application
app = FastAPI(
    title=f"Chat WebSocket Server ({config.WS_SERVER_ID})",
    description="Stateful WebSocket server for real-time chat",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/{user_id}/{device_id}/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: str, device_id: str, room_id: str
):
    """
    WebSocket connection endpoint (stateful)
    - Accept connection and register user
    - Handle incoming messages (ping/pong, typing, etc.)
    - Manage disconnection
    """
    if not await manager.connect(websocket, user_id, device_id, room_id):
        logger.warning(f"Failed to connect user {user_id}")
        return

    try:
        # Send welcome message
        welcome_message = {
            "type": "welcome",
            "message": f"Connected to room {room_id}",
            "server_id": config.WS_SERVER_ID,
            "timestamp": datetime.now().isoformat(),
        }
        await websocket.send_text(json.dumps(welcome_message))

        # Listen for client messages
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # Update last ping time
                await manager.update_last_ping(websocket)

                if message_type == "ping":
                    # Respond to ping
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send_text(json.dumps(pong_message))

                elif message_type == "typing":
                    # Broadcast typing indicator to room
                    typing_message = {
                        "type": "typing",
                        "user_id": user_id,
                        "room_id": room_id,
                        "is_typing": message.get("is_typing", False),
                        "timestamp": datetime.now().isoformat(),
                    }

                    sent_count = await manager.broadcast_to_room(
                        room_id, typing_message, sender_websocket=websocket
                    )

                    logger.debug(
                        f"Broadcasted typing indicator from {user_id} to {sent_count} connections"
                    )

                elif message_type == "read_receipt":
                    # Handle read receipt
                    receipt_message = {
                        "type": "read_receipt",
                        "user_id": user_id,
                        "room_id": room_id,
                        "message_id": message.get("message_id"),
                        "timestamp": datetime.now().isoformat(),
                    }

                    await manager.send_to_room(
                        room_id, receipt_message, exclude_user=user_id
                    )

                else:
                    logger.warning(
                        f"Unknown message type from {user_id}: {message_type}"
                    )

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from user {user_id}: {data}")
            except Exception as e:
                logger.error(f"Error processing message from {user_id}: {e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": f"websocket_server_{config.WS_SERVER_ID}",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/stats")
async def get_stats():
    """Get current connection statistics"""
    if manager:
        stats = await manager.get_connection_stats()
        stats["timestamp"] = datetime.now().isoformat()
        return stats

    return {
        "status": "initializing",
        "server_id": config.WS_SERVER_ID,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/connections/{user_id}")
async def get_user_connections(user_id: str):
    """Get connection info for a specific user"""
    if not manager or user_id not in manager.user_connections:
        return {"user_id": user_id, "connections": []}

    connections = []
    for conn_info in manager.user_connections[user_id]:
        connections.append(
            {
                "device_id": conn_info.device_id,
                "room_id": conn_info.room_id,
                "connected_at": conn_info.connected_at.isoformat(),
                "last_ping": conn_info.last_ping.isoformat(),
            }
        )

    return {
        "user_id": user_id,
        "server_id": config.WS_SERVER_ID,
        "connections": connections,
        "total": len(connections),
    }
