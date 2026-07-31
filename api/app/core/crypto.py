"""Symmetric encryption for stored secrets (spec hardening).

Calendar OAuth tokens are third-party credentials; storing them plaintext in
Postgres is unacceptable. We encrypt them at rest with Fernet (AES-128-CBC +
HMAC), keyed from a dedicated secret. The key is derived from ENCRYPTION_KEY if
set (prod), else deterministically from JWT_SECRET for dev so the app still runs.
Rotate by re-encrypting; Fernet supports MultiFernet for rotation later.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import get_settings

settings = get_settings()


def _key() -> bytes:
    raw = (getattr(settings, "encryption_key", None) or settings.jwt_secret).encode()
    # Fernet needs a 32-byte urlsafe-base64 key; derive one deterministically
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())


_fernet = Fernet(_key())


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet.decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None
