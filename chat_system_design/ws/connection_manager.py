import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket
import redis.asyncio as redis

from config import config

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """WebSocket connection information"""

    def __init__(
        self, websocket: WebSocket, user_id: str, device_id: str, room_id: str
    ):
        self.websocket = websocket
        self.user_id = user_id
        self.device_id = device_id
        self.room_id = room_id
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()


class ConnectionManager:
    """Manages WebSocket connections (stateful)"""

    def __init__(self, redis_pool: redis.Redis):
        # user_id -> Set[ConnectionInfo]
        self.user_connections: Dict[str, Set[ConnectionInfo]] = {}
        # websocket -> ConnectionInfo
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        # room_id -> Set[ConnectionInfo]
        self.room_connections: Dict[str, Set[ConnectionInfo]] = {}

        self.redis = redis_pool

    async def connect(
        self, websocket: WebSocket, user_id: str, device_id: str, room_id: str
    ) -> bool:
        """Accept WebSocket connection and register user"""
        try:
            await websocket.accept()

            # Create connection info
            conn_info = ConnectionInfo(websocket, user_id, device_id, room_id)

            # Check connection limits
            if user_id in self.user_connections:
                if (
                    len(self.user_connections[user_id])
                    >= config.MAX_CONNECTIONS_PER_USER
                ):
                    await websocket.close(code=1008, reason="Too many connections")
                    return False

            # Register connection
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()

            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()

            self.user_connections[user_id].add(conn_info)
            self.room_connections[room_id].add(conn_info)
            self.connection_info[websocket] = conn_info

            # Update Redis: presence and session
            await self._update_presence(user_id, device_id, "online")
            await self._update_session(user_id, device_id, True)

            logger.info(
                f"User {user_id} (device: {device_id}) connected to room {room_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect user {user_id}: {e}", exc_info=True)
            return False

    async def disconnect(self, websocket: WebSocket):
        """Disconnect WebSocket and cleanup"""
        if websocket not in self.connection_info:
            return

        conn_info = self.connection_info[websocket]
        user_id = conn_info.user_id
        device_id = conn_info.device_id
        room_id = conn_info.room_id

        # Remove from tracking
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(conn_info)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        if room_id in self.room_connections:
            self.room_connections[room_id].discard(conn_info)
            if not self.room_connections[room_id]:
                del self.room_connections[room_id]

        del self.connection_info[websocket]

        # Update Redis: presence and session
        await self._update_presence(user_id, device_id, "offline")
        await self._update_session(user_id, device_id, False)

        logger.info(
            f"User {user_id} (device: {device_id}) disconnected from room {room_id}"
        )

    async def send_to_user(
        self, user_id: str, message: dict, exclude_websocket: Optional[WebSocket] = None
    ) -> int:
        """Send message to all connections of a user"""
        sent_count = 0

        if user_id not in self.user_connections:
            return sent_count

        disconnected = set()

        for conn_info in list(self.user_connections[user_id]):
            if exclude_websocket and conn_info.websocket == exclude_websocket:
                continue

            try:
                await conn_info.websocket.send_text(json.dumps(message))
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                disconnected.add(conn_info)

        # Clean up disconnected websockets
        for conn_info in disconnected:
            await self.disconnect(conn_info.websocket)

        return sent_count

    async def send_to_room(
        self, room_id: str, message: dict, exclude_user: Optional[str] = None
    ) -> int:
        """Send message to all users in a room"""
        sent_count = 0

        if room_id not in self.room_connections:
            return sent_count

        disconnected = set()

        for conn_info in list(self.room_connections[room_id]):
            if exclude_user and conn_info.user_id == exclude_user:
                continue

            try:
                await conn_info.websocket.send_text(json.dumps(message))
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to send to room {room_id}: {e}")
                disconnected.add(conn_info)

        # Clean up disconnected websockets
        for conn_info in disconnected:
            await self.disconnect(conn_info.websocket)

        return sent_count

    async def broadcast_to_room(
        self, room_id: str, message: dict, sender_websocket: Optional[WebSocket] = None
    ) -> int:
        """Broadcast message to room (excluding sender)"""
        sent_count = 0

        if room_id not in self.room_connections:
            return sent_count

        disconnected = set()

        for conn_info in list(self.room_connections[room_id]):
            if sender_websocket and conn_info.websocket == sender_websocket:
                continue

            try:
                await conn_info.websocket.send_text(json.dumps(message))
                sent_count += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to room {room_id}: {e}")
                disconnected.add(conn_info)

        # Clean up disconnected websockets
        for conn_info in disconnected:
            await self.disconnect(conn_info.websocket)

        return sent_count

    async def update_last_ping(self, websocket: WebSocket):
        """Update last ping time for connection"""
        if websocket in self.connection_info:
            self.connection_info[websocket].last_ping = datetime.now()

    async def get_connection_stats(self) -> dict:
        """Get current connection statistics"""
        total_connections = sum(
            len(connections) for connections in self.user_connections.values()
        )
        room_stats = {
            room_id: len(connections)
            for room_id, connections in self.room_connections.items()
        }

        return {
            "server_id": config.WS_SERVER_ID,
            "total_users": len(self.user_connections),
            "total_connections": total_connections,
            "rooms": room_stats,
            "online_users": list(self.user_connections.keys()),
        }

    async def _update_presence(self, user_id: str, device_id: str, status: str):
        """Update user presence in Redis"""
        try:
            presence_key = config.PRESENCE_KEY_PATTERN.format(user_id=user_id)
            presence_data = {
                "user_id": user_id,
                "status": status,
                "last_seen": datetime.now().isoformat(),
                "ws_server": config.WS_SERVER_ID,
                "device_id": device_id,
            }

            await self.redis.set(
                presence_key, json.dumps(presence_data), ex=3600
            )  # 1 hour expiry

        except Exception as e:
            logger.error(f"Failed to update presence for {user_id}: {e}")

    async def _update_session(self, user_id: str, device_id: str, is_connected: bool):
        """Update session information in Redis"""
        try:
            session_key = config.SESSION_KEY_PATTERN.format(
                user_id=user_id, device_id=device_id
            )

            if is_connected:
                await self.redis.set(
                    session_key, config.WS_SERVER_ID, ex=3600
                )  # 1 hour expiry
            else:
                await self.redis.delete(session_key)

        except Exception as e:
            logger.error(f"Failed to update session for {user_id}:{device_id}: {e}")

    async def cleanup_stale_connections(self):
        """Clean up stale connections (called periodically)"""
        now = datetime.now()
        stale_connections = []

        for websocket, conn_info in self.connection_info.items():
            # Check if connection is stale (no ping for too long)
            if (now - conn_info.last_ping).total_seconds() > config.WEBSOCKET_TIMEOUT:
                stale_connections.append(websocket)

        for websocket in stale_connections:
            logger.info(
                f"Cleaning up stale connection: {self.connection_info[websocket].user_id}"
            )
            await self.disconnect(websocket)
            try:
                await websocket.close(code=1000, reason="Connection timeout")
            except Exception:
                pass  # Connection might already be closed
