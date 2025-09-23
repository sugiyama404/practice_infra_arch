import os
from typing import Optional


class Config:
    """API Server Configuration"""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://chat_user:chat_pass@localhost:5432/chat_db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # API Settings
    API_PREFIX: str = "/api"
    VERSION: str = "1.0.0"
    TITLE: str = "Chat System API"
    DESCRIPTION: str = "Stateless API server for real-time chat system"

    # Rate Limiting (future use)
    RATE_LIMIT_ENABLED: bool = (
        os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    )
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # Database connection pool
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

    @classmethod
    def get_database_config(cls) -> dict:
        """Get database connection configuration"""
        return {
            "min_size": cls.DB_POOL_MIN_SIZE,
            "max_size": cls.DB_POOL_MAX_SIZE,
            "command_timeout": 60,
        }


config = Config()
