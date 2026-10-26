"""Celery app. CV/LLM work runs here, never inline in a request (spec §1.1)."""
import socket
from urllib.parse import urlparse

from celery import Celery
from ..config import get_settings

settings = get_settings()
celery_app = Celery("sylia", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]


def _broker_reachable(url: str, timeout: float = 0.5) -> bool:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "localhost", parsed.port or 6379), timeout):
            return True
    except OSError:
        return False


# No broker → run tasks inline in the API process, so dev, tests and a single
# API-only deployment need zero infra. Without this `.delay()` blocks on
# connection retries whenever celery is installed but Redis isn't running.
# Set REQUIRE_REDIS=true once a separate worker runs: then a missing broker fails.
if not settings.require_redis and not _broker_reachable(settings.redis_url):
    celery_app.conf.task_always_eager = True
