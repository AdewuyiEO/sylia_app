"""Celery app. CV/LLM work runs here, never inline in a request (spec §1.1)."""
from celery import Celery
from ..config import get_settings

settings = get_settings()
celery_app = Celery("sylia", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
