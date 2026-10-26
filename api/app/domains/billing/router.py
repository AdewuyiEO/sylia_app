"""Billing (spec §3.7). Store/Stripe webhooks are the source of truth."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User, Subscription
from . import service

router = APIRouter(prefix="/v1/billing", tags=["billing"])


def _sub(db: Session, user_id) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if sub is None:
        sub = Subscription(user_id=user_id)
        db.add(sub)
    return sub


@router.get("/status")
def billing_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sub = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
    return service.status_for(user, sub)


@router.post("/checkout-session")
def checkout(user: User = Depends(get_current_user)):
    """Web only. The iOS/Android apps buy through the store SDK (RevenueCat)."""
    return service.create_checkout_session(user.email, str(user.id))


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe (web). Verify signature, then reconcile subscription_status."""
    raw = await request.body()
    event = service.verify_webhook(raw, request.headers.get("stripe-signature"))
    if event is None:
        return {"received": True, "verified": False}

    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    user_id = (obj.get("metadata") or {}).get("user_id")
    if user_id:
        u = db.get(User, uuid.UUID(user_id))
        if u:
            sub = _sub(db, u.id)
            sub.provider = "stripe"
            if etype in ("customer.subscription.created", "customer.subscription.updated",
                         "checkout.session.completed"):
                u.subscription_status = sub.status = "active"
                if obj.get("current_period_end"):
                    from datetime import datetime, timezone
                    sub.current_period_end = datetime.fromtimestamp(obj["current_period_end"], timezone.utc)
                sub.stripe_customer_id = obj.get("customer") or sub.stripe_customer_id
            elif etype == "customer.subscription.deleted":
                u.subscription_status = sub.status = "canceled"
            elif etype == "invoice.payment_failed":
                u.subscription_status = sub.status = "past_due"
            db.commit()
    return {"received": True, "verified": True}


@router.post("/revenuecat/webhook")
async def revenuecat_webhook(request: Request, db: Session = Depends(get_db)):
    """App Store / Play Store purchases, via RevenueCat. The app identifies the
    buyer with our user id (Purchases.logIn(user_id)), so app_user_id is our id."""
    if not service.revenuecat_authorized(request.headers.get("authorization")):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bad webhook authorization")
    event = (await request.json()).get("event") or {}
    candidates = [event.get("app_user_id"), event.get("original_app_user_id"),
                  *(event.get("aliases") or [])]
    user = None
    for cid in candidates:
        try:
            user = db.get(User, uuid.UUID(str(cid)))
        except (ValueError, TypeError):
            continue
        if user:
            break
    if user is None:
        return {"received": True, "applied": False, "reason": "unknown user"}
    applied = service.apply_revenuecat_event(event, user, _sub(db, user.id))
    db.commit()
    return {"received": True, "applied": applied}
