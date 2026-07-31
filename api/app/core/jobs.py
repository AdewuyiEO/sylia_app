"""Job-handle pattern (spec §3): CV/LLM endpoints enqueue and return a job_id.

In-memory store for dev/tests; swap for Redis-backed status in prod. The API
contract (202 + job_id, then poll GET .../jobs/{id}) never changes.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"          # queued|processing|done|failed
    result: Any = None
    error: str | None = None
    meta: dict = field(default_factory=dict)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create(self, kind: str, **meta: Any) -> Job:
        job = Job(id=str(uuid.uuid4()), kind=kind, meta=meta)
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> None:
        job = self._jobs.get(job_id)
        if job:
            for k, v in fields.items():
                setattr(job, k, v)


jobs = JobStore()
