"""Object storage abstraction (spec §1.1: S3 / Cloudflare R2).

Prod: boto3 against S3 or R2 (R2 is S3-compatible via an endpoint URL).
Dev/tests: a local directory, so the whole pipeline runs with no cloud creds.
The pipeline only needs `get_bytes` / `put_bytes`; swapping backends is invisible
to callers.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..config import get_settings

settings = get_settings()
_LOCAL_ROOT = Path(os.environ.get("LOCAL_STORAGE_DIR", "./_storage"))


class _LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def get_bytes(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def put_bytes(self, key: str, data: bytes) -> str:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key


class _S3Storage:  # pragma: no cover - exercised in prod
    def __init__(self):
        import boto3
        self.bucket = settings.s3_bucket
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)

    def get_bytes(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def put_bytes(self, key: str, data: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key


def get_storage():
    # use S3/R2 when an endpoint or real bucket is configured; else local dev store
    if settings.env != "dev" or settings.s3_endpoint_url:
        try:
            return _S3Storage()
        except Exception:
            pass
    return _LocalStorage(_LOCAL_ROOT)


storage = get_storage()
