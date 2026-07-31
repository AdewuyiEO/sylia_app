"""Auth (spec §3.1) — the one domain that is fully synchronous."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from ...db import get_db
from ...models import User
from ...security import (hash_password, verify_password,
                         create_access_token, create_refresh_token, decode_token)
from ...schemas.auth import SignupIn, LoginIn, TokenPair, RefreshIn

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/signup", response_model=TokenPair, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> TokenPair:
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password) if body.password else None,
        auth_provider=body.auth_provider,
    )
    from ..billing.service import start_trial
    start_trial(user)
    db.add(user); db.commit(); db.refresh(user)
    return TokenPair(access_token=create_access_token(str(user.id)),
                     refresh_token=create_refresh_token(str(user.id)))


@router.post("/login", response_model=TokenPair)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad credentials")
    return TokenPair(access_token=create_access_token(str(user.id)),
                     refresh_token=create_refresh_token(str(user.id)))


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshIn) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token)
        assert payload.get("type") == "refresh"
        uid = payload["sub"]
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    return TokenPair(access_token=create_access_token(uid),
                     refresh_token=create_refresh_token(uid))


@router.post("/logout", status_code=204)
def logout() -> None:
    # stateless JWT: real revocation lands with a refresh-token denylist in Redis.
    return None
