"""Integrations & Billing (spec §3.7). Stripe webhook is the source of truth."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ...db import get_db
from ...deps import get_current_user
from ...models import User

router = APIRouter(prefix="/v1", tags=["billing"])


@router.get("/integrations/weather/today")
def weather_today(lat: float | None = None, lon: float | None = None,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..integrations.weather import get_today_weather
    return get_today_weather(db, lat, lon)


@router.get("/integrations/calendar/today-signal")
def calendar_signal(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..integrations.calendar import formality_from_events, fetch_today_events
    from ...models import CalendarConnection
    from sqlalchemy import select
    cal = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id))
    from ...core.crypto import decrypt
    events = fetch_today_events(decrypt(cal.access_token_encrypted)) if cal else []
    return formality_from_events(events, cal.category_mapping if cal else None)


@router.post("/billing/checkout-session")
def checkout(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from ..billing.service import create_checkout_session
    return create_checkout_session(user.email, str(user.id))


@router.post("/billing/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe is the source of truth. Verify signature, then reconcile the user's
    subscription_status from the event."""
    from ..billing.service import verify_webhook
    from sqlalchemy import select
    raw = await request.body()
    event = verify_webhook(raw, request.headers.get("stripe-signature"))
    if event is None:
        return {"received": True, "verified": False}

    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    user_id = (obj.get("metadata") or {}).get("user_id")
    if user_id:
        u = db.get(User, __import__("uuid").UUID(user_id))
        if u:
            if etype in ("customer.subscription.created", "customer.subscription.updated",
                         "checkout.session.completed"):
                u.subscription_status = "active"
            elif etype in ("customer.subscription.deleted",):
                u.subscription_status = "canceled"
            elif etype == "invoice.payment_failed":
                u.subscription_status = "past_due"
            db.commit()
    return {"received": True, "verified": True}


@router.get("/billing/status")
def status(user: User = Depends(get_current_user)):
    from ..billing.service import status_for
    return status_for(user)


@router.get("/affiliate/recommendations")
def affiliate(outfit_id: str | None = None, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    """Fit-gated: only products clearing the fit threshold are ever returned.
    (Candidate sourcing is a later build; the gate + shape are enforced now.)"""
    from ..billing.service import gate_affiliate
    candidates: list[dict] = []   # populated by the gap-analysis/retailer sourcing step
    return {"recommendations": gate_affiliate(candidates),
            "disclosure": "Sylia may earn a commission on purchases."}


@router.post("/integrations/calendar/connect")
def connect_calendar(payload: dict, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Store Google OAuth tokens ENCRYPTED at rest (hardening). Client sends the
    tokens obtained from the OAuth flow; we never persist them in plaintext."""
    from ...core.crypto import encrypt
    from ...models import CalendarConnection
    from sqlalchemy import select
    conn = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id))
    if conn is None:
        conn = CalendarConnection(user_id=user.id, provider="google")
        db.add(conn)
    conn.access_token_encrypted = encrypt(payload.get("access_token"))
    conn.refresh_token_encrypted = encrypt(payload.get("refresh_token"))
    if "category_mapping" in payload:
        conn.category_mapping = payload["category_mapping"]
    db.commit()
    return {"connected": True, "provider": "google"}
