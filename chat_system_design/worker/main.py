import json
import asyncio
import logging
from typing import Optional

import redis.asyncio as redis
import aio_pika
import asyncpg

from config import config
from message_processor import MessageProcessor, MessageData

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageWorker:
    """Main worker class that consumes messages from RabbitMQ and processes them"""

    def __init__(self):
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_pool: Optional[redis.Redis] = None
        self.rabbitmq_connection: Optional[aio_pika.Connection] = None
        self.rabbitmq_channel: Optional[aio_pika.Channel] = None
        self.ws_exchange: Optional[aio_pika.Exchange] = None
        self.processor: Optional[MessageProcessor] = None
        self.is_running = False

    async def initialize(self):
        """Initialize all connections and components"""
        try:
            logger.info(f"Initializing worker {config.WORKER_ID}...")

            # Database connection pool
            self.db_pool = await asyncpg.create_pool(
                config.DATABASE_URL, **config.get_database_config()
            )
            logger.info("Connected to PostgreSQL")

            # Redis connection
            self.redis_pool = redis.from_url(config.REDIS_URL)
            logger.info("Connected to Redis")

            # RabbitMQ connection
            self.rabbitmq_connection = await aio_pika.connect_robust(
                config.RABBITMQ_URL
            )
            self.rabbitmq_channel = await self.rabbitmq_connection.channel()

            # Set QoS for fair dispatching
            await self.rabbitmq_channel.set_qos(prefetch_count=config.PREFETCH_COUNT)

            # Declare message queue
            await self.rabbitmq_channel.declare_queue("messages", durable=True)

            # Declare WebSocket exchange for broadcasting
            self.ws_exchange = await self.rabbitmq_channel.declare_exchange(
                "ws_messages", aio_pika.ExchangeType.FANOUT
            )

            logger.info("Connected to RabbitMQ")

            # Initialize message processor
            self.processor = MessageProcessor(self.db_pool, self.redis_pool)
            await self.processor.initialize()
            logger.info("Message processor initialized")

            logger.info(f"Worker {config.WORKER_ID} initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize worker: {e}")
            raise

    async def close(self):
        """Close all connections"""
        logger.info("Shutting down worker...")

        self.is_running = False

        if self.processor:
            await self.processor.close()

        if self.rabbitmq_connection:
            await self.rabbitmq_connection.close()
            logger.info("Closed RabbitMQ connection")

        if self.redis_pool:
            await self.redis_pool.close()
            logger.info("Closed Redis connection")

        if self.db_pool:
            await self.db_pool.close()
            logger.info("Closed database connection pool")

        logger.info("Worker shutdown completed")

    async def process_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        """
        Process incoming message from RabbitMQ queue
        """
        async with message.process():
            try:
                # Parse message data
                raw_data = json.loads(message.body.decode())
                message_data = MessageData(**raw_data)

                logger.info(
                    f"Processing message {message_data.message_id} from user {message_data.user_id}"
                )

                # Process the message
                success = await self.processor.process_message(message_data)

                if success:
                    # Broadcast to WebSocket servers
                    ws_message = await self.processor._broadcast_to_websockets(
                        message_data
                    )

                    await self.ws_exchange.publish(
                        aio_pika.Message(json.dumps(ws_message).encode()),
                        routing_key="",
                    )

                    logger.info(
                        f"Successfully processed and broadcasted message {message_data.message_id}"
                    )
                else:
                    logger.error(f"Failed to process message {message_data.message_id}")
                    # Message will be requeued automatically due to exception

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {e}")
                # Don't requeue malformed messages
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Let the message be requeued for retry
                raise

    async def start_consuming(self):
        """Start consuming messages from RabbitMQ"""
        try:
            queue = await self.rabbitmq_channel.get_queue("messages")
            logger.info(
                f"Starting to consume messages from queue 'messages' with prefetch={config.PREFETCH_COUNT}"
            )

            self.is_running = True

            await queue.consume(self.process_message)

            # Keep the worker running
            while self.is_running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in message consumer: {e}")
            raise

    async def health_check(self) -> dict:
        """Perform health check on all connections"""
        health = {"worker_id": config.WORKER_ID, "status": "healthy", "components": {}}

        # Check database
        try:
            async with self.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health["components"]["database"] = "healthy"
        except Exception as e:
            health["components"]["database"] = f"unhealthy: {e}"
            health["status"] = "unhealthy"

        # Check Redis
        try:
            await self.redis_pool.ping()
            health["components"]["redis"] = "healthy"
        except Exception as e:
            health["components"]["redis"] = f"unhealthy: {e}"
            health["status"] = "unhealthy"

        # Check RabbitMQ
        try:
            if self.rabbitmq_connection and not self.rabbitmq_connection.is_closed:
                health["components"]["rabbitmq"] = "healthy"
            else:
                health["components"]["rabbitmq"] = "unhealthy: connection closed"
                health["status"] = "unhealthy"
        except Exception as e:
            health["components"]["rabbitmq"] = f"unhealthy: {e}"
            health["status"] = "unhealthy"

        return health

    async def get_stats(self) -> dict:
        """Get worker statistics"""
        try:
            stats = {
                "worker_id": config.WORKER_ID,
                "is_running": self.is_running,
                "config": {
                    "prefetch_count": config.PREFETCH_COUNT,
                    "db_pool_size": f"{config.DB_POOL_MIN_SIZE}-{config.DB_POOL_MAX_SIZE}",
                    "max_retries": config.MAX_RETRIES,
                },
            }

            # Add database stats
            if self.db_pool:
                stats["database"] = {
                    "size": self.db_pool.get_size(),
                    "idle": self.db_pool.get_idle_size(),
                }

            # Add Redis info
            if self.redis_pool:
                info = await self.redis_pool.info()
                stats["redis"] = {
                    "connected_clients": info.get("connected_clients"),
                    "used_memory": info.get("used_memory_human"),
                }

            return stats

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


async def cleanup_task(worker: MessageWorker):
    """Periodic cleanup task"""
    while worker.is_running:
        try:
            # Sleep for 1 hour
            await asyncio.sleep(3600)

            if worker.processor:
                # Cleanup old messages (optional)
                deleted_count = await worker.processor.cleanup_old_messages(30)
                if deleted_count > 0:
                    logger.info(
                        f"Cleanup task: marked {deleted_count} old messages as deleted"
                    )

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")


async def main():
    """Main worker function"""
    worker = MessageWorker()
    cleanup_task_handle = None

    try:
        # Initialize worker
        await worker.initialize()

        # Start cleanup task
        cleanup_task_handle = asyncio.create_task(cleanup_task(worker))

        logger.info(f"Worker {config.WORKER_ID} started and ready to process messages")

        # Start consuming messages
        await worker.start_consuming()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
    finally:
        # Cleanup
        if cleanup_task_handle:
            cleanup_task_handle.cancel()

        await worker.close()
        logger.info(f"Worker {config.WORKER_ID} stopped")


if __name__ == "__main__":
    # Handle graceful shutdown
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        exit(1)
