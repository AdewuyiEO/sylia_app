"""Photo uploads: the phone asks for a signed URL, PUTs the image straight to
storage, then registers the returned key with the closet or body-scan endpoint.

Keys are namespaced per user (uploads/{user_id}/{purpose}/...), and every
endpoint that accepts a key checks that prefix, so one user can never point the
pipeline at another user's photo.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ...config import get_settings
from ...core.storage import storage, is_local, verify_local_token
from ...deps import get_current_user
from ...models import User

settings = get_settings()
router = APIRouter(prefix="/v1", tags=["uploads"])

PURPOSES = ("closet", "body", "tryon")
_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic"}


class UploadIn(BaseModel):
    purpose: str = Field(pattern="^(closet|body|tryon)$")
    content_type: str = "image/jpeg"


def key_prefix(user_id, purpose: str) -> str:
    return f"uploads/{user_id}/{purpose}/"


def assert_owned_key(user: User, key: str | None, purpose: str) -> str:
    """Reject keys outside the caller's own upload namespace, or never uploaded."""
    if not key or not key.startswith(key_prefix(user.id, purpose)) or ".." in key:
        raise HTTPException(422, "Unknown upload key")
    if not storage.exists(key):
        raise HTTPException(422, "Upload not found — PUT the image first")
    return key


@router.post("/uploads", status_code=201)
def create_upload(body: UploadIn, user: User = Depends(get_current_user)):
    ext = _EXT.get(body.content_type)
    if ext is None:
        raise HTTPException(422,
                            f"content_type must be one of {sorted(_EXT)}")
    key = f"{key_prefix(user.id, body.purpose)}{uuid.uuid4()}.{ext}"
    return {"key": key, "upload": storage.presign_put(key, body.content_type),
            "max_bytes": settings.upload_max_bytes, "expires_in": settings.upload_url_ttl_s}


@router.put("/uploads/local", status_code=204, include_in_schema=False)
async def put_local(token: str, request: Request) -> Response:
    """Signed PUT for disk storage (dev, or a single-VPS deploy)."""
    if not is_local():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        claims = verify_local_token(token, "put")
    except Exception:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Upload URL invalid or expired")
    if request.headers.get("content-type", "").split(";")[0] != claims["ct"]:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Content-Type mismatch")
    data = await request.body()
    if not data or len(data) > settings.upload_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Image empty or too large")
    storage.put_bytes(claims["key"], data, claims["ct"])
    return Response(status_code=204)


@router.get("/files", include_in_schema=False)
def get_local(token: str) -> Response:
    """Signed GET for disk storage (dev, or a single-VPS deploy)."""
    if not is_local():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        key = verify_local_token(token, "get")["key"]
        data = storage.get_bytes(key)
    except Exception:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    ext = key.rsplit(".", 1)[-1].lower()
    media = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "heic": "image/heic"}
    return Response(data, media_type=media.get(ext, "application/octet-stream"),
                    headers={"Cache-Control": "private, max-age=3600"})
