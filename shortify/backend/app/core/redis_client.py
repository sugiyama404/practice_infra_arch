"""Redis client helpers."""

from __future__ import annotations

import importlib
import os
from typing import Any


def create_client() -> Any:
    """Instantiate a Redis client configured from environment variables."""
    try:
        redis_module = importlib.import_module("redis.asyncio")
    except ImportError as exc:  # pragma: no cover - redis provided at runtime
        raise RuntimeError("redis.asyncio is required but not installed") from exc

    redis_cls = getattr(redis_module, "Redis")
    return redis_cls(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


def base_url(default: str) -> str:
    """Return the externally reachable base URL for the service."""
    return os.getenv("BASE_URL", default).rstrip("/")
