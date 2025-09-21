import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "cloudmart_user")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "cloudmart_pass")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "cloudmart_saga")

    # Redis (Choreography)
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))

    # RabbitMQ (Orchestration)
    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "localhost")
    rabbitmq_port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_user: str = os.getenv("RABBITMQ_USER", "cloudmart_user")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "cloudmart_pass")
    rabbitmq_vhost: str = os.getenv("RABBITMQ_VHOST", "cloudmart_vhost")

    # Service URLs
    order_service_url: str = os.getenv("ORDER_SERVICE_URL", "http://localhost:8001")
    inventory_service_url: str = os.getenv(
        "INVENTORY_SERVICE_URL", "http://localhost:8002"
    )
    payment_service_url: str = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8003")
    shipping_service_url: str = os.getenv(
        "SHIPPING_SERVICE_URL", "http://localhost:8004"
    )
    saga_orchestrator_url: str = os.getenv(
        "SAGA_ORCHESTRATOR_URL", "http://localhost:8005"
    )

    # Application
    app_name: str = "CloudMart Saga Pattern Demo"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Saga Configuration
    saga_timeout_seconds: int = int(os.getenv("SAGA_TIMEOUT_SECONDS", "300"))
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    retry_backoff_seconds: int = int(os.getenv("RETRY_BACKOFF_SECONDS", "5"))

    # Event Configuration (Choreography)
    event_channel_prefix: str = os.getenv("EVENT_CHANNEL_PREFIX", "cloudmart.events")
    event_timeout_seconds: int = int(os.getenv("EVENT_TIMEOUT_SECONDS", "30"))

    # Message Configuration (Orchestration)
    message_queue_prefix: str = os.getenv("MESSAGE_QUEUE_PREFIX", "cloudmart.saga")
    message_timeout_seconds: int = int(os.getenv("MESSAGE_TIMEOUT_SECONDS", "30"))

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Database URL
def get_database_url() -> str:
    return f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"


# Redis URL
def get_redis_url() -> str:
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


# RabbitMQ URL
def get_rabbitmq_url() -> str:
    return f"amqp://{settings.rabbitmq_user}:{settings.rabbitmq_password}@{settings.rabbitmq_host}:{settings.rabbitmq_port}/{settings.rabbitmq_vhost}"
