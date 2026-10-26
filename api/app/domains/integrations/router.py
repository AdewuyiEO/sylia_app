"""Integrations: weather + Google Calendar (read-only, one formality signal).

Calendar connect is a server-side OAuth code flow: the app opens /oauth/start's
URL in a browser session, Google redirects to our callback, we exchange the code
and store the tokens encrypted, then bounce back into the app via its scheme.
The tokens never touch the phone.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...db import get_db
from ...deps import get_current_user
from ...models import User, CalendarConnection
from . import calendar as cal

settings = get_settings()
router = APIRouter(prefix="/v1/integrations", tags=["integrations"])
APP_RETURN = "sylia://calendar"


@router.get("/weather/today")
def weather_today(lat: float | None = None, lon: float | None = None,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from .weather import get_today_weather
    return get_today_weather(db, lat, lon)


def _conn(db: Session, user: User) -> CalendarConnection | None:
    return db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id))


@router.get("/calendar")
def calendar_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _conn(db, user)
    return {"connected": bool(conn and conn.access_token_encrypted),
            "provider": conn.provider if conn else None,
            "available": cal.oauth_configured(),
            "category_mapping": conn.category_mapping if conn else {}}


@router.get("/calendar/today-signal")
def calendar_signal(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _conn(db, user)
    return cal.formality_from_events(cal.events_for_user(db, conn),
                                     conn.category_mapping if conn else None)


@router.get("/calendar/oauth/start")
def oauth_start(user: User = Depends(get_current_user)):
    if not cal.oauth_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Calendar connect isn't configured yet")
    state = jwt.encode({"sub": str(user.id), "kind": "gcal_state",
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
                       settings.jwt_secret, algorithm=settings.jwt_alg)
    params = {"client_id": settings.google_client_id, "redirect_uri": cal.redirect_uri(),
              "response_type": "code", "scope": cal.CALENDAR_SCOPE, "access_type": "offline",
              "prompt": "consent", "include_granted_scopes": "true", "state": state}
    return {"auth_url": f"{cal.GOOGLE_AUTH_URL}?{urlencode(params)}", "return_url": APP_RETURN}


@router.get("/calendar/oauth/callback", include_in_schema=False)
def oauth_callback(state: str, code: str | None = None, error: str | None = None,
                   db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_alg])
        if claims.get("kind") != "gcal_state":
            raise ValueError
        user = db.get(User, __import__("uuid").UUID(claims["sub"]))
        if user is None:
            raise ValueError
    except Exception:
        return RedirectResponse(f"{APP_RETURN}?status=error&reason=state")
    if error or not code:
        return RedirectResponse(f"{APP_RETURN}?status=cancelled")
    try:
        tokens = cal.exchange_code(code)
    except Exception:
        return RedirectResponse(f"{APP_RETURN}?status=error&reason=exchange")

    conn = _conn(db, user)
    if conn is None:
        conn = CalendarConnection(user_id=user.id, provider="google")
        db.add(conn)
    cal.store_tokens(conn, tokens)
    db.commit()
    return RedirectResponse(f"{APP_RETURN}?status=connected")


@router.patch("/calendar/mapping")
def update_mapping(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """User overrides: {"keyword": formality 1-5}, e.g. {"date night": 4}."""
    conn = _conn(db, user)
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar not connected")
    mapping = {}
    for k, v in (payload.get("category_mapping") or {}).items():
        if not isinstance(v, int) or not 1 <= v <= 5:
            raise HTTPException(422, "formality must be 1-5")
        mapping[str(k)[:60].lower()] = v
    conn.category_mapping = mapping
    db.commit()
    return {"category_mapping": mapping}


@router.delete("/calendar", status_code=204)
def disconnect(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _conn(db, user)
    if conn is None:
        return None
    from ...core.crypto import decrypt
    token = decrypt(conn.refresh_token_encrypted) or decrypt(conn.access_token_encrypted)
    if token:
        try:
            import httpx
            httpx.post(cal.GOOGLE_REVOKE_URL, params={"token": token}, timeout=5.0)
        except Exception:
            pass   # best effort; we drop our copy regardless
    db.delete(conn)
    db.commit()
    return None
