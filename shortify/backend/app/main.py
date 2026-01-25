"""FastAPI application for the shortify URL shortener."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from .core.base62 import encode
from .core.id_generator import SnowflakeGenerator
import hashlib
from .core.redis_client import base_url, create_client

app = FastAPI(title="shortify", version="0.1.0", debug=True)

_id_generator = SnowflakeGenerator()
_redis_client: Any | None = None


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_url: str
    slug: str


async def get_redis() -> Any:
    if _redis_client is None:
        raise HTTPException(status_code=503, detail="Cache backend is not ready")
    return _redis_client


@app.on_event("startup")
async def on_startup() -> None:
    global _redis_client
    client = create_client()
    await client.ping()  # Fail fast if Redis is unreachable.
    _redis_client = client


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if _redis_client is not None:
        await _redis_client.aclose()


@app.post("/api/v1/data/shorten", response_model=ShortenResponse)
async def shorten_url(
    payload: ShortenRequest,
    request: Request,
    redis=Depends(get_redis),
) -> ShortenResponse:
    long_url = str(payload.url)
    url_hash = hashlib.sha256(long_url.encode()).hexdigest()
    reverse_key = f"reverse-url:{url_hash}"

    existing_slug = await redis.get(reverse_key)
    service_base = base_url(str(request.base_url))
    if existing_slug:
        return ShortenResponse(
            short_url=f"{service_base}/{existing_slug}", slug=existing_slug
        )

    identifier = _id_generator.generate_id()
    slug = encode(identifier)
    key = f"url:{slug}"

    # Store both forward and reverse mappings
    await redis.set(key, long_url)
    await redis.set(reverse_key, slug)

    return ShortenResponse(short_url=f"{service_base}/{slug}", slug=slug)


@app.get("/{slug}")
async def redirect(slug: str, redis=Depends(get_redis)) -> RedirectResponse:
    key = f"url:{slug}"
    destination = await redis.get(key)
    if destination is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(destination, status_code=302)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
