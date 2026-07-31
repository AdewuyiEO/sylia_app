"""Integration tests. Weather normalisation/caching/defaults and the calendar
formality signal run for real (no network — the live fetch returns None/[] with
no API key, exercising the graceful-default path we ship). Also verifies the
daily-look endpoint now threads real context through the scorer.
Run: python3 tests/test_integrations.py
"""
import sys, os, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
os.environ["LOCAL_STORAGE_DIR"] = f"{_dir}/s"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.domains.integrations.weather import _normalise, _default_weather, get_today_weather  # noqa: E402
from app.domains.integrations.calendar import formality_from_events  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine, SessionLocal  # noqa: E402
from app.models import Base  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

_p, _f, _fails = 0, 0, []
def test(name, fn):
    global _p, _f
    try:
        fn(); _p += 1
    except Exception as e:
        _f += 1; _fails.append(f"  x {name}\n      {e}")
def ok(c, m=""): assert c, m


def t_normalise_owm():
    owm = {"main": {"temp": 41.4}, "weather": [{"main": "Rain"}]}
    n = _normalise(owm)
    ok(n["temp_f"] == 41, f"temp rounded, got {n['temp_f']}")
    ok(n["precipitation"] is True, "rain → precipitation true")
    clear = _normalise({"main": {"temp": 72}, "weather": [{"main": "Clear"}]})
    ok(clear["precipitation"] is False, "clear → no precipitation")
test("weather normalisation maps OWM shape to scorer Context", t_normalise_owm)


def t_weather_default_without_key():
    # no API key configured → default, never a crash
    db = SessionLocal()
    w = get_today_weather(db, 6.5, 3.4)      # Lagos-ish coords
    db.close()
    ok(w["source"] in ("default", "openweathermap"), "returns a usable payload")
    ok("temp_f" in w and "precipitation" in w, "has the fields the scorer needs")
test("weather degrades to a default when no API key is set", t_weather_default_without_key)


def t_weather_cache_roundtrip():
    db = SessionLocal()
    w1 = get_today_weather(db, 40.7, -74.0)
    w2 = get_today_weather(db, 40.7, -74.0)   # second call should hit cache
    db.close()
    ok(w1 == w2, "cached weather is stable within TTL")
test("weather caches per location+day", t_weather_cache_roundtrip)


def t_calendar_most_formal_wins():
    events = [{"summary": "Morning gym"}, {"summary": "Client presentation 2pm"},
              {"summary": "Coffee catch-up"}]
    sig = formality_from_events(events)
    ok(sig["formality_category"] == 4, f"client presentation (4) should win, got {sig['formality_category']}")
    ok("presentation" in (sig["driver"] or "").lower(), "driver names the formal event")
test("calendar signal = the most formal event of the day", t_calendar_most_formal_wins)


def t_calendar_neutral_default():
    ok(formality_from_events([])["formality_category"] == 3, "no events → neutral 3")
    ok(formality_from_events([{"summary": "random thing"}])["formality_category"] == 3,
       "unmatched events → neutral 3")
test("calendar defaults to neutral formality with no signal", t_calendar_neutral_default)


def t_user_mapping_overrides():
    # a user can teach the mapping: their 'demo' means a client-grade event
    sig = formality_from_events([{"summary": "Big demo"}], user_mapping={"demo": 5})
    ok(sig["formality_category"] == 5, f"user override applied, got {sig['formality_category']}")
test("user category_mapping overrides default keywords", t_user_mapping_overrides)


def t_daily_look_threads_context():
    H = {"Authorization": "Bearer " + client.post(
        "/v1/auth/signup", json={"email": "ctx@x.com", "password": "pw123456"}
    ).json()["access_token"]}
    r = client.get("/v1/daily-look?lat=40.7&lon=-74.0", headers=H)
    ok(r.status_code == 200, r.text)
    body = r.json()
    ok("context" in body, "response now includes the resolved context")
    ok("weather" in body["context"] and "calendar" in body["context"], "weather + calendar present")
test("daily-look now returns the real resolved context", t_daily_look_threads_context)


if __name__ == "__main__":
    print("\nSylia integrations\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
