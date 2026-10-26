"""Calendar signal (spec §1.1: Google Calendar read-only, ONE formality signal).

Deliberately NOT full semantic parsing for MVP. We read today's events and map
them to a single formality category 1-5 via keyword rules (the user's stored
category_mapping can override defaults). The most formal event of the day wins —
you dress for your most important meeting. No calendar connected → neutral 3.
"""
from __future__ import annotations

# default keyword → formality (1 casual … 5 black-tie). User mapping overrides.
DEFAULT_KEYWORDS: dict[str, int] = {
    "gym": 1, "workout": 1, "run": 1,
    "coffee": 2, "lunch": 2, "errand": 2,
    "standup": 3, "1:1": 3, "sync": 3, "review": 3, "office": 3,
    "client": 4, "presentation": 4, "interview": 4, "board": 4, "pitch": 4,
    "gala": 5, "wedding": 5, "ceremony": 5, "black tie": 5,
}


def formality_from_events(events: list[dict], user_mapping: dict | None = None) -> dict:
    """events: [{summary, start_iso, formality?}]. Returns the single MVP signal.

    Returns {formality_category, driver} where driver is the event that set it —
    useful for the daily-look explanation ('smart enough for your client call').
    """
    mapping = {**DEFAULT_KEYWORDS, **{k.lower(): v for k, v in (user_mapping or {}).items()}}
    best_score, driver = 3, None                      # default neutral

    for ev in events:
        summary = (ev.get("summary") or "").lower()
        score = None
        for kw, val in mapping.items():
            if kw in summary:
                score = val if score is None else max(score, val)
        if score is None:
            continue
        if driver is None or score > best_score:
            best_score, driver = score, ev.get("summary")

    return {"formality_category": best_score, "driver": driver}


def fetch_today_events(access_token: str | None) -> list[dict]:
    """Live Google Calendar read. Returns [] with no token or on error (→ neutral)."""
    if not access_token:
        return []
    try:
        import httpx
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        end = now + timedelta(hours=24)
        r = httpx.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"timeMin": now.isoformat(), "timeMax": end.isoformat(),
                    "singleEvents": "true", "orderBy": "startTime"},
            timeout=5.0,
        )
        r.raise_for_status()
        return [{"summary": i.get("summary"),
                 "start_iso": i.get("start", {}).get("dateTime")}
                for i in r.json().get("items", [])]
    except Exception:
        return []


# ── Google OAuth (read-only calendar) ────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"


def oauth_configured() -> bool:
    from ...config import get_settings
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def redirect_uri() -> str:
    from ...config import get_settings
    return f"{get_settings().public_base_url}/v1/integrations/calendar/oauth/callback"


def exchange_code(code: str) -> dict:
    """Authorization code → {access_token, refresh_token?, expires_in}. Raises on failure."""
    import httpx
    from ...config import get_settings
    s = get_settings()
    r = httpx.post(GOOGLE_TOKEN_URL, data={
        "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
        "redirect_uri": redirect_uri(), "grant_type": "authorization_code"}, timeout=10.0)
    r.raise_for_status()
    return r.json()


def refresh_access_token(refresh_token: str) -> dict | None:
    import httpx
    from ...config import get_settings
    s = get_settings()
    try:
        r = httpx.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh_token, "client_id": s.google_client_id,
            "client_secret": s.google_client_secret, "grant_type": "refresh_token"}, timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def store_tokens(conn, tokens: dict) -> None:
    from datetime import datetime, timezone, timedelta
    from ...core.crypto import encrypt
    conn.access_token_encrypted = encrypt(tokens.get("access_token"))
    if tokens.get("refresh_token"):            # Google only sends it on first consent
        conn.refresh_token_encrypted = encrypt(tokens["refresh_token"])
    expires_in = tokens.get("expires_in")
    conn.token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in) - 60)
                             if expires_in else None)


def events_for_user(db, conn) -> list[dict]:
    """Today's events for a connection, refreshing an expired access token first."""
    if conn is None:
        return []
    from datetime import datetime, timezone
    from ...core.crypto import decrypt
    exp = conn.token_expires_at
    if exp is not None and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp is not None and exp <= datetime.now(timezone.utc) and conn.refresh_token_encrypted:
        fresh = refresh_access_token(decrypt(conn.refresh_token_encrypted))
        if fresh:
            store_tokens(conn, fresh)
            db.commit()
    return fetch_today_events(decrypt(conn.access_token_encrypted))
