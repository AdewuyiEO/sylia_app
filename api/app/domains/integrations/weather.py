"""Weather service (spec §1.1: OpenWeatherMap, cached).

Fetches today's forecast for a lat/lon, caches it in `weather_cache` (keyed by a
coarse location + date) so we hit the API at most a few times per location per
day, and normalises to the exact shape the scorer's Context wants:
{temp_f, temp_c, precipitation, condition}. Degrades to a sensible seasonal default
if no API key is set or the call fails — the daily look must never hard-fail on
a weather outage.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session

from ...config import get_settings
from ...models import WeatherCache

settings = get_settings()
_CACHE_TTL = timedelta(hours=3)


def _location_key(lat: float, lon: float) -> str:
    # coarse to ~11km grid so nearby users share a cache entry
    return f"{round(lat, 1)},{round(lon, 1)}"


def _f_to_c(f: float) -> int:
    return round((f - 32) * 5 / 9)


def _default_weather() -> dict:
    return {"temp_f": 68, "temp_c": 20, "precipitation": False, "condition": None,
            "source": "default"}


def _normalise(owm: dict) -> dict:
    """OpenWeatherMap 'One Call'/'current' shape → scorer Context fields."""
    try:
        temp_f = owm["main"]["temp"] if "main" in owm else owm.get("temp_f", 68)
        weather_list = owm.get("weather", [])
        main = (weather_list[0]["main"].lower() if weather_list else "")
        precip = main in {"rain", "drizzle", "thunderstorm", "snow"}
        return {"temp_f": round(float(temp_f)), "temp_c": _f_to_c(float(temp_f)),
                "precipitation": bool(precip), "condition": main or None,
                "source": "openweathermap"}
    except Exception:
        return _default_weather()


def get_today_weather(db: Session, lat: float | None, lon: float | None) -> dict:
    if lat is None or lon is None:
        return _default_weather()

    key = _location_key(lat, lon)
    today = date.today()
    now = datetime.now(timezone.utc)

    cached = db.get(WeatherCache, (key, today))
    if cached and cached.expires_at:
        exp = cached.expires_at
        if exp.tzinfo is None:                  # SQLite returns naive datetimes
            exp = exp.replace(tzinfo=timezone.utc)
        if exp > now:
            return cached.payload

    fresh = _fetch_owm(lat, lon)
    payload = _normalise(fresh) if fresh else _default_weather()

    # upsert cache
    if cached is None:
        cached = WeatherCache(location_key=key, date=today)
        db.add(cached)
    cached.payload = payload
    cached.expires_at = now + _CACHE_TTL
    db.commit()
    return payload


def _fetch_owm(lat: float, lon: float) -> dict | None:
    """Live OpenWeatherMap call. Returns None (→ default) with no key or on error."""
    if not settings.openweather_api_key:
        return None
    try:
        import httpx
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"lat": lat, "lon": lon, "units": "imperial",
                  "appid": settings.openweather_api_key}
        r = httpx.get(url, params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None
