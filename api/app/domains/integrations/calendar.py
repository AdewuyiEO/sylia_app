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
