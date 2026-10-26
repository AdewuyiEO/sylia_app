"""Job-handle pattern (spec §3): CV/LLM endpoints enqueue and return a job_id.

Status lives in the shared KV store (Redis in prod), so the API process and the
Celery worker see the same job. The API contract (202 + job_id, then poll
GET .../jobs/{id}) never changes.
"""
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from .kv import kv

_TTL = 24 * 3600


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"          # queued|processing|done|failed
    result: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


class JobStore:
    @staticmethod
    def _key(job_id: str) -> str:
        return f"job:{job_id}"

    def create(self, kind: str, **meta: Any) -> Job:
        job = Job(id=str(uuid.uuid4()), kind=kind, meta=meta)
        kv.set(self._key(job.id), asdict(job), ttl=_TTL)
        return job

    def get(self, job_id: str) -> Job | None:
        raw = kv.get(self._key(job_id))
        return Job(**raw) if raw else None

    def get_owned(self, job_id: str, user_id: str) -> Job | None:
        """A job is only visible to the user who created it."""
        job = self.get(job_id)
        if job is None or job.meta.get("user_id") != user_id:
            return None
        return job

    def update(self, job_id: str, **fields: Any) -> None:
        raw = kv.get(self._key(job_id))
        if raw:
            raw.update(fields)
            kv.set(self._key(job_id), raw, ttl=_TTL)


jobs = JobStore()
