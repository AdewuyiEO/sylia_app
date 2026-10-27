"""Object storage abstraction (spec §1.1: S3 / Cloudflare R2).

Prod: boto3 against S3 or R2 (R2 is S3-compatible via an endpoint URL). Phones
upload straight to the bucket with a presigned PUT and read images back with
presigned GETs, so image bytes never pass through the API.
Disk (dev, tests, and single-VPS deploys with STORAGE_BACKEND=disk): a local
directory, with short-lived signed URLs served by the API itself
(/v1/uploads/local, /v1/files) so the client flow is identical.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import jwt

from ..config import get_settings

settings = get_settings()
_LOCAL_ROOT = Path(os.environ.get("LOCAL_STORAGE_DIR", "./_storage"))


def _sign(claims: dict, ttl_s: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(seconds=ttl_s)
    return jwt.encode({**claims, "exp": exp}, settings.jwt_secret, algorithm=settings.jwt_alg)


def verify_local_token(token: str, kind: str) -> dict:
    """Decode a signed local-storage URL token; raises on expiry/tamper/wrong kind."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    if claims.get("kind") != kind:
        raise ValueError("wrong token kind")
    return claims


class _LocalStorage:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("key escapes storage root")
        return p

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValueError:
            return False

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except ValueError:
            pass

    def presign_put(self, key: str, content_type: str) -> dict:
        token = _sign({"kind": "put", "key": key, "ct": content_type}, settings.upload_url_ttl_s)
        return {"url": f"{settings.public_base_url}/v1/uploads/local?token={quote(token)}",
                "method": "PUT", "headers": {"Content-Type": content_type}}

    def presign_get(self, key: str, ttl_s: int = 3600) -> str:
        token = _sign({"kind": "get", "key": key}, ttl_s)
        return f"{settings.public_base_url}/v1/files?token={quote(token)}"


class _S3Storage:  # pragma: no cover - exercised in prod
    def __init__(self):
        import boto3
        self.bucket = settings.s3_bucket
        self.client = boto3.client("s3", endpoint_url=settings.s3_endpoint_url)

    def get_bytes(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        return key

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def presign_put(self, key: str, content_type: str) -> dict:
        url = self.client.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=settings.upload_url_ttl_s)
        return {"url": url, "method": "PUT", "headers": {"Content-Type": content_type}}

    def presign_get(self, key: str, ttl_s: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=ttl_s)


def get_storage():
    if settings.storage_backend == "disk":
        return _LocalStorage(_LOCAL_ROOT)
    if settings.storage_backend == "s3":
        return _S3Storage()
    # auto: S3/R2 when an endpoint is configured or outside dev; else the local dev store
    if settings.env != "dev" or settings.s3_endpoint_url:
        try:
            return _S3Storage()
        except Exception:
            pass
    return _LocalStorage(_LOCAL_ROOT)


storage = get_storage()


def is_local() -> bool:
    return isinstance(storage, _LocalStorage)
