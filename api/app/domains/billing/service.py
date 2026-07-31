"""Billing + affiliate logic (spec §3.7).

Two responsibilities:
  * Subscription lifecycle via Stripe. The webhook is the SOURCE OF TRUTH — we
    never trust the client to say "I paid"; we reconcile from Stripe events.
    Stripe is an optional import; without it (dev/tests) checkout returns a stub
    URL and status is driven by the local trial window, so the flow is testable.
  * The fit-gated affiliate: a product is only ever written as a recommendation
    if its fit_score clears the threshold. The gate is enforced HERE, at write
    time — so a low-fit product can never reach the user even via a bug upstream.
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

# a product must fit the user at least this well to ever be surfaced
AFFILIATE_FIT_THRESHOLD = 0.6


def stripe_available() -> bool:
    return _HAS_STRIPE and bool(settings.stripe_secret_key)


def create_checkout_session(user_email: str, user_id: str) -> dict:
    """Return {checkout_url, mode}. Real Stripe session when configured, else stub."""
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
        subscription_data={"trial_period_days": settings.trial_days},
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


def status_for(user) -> dict:
    """Effective subscription status. Trial is time-boxed locally; paid state is
    whatever the webhook last reconciled onto the user."""
    now = datetime.now(timezone.utc)
    trial_ends = user.trial_ends_at
    if trial_ends and trial_ends.tzinfo is None:
        trial_ends = trial_ends.replace(tzinfo=timezone.utc)
    in_trial = user.subscription_status == "trial" and trial_ends and trial_ends > now
    entitled = user.subscription_status == "active" or bool(in_trial)
    return {
        "status": user.subscription_status,
        "entitled": entitled,
        "in_trial": bool(in_trial),
        "trial_ends_at": trial_ends.isoformat() if trial_ends else None,
        "price_usd": settings.subscription_price_usd,
    }


def start_trial(user) -> None:
    if user.trial_ends_at is None:
        user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=settings.trial_days)
        user.subscription_status = "trial"


# ── fit-gated affiliate ──────────────────────────────────────────────────────
def gate_affiliate(candidates: list[dict]) -> list[dict]:
    """Keep only products that clear the fit threshold. Enforced at write time so
    an under-fit product can never be surfaced. Each candidate: {..., fit_score}."""
    return [c for c in candidates if (c.get("fit_score") or 0) >= AFFILIATE_FIT_THRESHOLD]
