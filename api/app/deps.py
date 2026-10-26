"""Shared FastAPI dependencies: DB session + current authenticated user."""
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .db import get_db
from .security import decode_token
from .models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_entitled(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Pro features (trial or paid). 402 tells the app to show the paywall."""
    from sqlalchemy import select
    from .models import Subscription
    from .domains.billing.service import status_for
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    if not status_for(user, sub)["entitled"]:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Sylia Pro required")
    return user
