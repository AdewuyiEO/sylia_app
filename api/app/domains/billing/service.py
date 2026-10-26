"""Billing logic (spec §3.7).

Subscriptions are sold through the stores: Apple In-App Purchase on iOS and
Google Play Billing on Android (required for digital subscriptions sold inside
the apps, worldwide), with RevenueCat in front of both for receipt validation,
regional pricing and tax. Stripe stays for web checkout.

Either way a server-side webhook is the SOURCE OF TRUTH — we never trust the
client to say "I paid". Without keys (dev/tests) checkout returns a stub URL and
entitlement is driven by the local trial window, so the flow stays testable.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from ...config import get_settings

settings = get_settings()

try:
    import stripe
    _HAS_STRIPE = True
except Exception:
    _HAS_STRIPE = False


def stripe_available() -> bool:
    return _HAS_STRIPE and bool(settings.stripe_secret_key)


def create_checkout_session(user_email: str, user_id: str) -> dict:
    """Web checkout. Return {checkout_url, mode}. Real Stripe session when configured, else stub."""
    if not stripe_available():
        return {"checkout_url": f"https://example.test/checkout/{user_id}", "mode": "stub"}
    import stripe
    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user_email,
        line_items=[{"price_data": {
            "currency": "usd",
            "product_data": {"name": "Sylia Pro"},
            "recurring": {"interval": "month"},
            "unit_amount": settings.subscription_price_usd * 100,
        }, "quantity": 1}],
        subscription_data={"trial_period_days": settings.trial_days,
                           "metadata": {"user_id": user_id}},
        success_url="sylia://billing/success",
        cancel_url="sylia://billing/cancel",
        metadata={"user_id": user_id},
    )
    return {"checkout_url": session.url, "mode": "live", "session_id": session.id}


def verify_webhook(payload: bytes, sig_header: str | None) -> dict | None:
    """Verify + parse a Stripe event. Returns the event dict, or None if invalid."""
    if not stripe_available() or not settings.stripe_webhook_secret:
        return None
    import stripe
    try:
        return stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret)
    except Exception:
        return None


# ── RevenueCat (App Store + Play Store) ──────────────────────────────────────
# event type -> resulting status. CANCELLATION only turns off auto-renew: the
# user keeps access until EXPIRATION, so it doesn't change status.
REVENUECAT_STATUS = {
    "INITIAL_PURCHASE": "active", "RENEWAL": "active", "PRODUCT_CHANGE": "active",
    "UNCANCELLATION": "active", "NON_RENEWING_PURCHASE": "active",
    "SUBSCRIPTION_EXTENDED": "active", "TEMPORARY_ENTITLEMENT_GRANT": "active",
    "BILLING_ISSUE": "past_due", "EXPIRATION": "canceled",
}
_STORES = {"APP_STORE": "app_store", "MAC_APP_STORE": "app_store", "PLAY_STORE": "play_store",
           "STRIPE": "stripe", "RC_BILLING": "stripe", "AMAZON": "amazon"}


def revenuecat_authorized(header: str | None) -> bool:
    import hmac
    secret = settings.revenuecat_webhook_secret
    if not secret or not header:
        return False
    presented = header.removeprefix("Bearer ").strip()
    return hmac.compare_digest(presented, secret)


def apply_revenuecat_event(event: dict, user, sub) -> bool:
    """Reconcile one RevenueCat event onto the user + subscription rows.
    Returns False for events that don't change entitlement."""
    etype = event.get("type", "")
    new_status = REVENUECAT_STATUS.get(etype)
    entitlements = event.get("entitlement_ids") or []
    if entitlements and settings.revenuecat_entitlement not in entitlements:
        return False
    exp_ms = event.get("expiration_at_ms")
    if exp_ms:
        sub.current_period_end = datetime.fromtimestamp(int(exp_ms) / 1000, timezone.utc)
    sub.provider = _STORES.get(event.get("store", ""), sub.provider)
    sub.product_id = event.get("product_id") or sub.product_id
    if new_status is None:
        return etype == "CANCELLATION"
    sub.status = new_status
    user.subscription_status = new_status
    return True


def _aware(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def status_for(user, sub=None) -> dict:
    """Effective subscription status. Trial is time-boxed locally; paid state is
    whatever the webhook last reconciled, bounded by the store's expiry date."""
    now = datetime.now(timezone.utc)
    trial_ends = _aware(user.trial_ends_at)
    period_end = _aware(sub.current_period_end) if sub is not None else None
    in_trial = user.subscription_status == "trial" and trial_ends and trial_ends > now
    paid = user.subscription_status in ("active", "past_due") and (period_end is None or period_end > now)
    return {
        "status": user.subscription_status,
        "entitled": bool(paid or in_trial),
        "in_trial": bool(in_trial),
        "trial_ends_at": trial_ends.isoformat() if trial_ends else None,
        "renews_or_expires_at": period_end.isoformat() if period_end else None,
        "provider": sub.provider if sub is not None else None,
        "price_usd": settings.subscription_price_usd,   # list price; stores localise per region
    }


def start_trial(user) -> None:
    if user.trial_ends_at is None:
        user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.trial_days)
        user.subscription_status = "trial"
