"""Sign in with Apple: verify the identity token the iOS app receives.

The token is an RS256 JWT signed with one of Apple's rotating keys. We check the
signature against Apple's JWKS, the issuer, and that the audience is our bundle
id. `sub` is the stable Apple user id; `email` may be a private relay address.
"""
from __future__ import annotations

from functools import lru_cache

import jwt

from ...config import get_settings

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(APPLE_JWKS_URL, cache_keys=True)


def signing_key_for(token: str):
    """Seam for tests: returns the public key that signed `token`."""
    return _jwks_client().get_signing_key_from_jwt(token).key


def verify_identity_token(token: str) -> dict:
    """Return the verified claims, or raise ValueError."""
    settings = get_settings()
    try:
        claims = jwt.decode(token, signing_key_for(token), algorithms=["RS256"],
                            audience=settings.apple_bundle_id, issuer=APPLE_ISSUER)
    except Exception as e:
        raise ValueError(f"invalid Apple identity token: {e}") from e
    if not claims.get("sub"):
        raise ValueError("Apple identity token has no subject")
    return claims
