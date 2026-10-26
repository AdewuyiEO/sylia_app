"""Shared key-value store for short-lived state: job status, onboarding sessions,
rate-limit counters.

Redis when REDIS_URL is reachable, so the API and the Celery worker (separate
processes in prod) see the same job status and sessions. Falls back to an
in-process dict outside prod so dev and tests need zero infra. Values are JSON.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Any
from urllib.parse import urlparse

from ..config import get_settings

settings = get_settings()


class _MemoryKV:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float | None, str]] = {}
        self._lock = threading.Lock()

    def _live(self, key: str) -> str | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        exp, val = hit
        if exp is not None and exp < time.time():
            self._data.pop(key, None)
            return None
        return val

    def get(self, key: str) -> Any:
        with self._lock:
            raw = self._live(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl if ttl else None, json.dumps(value))

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def incr(self, key: str, ttl: int) -> int:
        """Increment a counter; the TTL is set when the counter is created."""
        with self._lock:
            raw = self._live(key)
            if raw is None:
                self._data[key] = (time.time() + ttl, "1")
                return 1
            exp, _ = self._data[key]
            n = int(raw) + 1
            self._data[key] = (exp, str(n))
            return n


class _RedisKV:  # pragma: no cover - exercised with a live Redis
    def __init__(self, url: str) -> None:
        import redis
        self.r = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Any:
        raw = self.r.get(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self.r.set(key, json.dumps(value), ex=ttl)

    def delete(self, key: str) -> None:
        self.r.delete(key)

    def incr(self, key: str, ttl: int) -> int:
        pipe = self.r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl, nx=True)
        n, _ = pipe.execute()
        return int(n)


def _reachable(url: str, timeout: float = 0.5) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "localhost", parsed.port or 6379), timeout):
            return True
    except OSError:
        return False


def _make():
    if settings.redis_url and _reachable(settings.redis_url):
        try:
            return _RedisKV(settings.redis_url)
        except Exception:
            pass
    if settings.env == "prod" and settings.require_redis:
        raise RuntimeError("REDIS_URL is unreachable and REQUIRE_REDIS is set")
    return _MemoryKV()


kv = _make()
