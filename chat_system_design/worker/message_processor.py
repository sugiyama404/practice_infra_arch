import logging
from datetime import datetime
from typing import List, Optional, Dict
import aiohttp
import redis.asyncio as redis
import asyncpg
from pydantic import BaseModel

from config import config

logger = logging.getLogger(__name__)


class MessageData(BaseModel):
    """Message data structure"""

    message_id: int
    user_id: str
    device_id: str
    room_id: str
    content: str
    message_type: str = "text"
    timestamp: str
    metadata: Optional[dict] = None


class MessageProcessor:
    """Handles message processing logic"""

    def __init__(self, db_pool: asyncpg.Pool, redis_pool: redis.Redis):
        self.db_pool = db_pool
        self.redis = redis_pool
        self.http_session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize HTTP session for push notifications"""
        self.http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )

    async def close(self):
        """Clean up resources"""
        if self.http_session:
            await self.http_session.close()

    async def process_message(self, message_data: MessageData) -> bool:
        """
        Process a single message:
        1. Save to PostgreSQL
        2. Update Redis (device cur_max_message_id)
        3. Broadcast to WebSocket servers
        4. Send push notifications to offline users
        """
        try:
            logger.info(
                f"Processing message {message_data.message_id} from {message_data.user_id}"
            )

            # 1. Save message to database
            await self._save_message_to_db(message_data)

            # 2. Update device's cur_max_message_id
            await self._update_device_message_id(message_data)

            # 3. Broadcast to WebSocket servers
            await self._broadcast_to_websockets(message_data)

            # 4. Handle push notifications for offline users
            await self._handle_push_notifications(message_data)

            logger.info(f"Successfully processed message {message_data.message_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to process message {message_data.message_id}: {e}")
            return False

    async def _save_message_to_db(self, message_data: MessageData):
        """Save message to PostgreSQL"""
        async with self.db_pool.acquire() as conn:
            query = """
                INSERT INTO messages (message_id, user_id, room_id, content, message_type, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (message_id) DO NOTHING
            """

            created_at = datetime.fromisoformat(
                message_data.timestamp.replace("Z", "+00:00")
            )

            await conn.execute(
                query,
                message_data.message_id,
                message_data.user_id,
                message_data.room_id,
                message_data.content,
                message_data.message_type,
                created_at,
            )

            logger.debug(f"Saved message {message_data.message_id} to database")

    async def _update_device_message_id(self, message_data: MessageData):
        """Update device's cur_max_message_id in Redis"""
        device_key = (
            f"device:{message_data.device_id}:cur_max_msg_id:{message_data.room_id}"
        )

        # Get current max_message_id for this device
        current_max = await self.redis.get(device_key)
        current_max = int(current_max) if current_max else 0

        # Update if new message_id is higher
        if message_data.message_id > current_max:
            await self.redis.set(device_key, message_data.message_id)
            logger.debug(
                f"Updated device {message_data.device_id} cur_max_msg_id to {message_data.message_id}"
            )

    async def _broadcast_to_websockets(self, message_data: MessageData):
        """Broadcast message to all WebSocket servers via RabbitMQ"""
        try:
            # This will be handled by the main worker's RabbitMQ channel
            # We just prepare the message data here
            ws_message = {
                "type": "new_message",
                "message_id": message_data.message_id,
                "user_id": message_data.user_id,
                "room_id": message_data.room_id,
                "content": message_data.content,
                "timestamp": message_data.timestamp,
                "message_type": message_data.message_type,
                "sender_user_id": message_data.user_id,
            }

            return ws_message

        except Exception as e:
            logger.error(f"Failed to prepare WebSocket broadcast: {e}")
            raise

    async def _handle_push_notifications(self, message_data: MessageData):
        """Handle push notifications for offline users"""
        try:
            # Get offline users in the room
            offline_users = await self._get_offline_users_in_room(
                message_data.room_id, message_data.user_id
            )

            if offline_users:
                await self._send_push_notifications(message_data, offline_users)
            else:
                logger.debug(
                    f"No offline users to notify for message {message_data.message_id}"
                )

        except Exception as e:
            logger.error(f"Failed to handle push notifications: {e}")

    async def _get_offline_users_in_room(
        self, room_id: str, sender_user_id: str
    ) -> List[str]:
        """Get list of offline users in a room"""
        try:
            # Get all room members from database
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT rm.user_id
                    FROM room_members rm
                    WHERE rm.room_id = $1 AND rm.user_id != $2
                """
                rows = await conn.fetch(query, room_id, sender_user_id)
                room_members = [row["user_id"] for row in rows]

            if not room_members:
                return []

            # Check which users are offline (no active sessions)
            offline_users = []

            for user_id in room_members:
                # Check if user has any active sessions
                pattern = f"session:{user_id}:*"
                has_session = False

                async for key in self.redis.scan_iter(match=pattern):
                    has_session = True
                    break

                if not has_session:
                    offline_users.append(user_id)

            logger.debug(f"Found {len(offline_users)} offline users in room {room_id}")
            return offline_users

        except Exception as e:
            logger.error(f"Failed to get offline users: {e}")
            return []

    async def _send_push_notifications(
        self, message_data: MessageData, offline_users: List[str]
    ):
        """Send push notifications to offline users"""
        if not self.http_session or not offline_users:
            return

        try:
            notification_payload = {
                "type": "message",
                "message_id": message_data.message_id,
                "room_id": message_data.room_id,
                "sender": message_data.user_id,
                "content": message_data.content,
                "timestamp": message_data.timestamp,
                "recipients": offline_users,
            }

            async with self.http_session.post(
                f"{config.PN_SERVER_URL}/push/send",
                json=notification_payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"Sent push notifications to {len(offline_users)} users: {result.get('message', 'OK')}"
                    )
                else:
                    error_text = await response.text()
                    logger.warning(
                        f"Push notification failed (HTTP {response.status}): {error_text}"
                    )

        except aiohttp.ClientError as e:
            logger.error(f"Push notification client error: {e}")
        except Exception as e:
            logger.error(f"Failed to send push notifications: {e}")

    async def get_room_stats(self, room_id: str) -> Dict:
        """Get statistics for a specific room"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get message count
                message_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM messages WHERE room_id = $1", room_id
                )

                # Get member count
                member_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM room_members WHERE room_id = $1", room_id
                )

                # Get latest message
                latest_message = await conn.fetchrow(
                    "SELECT message_id, created_at FROM messages WHERE room_id = $1 ORDER BY message_id DESC LIMIT 1",
                    room_id,
                )

            return {
                "room_id": room_id,
                "message_count": message_count,
                "member_count": member_count,
                "latest_message_id": latest_message["message_id"]
                if latest_message
                else None,
                "latest_message_time": latest_message["created_at"].isoformat()
                if latest_message
                else None,
            }

        except Exception as e:
            logger.error(f"Failed to get room stats: {e}")
            return {"room_id": room_id, "error": str(e)}

    async def cleanup_old_messages(self, days_old: int = 30) -> int:
        """Clean up old messages (optional maintenance task)"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    UPDATE messages
                    SET is_deleted = TRUE
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    AND is_deleted = FALSE
                """
                result = await conn.execute(query, days_old)

                # Extract affected row count from result
                rows_affected = int(result.split()[-1]) if result else 0

                logger.info(f"Marked {rows_affected} old messages as deleted")
                return rows_affected

        except Exception as e:
            logger.error(f"Failed to cleanup old messages: {e}")
            return 0
