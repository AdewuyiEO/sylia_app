"""Wear loop: daily looks persist per day, "worn" feeds novelty-decay and WWO,
swaps exclude items, history + stats, coverage preference, Pro gating.
Run: python tests/test_wear_loop.py
"""
import os, sys, tempfile
from datetime import date, timedelta
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
os.environ["LOCAL_STORAGE_DIR"] = os.path.join(_dir, "storage")
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine, SessionLocal  # noqa: E402
from app.models import Base, User  # noqa: E402
from sqlalchemy import select  # noqa: E402
from support import Harness, ok, signup, add_item  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
h = Harness("Sylia wear loop")

H = signup(client, "wear@x.com")
ITEMS = {
    "t1": add_item(client, H, category="top", subcategory="blouse", primary_color="cream",
                   formality_score=3, warmth_score=2),
    "t2": add_item(client, H, category="top", subcategory="shirt", primary_color="white",
                   formality_score=3, warmth_score=2),
    "t3": add_item(client, H, category="top", subcategory="tank top", primary_color="black",
                   formality_score=2, warmth_score=1, tags=["sleeveless"]),
    "b1": add_item(client, H, category="bottom", subcategory="trousers", primary_color="navy",
                   formality_score=3, warmth_score=2),
    "b2": add_item(client, H, category="bottom", subcategory="jeans", primary_color="denim",
                   formality_score=2, warmth_score=2),
    "s1": add_item(client, H, category="shoes", subcategory="loafers", primary_color="brown",
                   formality_score=3, warmth_score=2),
}
DAY = "2026-10-14"   # a Wednesday
_ctx = {}


def ids(look):
    return {i["id"] for i in look["items"]}


def t_generate_and_persist():
    r = client.get(f"/v1/daily-look?date={DAY}", headers=H)
    ok(r.status_code == 200, r.text)
    body = r.json()
    ok(len(body["looks"]) >= 2, f"expected several looks, got {len(body['looks'])}")
    top = body["looks"][0]
    ok(top["rank"] == 1 and top["id"] and top["explanation"], "top look persisted with id + explanation")
    ok(top["items"][0]["image_url"], "look items carry image URLs")
    ok(body["context"]["context_kind"] == "work", "weekday → work context")
    ok("temp_c" in body["context"]["weather"], "weather carries Celsius")
    _ctx["looks"] = body["looks"]
    again = client.get(f"/v1/daily-look?date={DAY}", headers=H).json()
    ok([l["id"] for l in again["looks"]] == [l["id"] for l in body["looks"]], "same day → same looks")
h.test("a day's looks are generated once and stay stable", t_generate_and_persist)


def t_weekend_context():
    sat = client.get("/v1/daily-look?date=2026-10-17", headers=H).json()
    ok(sat["context"]["context_kind"] == "weekend", "Saturday with no events → weekend")
h.test("weekend context on Saturdays", t_weekend_context)


def t_worn_is_exclusive_per_day():
    a, b = _ctx["looks"][0], _ctx["looks"][1]
    ok(client.post(f"/v1/daily-look/{a['id']}/feedback", json={"feedback": "worn"}, headers=H).status_code == 200)
    r = client.post(f"/v1/daily-look/{b['id']}/feedback", json={"feedback": "worn"}, headers=H)
    ok(r.json()["user_feedback"] == "worn" and r.json()["worn_at"], r.text)
    looks = {l["id"]: l for l in client.get(f"/v1/daily-look?date={DAY}", headers=H).json()["looks"]}
    ok(looks[a["id"]]["user_feedback"] == "pending", "wearing another look un-wears the first")
    ok(client.post(f"/v1/daily-look/{a['id']}/feedback", json={"feedback": "teleported"},
                   headers=H).status_code == 422, "unknown feedback rejected")
h.test("only one look per day can be worn", t_worn_is_exclusive_per_day)


def t_novelty_decay_next_day():
    worn = ids(_ctx["looks"][1])
    nxt = client.get(f"/v1/daily-look?date={date.fromisoformat(DAY) + timedelta(days=1)}", headers=H).json()
    top_next = nxt["looks"][0]
    ok(ids(top_next) != worn, "yesterday's worn look is not today's top pick")
h.test("worn looks feed novelty-decay the next day", t_novelty_decay_next_day)


def t_swap_excludes_item():
    look = _ctx["looks"][0]
    banned = next(i["id"] for i in look["items"] if i["category"] == "top")
    r = client.post(f"/v1/daily-look/{look['id']}/regenerate", json={"exclude_item_id": banned}, headers=H)
    ok(r.status_code == 200, r.text)
    new = r.json()
    ok(banned not in ids(new), "swapped look never contains the excluded item")
    ok(new["rank"] > max(l["rank"] for l in _ctx["looks"]), "swap is persisted as a new rank")
    shown = [ids(l) for l in _ctx["looks"]]
    ok(ids(new) not in shown, "swap doesn't repeat a look already shown today")
h.test("swap excludes the item and avoids repeats", t_swap_excludes_item)


def t_history_and_stats():
    hist = client.get("/v1/daily-look/history?days=3650", headers=H).json()
    ok(len(hist["looks"]) == 1 and hist["looks"][0]["user_feedback"] == "worn", hist)
    st = client.get("/v1/daily-look/stats", headers=H).json()
    for k in ("weekly_worn_outfits", "streak_days", "closet_size", "closet_utilization_30d",
              "never_worn", "most_worn"):
        ok(k in st, f"stats has {k}")
    ok(st["closet_size"] == 6, st)
    # log today as worn → WWO and streak count it
    today = client.get("/v1/daily-look", headers=H).json()
    client.post(f"/v1/daily-look/{today['looks'][0]['id']}/feedback", json={"feedback": "worn"}, headers=H)
    st = client.get("/v1/daily-look/stats", headers=H).json()
    ok(st["weekly_worn_outfits"] >= 1 and st["streak_days"] >= 1, st)
    ok(st["most_worn"] and st["most_worn"][0]["times_worn"] >= 1, "most-worn list populated")
h.test("history and WWO stats", t_history_and_stats)


def t_deleted_item_rebuilds_day():
    day = "2026-10-20"
    first = client.get(f"/v1/daily-look?date={day}", headers=H).json()["looks"][0]
    gone = first["items"][0]["id"]
    client.delete(f"/v1/wardrobe/items/{gone}", headers=H)
    after = client.get(f"/v1/daily-look?date={day}", headers=H).json()
    ok(all(gone not in ids(l) for l in after["looks"]), "looks rebuilt without the deleted piece")
h.test("deleting a piece rebuilds that day's looks", t_deleted_item_rebuilds_day)


def t_modest_coverage_end_to_end():
    H2 = signup(client, "modest@x.com")
    tank = add_item(client, H2, category="top", subcategory="tank top", primary_color="black",
                    formality_score=2, warmth_score=1, tags=["sleeveless"])
    add_item(client, H2, category="top", subcategory="blouse", primary_color="cream", formality_score=3, warmth_score=2)
    add_item(client, H2, category="bottom", subcategory="trousers", primary_color="navy", formality_score=3, warmth_score=2)
    add_item(client, H2, category="shoes", subcategory="flats", primary_color="black", formality_score=3, warmth_score=2)
    r = client.patch("/v1/identity-profile", json={"lifestyle_patterns": {"coverage": "modest"}}, headers=H2)
    ok(r.status_code == 200, r.text)
    looks = client.get(f"/v1/daily-look?date={DAY}", headers=H2).json()["looks"]
    ok(looks and all(tank not in ids(l) for l in looks), "modest users never get the tank top")
    bad = client.patch("/v1/identity-profile", json={"lifestyle_patterns": {"coverage": "x"}}, headers=H2)
    ok(bad.status_code == 422, "invalid coverage rejected")
h.test("modest coverage preference flows from profile to looks", t_modest_coverage_end_to_end)


def t_swap_requires_pro_after_trial():
    H3 = signup(client, "lapsed@x.com")
    for cat, sub, col in (("top", "shirt", "white"), ("top", "blouse", "cream"),
                          ("bottom", "trousers", "navy"), ("shoes", "loafers", "brown")):
        add_item(client, H3, category=cat, subcategory=sub, primary_color=col, formality_score=3, warmth_score=2)
    look = client.get(f"/v1/daily-look?date={DAY}", headers=H3).json()["looks"][0]
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == "lapsed@x.com"))
    from datetime import datetime, timezone
    u.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit(); db.close()
    r = client.post(f"/v1/daily-look/{look['id']}/regenerate", json={}, headers=H3)
    ok(r.status_code == 402, f"expired trial → paywall, got {r.status_code}")
    ok(client.get(f"/v1/daily-look?date={DAY}", headers=H3).status_code == 200, "daily look stays free")
h.test("swaps need Pro once the trial ends; the daily look stays free", t_swap_requires_pro_after_trial)


def t_other_users_cannot_touch_looks():
    other = signup(client, "nosy@x.com")
    lid = _ctx["looks"][0]["id"]
    ok(client.post(f"/v1/daily-look/{lid}/feedback", json={"feedback": "worn"}, headers=other).status_code == 404)
h.test("looks are private to their owner", t_other_users_cannot_touch_looks)


if __name__ == "__main__":
    h.report()
