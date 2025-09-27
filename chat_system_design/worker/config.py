import os


class Config:
    """Worker Service Configuration"""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://chat_user:chat_pass@localhost:5432/chat_db"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    # Push Notification Server
    PN_SERVER_URL: str = os.getenv("PN_SERVER_URL", "http://localhost:8000")

    # Worker Settings
    WORKER_ID: str = os.getenv("WORKER_ID", "worker_default")
    PREFETCH_COUNT: int = int(os.getenv("PREFETCH_COUNT", "1"))

    # Database connection pool
    DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
    DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "5"))

    # Processing settings
    MESSAGE_BATCH_SIZE: int = int(os.getenv("MESSAGE_BATCH_SIZE", "10"))
    PROCESS_TIMEOUT: int = int(os.getenv("PROCESS_TIMEOUT", "30"))

    # Retry settings
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))

    @classmethod
    def get_database_config(cls) -> dict:
        """Get database connection configuration"""
        return {
            "min_size": cls.DB_POOL_MIN_SIZE,
            "max_size": cls.DB_POOL_MAX_SIZE,
            "command_timeout": cls.PROCESS_TIMEOUT,
        }


config = Config()
