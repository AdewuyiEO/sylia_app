"""Fixed-window rate limiting on the shared KV store (Redis in prod).

Used on unauthenticated endpoints (signup/login/refresh) to blunt credential
stuffing. Keyed by client IP + bucket name.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request, status

from .kv import kv


def limit(bucket: str, per_minute: int):
    def dep(request: Request) -> None:
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() \
            or (request.client.host if request.client else "unknown")
        window = int(time.time() // 60)
        n = kv.incr(f"rl:{bucket}:{ip}:{window}", ttl=61)
        if n > per_minute:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "Too many attempts. Try again in a minute.")
    return dep
