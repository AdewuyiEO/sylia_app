"""Password hashing and JWT issuing/verification."""
from datetime import datetime, timedelta, timezone
import uuid

import jwt
import bcrypt

from .config import get_settings

settings = get_settings()

# bcrypt operates on bytes and caps input at 72 bytes; encode + clamp explicitly.
def _pw_bytes(pw: str) -> bytes:
    return pw.encode("utf-8")[:72]


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(_pw_bytes(pw), bcrypt.gensalt()).decode("utf-8")


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(pw), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _token(sub: str, ttl: timedelta, kind: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": sub, "type": kind, "iat": now, "exp": now + ttl, "jti": str(uuid.uuid4())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_access_token(user_id: str) -> str:
    return _token(user_id, timedelta(minutes=settings.access_token_ttl_min), "access")


def create_refresh_token(user_id: str) -> str:
    return _token(user_id, timedelta(days=settings.refresh_token_ttl_days), "refresh")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])


def token_pair(user_id: str) -> dict:
    return {"access_token": create_access_token(user_id),
            "refresh_token": create_refresh_token(user_id)}
