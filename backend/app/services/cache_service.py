"""
Feature 1.2: Redis Caching Service.

Provides asynchronous get, set, delete, and pattern invalidation.
Includes a silent fallback mechanism if Redis is disabled or offline.
"""

from __future__ import annotations

import json
import logging
from typing import Any
import redis.asyncio as aioredis

from backend.app.core.config import settings
from backend.app.core.logging import get_logger, log_once

logger = get_logger(__name__)


class CacheService:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._offline_logged = False

    @property
    def client(self) -> aioredis.Redis | None:
        if not settings.enable_caching:
            return None

        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=2.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True,
                )
            except Exception as exc:
                if not self._offline_logged:
                    logger.warning("Redis client initialization failed: %s. Caching will be bypassed.", exc)
                    self._offline_logged = True
                return None
        return self._redis

    async def get(self, key: str) -> Any | None:
        """Retrieve and deserialize a JSON-encoded value from the cache."""
        redis_client = self.client
        if redis_client is None:
            return None

        try:
            val = await redis_client.get(key)
            if val is not None:
                return json.loads(val)
        except Exception as exc:
            log_once(
                logger,
                logging.WARNING,
                f"redis_get_failed:{key}",
                "Redis GET failed for key %s: %s",
                key,
                exc,
            )
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Serialize and set a value in cache with a defined TTL in seconds."""
        redis_client = self.client
        if redis_client is None:
            return False

        try:
            payload = json.dumps(value, default=str)
            await redis_client.set(key, payload, ex=ttl)
            return True
        except Exception as exc:
            log_once(
                logger,
                logging.WARNING,
                f"redis_set_failed:{key}",
                "Redis SET failed for key %s: %s",
                key,
                exc,
            )
        return False

    async def delete(self, key: str) -> bool:
        """Delete a single key from cache."""
        redis_client = self.client
        if redis_client is None:
            return False

        try:
            await redis_client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Redis DELETE failed for key %s: %s", key, exc)
        return False

    async def delete_pattern(self, pattern: str) -> bool:
        """Invalidate all keys matching a pattern using SCAN."""
        redis_client = self.client
        if redis_client is None:
            return False

        try:
            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await redis_client.delete(*keys)
                logger.info("Invalidated cache keys matching pattern '%s': count=%d", pattern, len(keys))
            return True
        except Exception as exc:
            logger.warning("Redis delete_pattern failed for pattern %s: %s", pattern, exc)
        return False


cache_service = CacheService()
