import os


class Config:
    """WebSocket Server Configuration"""

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    # Server Identity
    WS_SERVER_ID: str = os.getenv("WS_SERVER_ID", "ws_default")

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))

    # WebSocket Settings
    WEBSOCKET_TIMEOUT: int = int(os.getenv("WEBSOCKET_TIMEOUT", "3600"))  # 1 hour
    PING_INTERVAL: int = int(os.getenv("PING_INTERVAL", "30"))  # 30 seconds
    PING_TIMEOUT: int = int(os.getenv("PING_TIMEOUT", "10"))  # 10 seconds

    # Connection Management
    MAX_CONNECTIONS_PER_USER: int = int(os.getenv("MAX_CONNECTIONS_PER_USER", "5"))

    # Redis Key Patterns
    PRESENCE_KEY_PATTERN: str = "presence:{user_id}"
    SESSION_KEY_PATTERN: str = "session:{user_id}:{device_id}"

    @property
    def websocket_config(self) -> dict:
        """Get WebSocket server configuration"""
        return {
            "ping_interval": self.PING_INTERVAL,
            "ping_timeout": self.PING_TIMEOUT,
            "close_timeout": 10,
            "max_size": 2**20,  # 1MB
            "max_queue": 32,
            "read_limit": 2**16,  # 64KB
            "write_limit": 2**16,  # 64KB
        }


config = Config()
