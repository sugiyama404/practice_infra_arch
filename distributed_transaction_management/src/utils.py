import time
import logging
from urllib.parse import urlparse
import socket

logger = logging.getLogger(__name__)


def wait_for_tcp(
    host: str, port: int, timeout: int = 60, interval: float = 1.0
) -> bool:
    """Wait until a TCP port at host:port is accepting connections."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=2):
                logger.info(f"Connection to {host}:{port} succeeded")
                return True
        except Exception:
            time.sleep(interval)
    logger.error(f"Timeout waiting for {host}:{port}")
    return False


def wait_for_database(db_url: str, timeout: int = 60) -> bool:
    """Parse a SQLAlchemy DB URL and wait for the underlying TCP port to be ready."""
    # Expecting URLs like mysql+pymysql://user:pass@host:port/dbname
    parsed = urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 3306
    logger.info(f"Waiting for database at {host}:{port}")
    return wait_for_tcp(host, port, timeout=timeout)


def wait_for_redis(redis_url: str, timeout: int = 30) -> bool:
    parsed = urlparse(redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    logger.info(f"Waiting for redis at {host}:{port}")
    return wait_for_tcp(host, port, timeout=timeout)
