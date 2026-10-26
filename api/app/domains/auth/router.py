"""Auth (spec §3.1) — the one domain that is fully synchronous.

Refresh tokens rotate: every /refresh revokes the presented token and issues a
new pair, so a stolen refresh token stops working as soon as either party uses
it. /logout revokes the presented refresh token.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ...config import get_settings
from ...core.ratelimit import limit
from ...db import get_db
from ...models import User, RevokedToken
from ...security import hash_password, verify_password, decode_token, token_pair
from ...schemas.auth import SignupIn, LoginIn, AppleIn, TokenPair, RefreshIn, LogoutIn, RegionIn
from . import apple

settings = get_settings()
router = APIRouter(prefix="/v1/auth", tags=["auth"])
_rl = limit("auth", settings.auth_rate_limit_per_min)

# countries that default to imperial units; everyone else gets metric
_IMPERIAL = {"US", "LR", "MM"}


def apply_region(user: User, region: RegionIn) -> None:
    if region.locale:
        user.locale = region.locale
    if region.country:
        user.country = region.country.upper()
    if region.timezone:
        user.timezone = region.timezone
    if region.units:
        user.units = region.units
    elif region.country:
        user.units = "imperial" if region.country.upper() in _IMPERIAL else "metric"


def _new_user(db: Session, email: str, region: RegionIn, **fields) -> User:
    from ..billing.service import start_trial
    user = User(email=email.lower(), **fields)
    apply_region(user, region)
    start_trial(user)
    db.add(user); db.commit(); db.refresh(user)
    return user


@router.post("/signup", response_model=TokenPair, status_code=201, dependencies=[Depends(_rl)])
def signup(body: SignupIn, db: Session = Depends(get_db)) -> TokenPair:
    if len(body.password) < settings.min_password_length:
        raise HTTPException(422,
                            f"Password must be at least {settings.min_password_length} characters")
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = _new_user(db, body.email, body, password_hash=hash_password(body.password),
                     auth_provider="email", display_name=body.display_name)
    return TokenPair(**token_pair(str(user.id)))


@router.post("/login", response_model=TokenPair, dependencies=[Depends(_rl)])
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad credentials")
    return TokenPair(**token_pair(str(user.id)))


@router.post("/apple", response_model=TokenPair, dependencies=[Depends(_rl)])
def sign_in_with_apple(body: AppleIn, db: Session = Depends(get_db)) -> TokenPair:
    try:
        claims = apple.verify_identity_token(body.identity_token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Apple identity token")

    user = db.scalar(select(User).where(User.apple_sub == claims["sub"]))
    email = (claims.get("email") or "").lower()
    if user is None and email and str(claims.get("email_verified")).lower() == "true":
        # link to an existing email account only when Apple vouches for the address
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.apple_sub = claims["sub"]
            db.commit()
    if user is None:
        # an address Apple didn't verify, or that belongs to another account, is
        # never used as this account's login email
        if not email or db.scalar(select(User).where(User.email == email)):
            email = f"{claims['sub']}@appleid.sylia.invalid"
        user = _new_user(db, email, body,
                         apple_sub=claims["sub"], auth_provider="apple",
                         display_name=body.display_name)
    return TokenPair(**token_pair(str(user.id)))


def _decode_refresh(token: str) -> dict:
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise ValueError("wrong token type")
        return payload
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")


def _revoke(db: Session, payload: dict) -> None:
    if db.get(RevokedToken, payload["jti"]) is None:
        db.add(RevokedToken(jti=payload["jti"],
                            expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc)))
        db.commit()


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(_rl)])
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenPair:
    payload = _decode_refresh(body.refresh_token)
    if db.get(RevokedToken, payload["jti"]) is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
    if db.get(User, uuid.UUID(payload["sub"])) is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    _revoke(db, payload)
    return TokenPair(**token_pair(payload["sub"]))


@router.post("/logout", status_code=204)
def logout(body: LogoutIn | None = None, db: Session = Depends(get_db)) -> None:
    if body and body.refresh_token:
        try:
            _revoke(db, decode_token(body.refresh_token))
        except Exception:
            pass   # an already-invalid token is as logged out as it gets
    return None
