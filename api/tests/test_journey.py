"""Morning reveal + style journey: streak maths, automatic freezes, milestone
awards, weekly challenge, levels, badges, and the reveal endpoint.
Run: python tests/test_journey.py
"""
import os, sys, tempfile
from datetime import date, datetime, timedelta, timezone
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
from app.domains.journey.service import walk_streak, longest_streak, freezes_to_apply, level_for  # noqa: E402
from sqlalchemy import select  # noqa: E402
from support import Harness, ok, signup, add_item  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
h = Harness("Sylia journey + reveal")
T = date(2026, 10, 17)
D = lambda n: T - timedelta(days=n)   # noqa: E731


def t_walk_streak():
    worn = {D(1), D(2), D(3)}
    ok(walk_streak(worn, set(), T) == 3, "today not logged yet keeps yesterday's streak")
    ok(walk_streak(worn | {T}, set(), T) == 4, "today counts once worn")
    ok(walk_streak({D(1), D(3), D(4)}, set(), T) == 1, "a missed day breaks it")
    ok(walk_streak({D(1), D(3), D(4)}, {D(2)}, T) == 3, "a frozen day bridges without counting")
    ok(walk_streak(set(), set(), T) == 0)
h.test("current streak: today pending, gaps break, freezes bridge", t_walk_streak)


def t_longest():
    worn = {D(20), D(19), D(18), D(10), D(9), D(7)}
    ok(longest_streak(worn, set()) == 3, "longest run")
    ok(longest_streak(worn, {D(8)}) == 3, "freeze joins 10,9,(8),7 → 3 worn days")
    ok(longest_streak({D(20), D(19), D(18), D(16)}, {D(17)}) == 4, "freeze joins 20..18,(17),16 → 4")
h.test("longest streak counts worn days across freezes", t_longest)


def t_freezes_to_apply():
    worn = {D(2), D(3), D(4)}
    ok(freezes_to_apply(worn, set(), T, 2) == [D(1)], "one missed day after a streak uses one freeze")
    ok(freezes_to_apply({D(3), D(4)}, set(), T, 2) == [D(1), D(2)], "two missed days, two freezes")
    ok(freezes_to_apply({D(4)}, set(), T, 2) == [], "gap longer than freezes held → streak is lost")
    ok(freezes_to_apply({D(1)}, set(), T, 2) == [], "nothing missed")
    ok(freezes_to_apply(set(), set(), T, 2) == [], "no streak to protect")
    ok(freezes_to_apply(worn, set(), T, 0) == [], "no freezes held")
h.test("freezes only cover a gap after a live streak", t_freezes_to_apply)


def t_levels():
    ok(level_for(0)["name"] == "Starter" and level_for(0)["next_at"] == 100)
    ok(level_for(480)["name"] == "Curator" and level_for(480)["next_name"] == "Tastemaker")
    ok(level_for(5000)["name"] == "Icon" and level_for(5000)["next_at"] is None)
h.test("levels from points", t_levels)


# ── end to end over the API ─────────────────────────────────────────────────
H = signup(client, "journey@x.com")
for cat, sub, col in (("top", "blouse", "cream"), ("top", "shirt", "white"), ("bottom", "trousers", "navy"),
                      ("bottom", "jeans", "denim"), ("shoes", "loafers", "brown"), ("top", "knit", "rust")):
    add_item(client, H, category=cat, subcategory=sub, primary_color=col, formality_score=3, warmth_score=2)
TODAY = datetime.now(timezone.utc).date()


def wear_on(d):
    look = client.get(f"/v1/daily-look?date={d.isoformat()}", headers=H).json()["looks"][0]
    r = client.post(f"/v1/daily-look/{look['id']}/feedback", json={"feedback": "worn"}, headers=H)
    assert r.status_code == 200, r.text
    return look


def t_reveal_flow():
    d = client.get("/v1/daily-look", headers=H).json()
    ok(d["revealed"] is False and d["reveal_hour"] == 7, f"fresh day is unrevealed: {d.get('revealed')}")
    ok(d["next_reveal_at"].startswith((TODAY + timedelta(days=1)).isoformat()), d["next_reveal_at"])
    r = client.post(f"/v1/daily-look/{d['looks'][0]['id']}/reveal", headers=H)
    ok(r.status_code == 200 and r.json()["revealed"], r.text)
    ok(client.get("/v1/daily-look", headers=H).json()["revealed"] is True, "stays revealed")
    me = client.patch("/v1/me", json={"reveal_hour": 6}, headers=H).json()
    ok(me["reveal_hour"] == 6, me)
    ok(client.patch("/v1/me", json={"reveal_hour": 25}, headers=H).status_code == 422, "hour validated")
h.test("reveal: unrevealed → revealed, next unlock time, reveal hour", t_reveal_flow)


def t_streak_with_auto_freeze():
    # worn 5 days ago .. 2 days ago, missed yesterday → one freeze bridges it
    for n in (5, 4, 3, 2):
        wear_on(TODAY - timedelta(days=n))
    j = client.get("/v1/journey", headers=H).json()
    ok(j["streak"] == 4, f"streak bridged by a freeze: {j['streak']}")
    ok(j["freezes"] == 1, f"one freeze used: {j['freezes']}")
    states = [x["state"] for x in j["days"]]
    ok(states[-2] == "frozen" and states[-1] == "today", states[-3:])
    ok(j["days"][-3]["image_url"], "worn days carry a photo of the look")
    st = client.get("/v1/daily-look/stats", headers=H).json()
    ok(st["streak_days"] == 4, f"stats agree with the journey: {st['streak_days']}")
h.test("missing a day uses a freeze automatically", t_streak_with_auto_freeze)


def t_milestone_award():
    # 6 earlier worn days + today = 7 worn in the chain → +1 freeze
    for n in (8, 7, 6):
        wear_on(TODAY - timedelta(days=n))
    wear_on(TODAY)
    j = client.get("/v1/journey", headers=H).json()
    ok(j["streak"] == 8 and j["worn_today"], f"streak {j['streak']}")
    j2 = client.get("/v1/journey", headers=H).json()
    ok(j2["freezes"] == j["freezes"], "award is once per day, not per request")
    ok(j["longest"] >= 8)
    ok(any(b["id"] == "first_week" and b["earned"] for b in j["badges"]), "first-week badge earned")
h.test("streak, longest and first-week badge", t_milestone_award)


def t_award_at_seven():
    from app.domains.journey.service import refresh
    db = SessionLocal()
    u = db.scalar(select(User).where(User.email == "journey@x.com"))
    u.streak_freezes = 0
    u.freeze_awarded_on = None
    db.commit()
    db.close()
    H2 = signup(client, "seven@x.com")
    for cat, sub, col in (("top", "blouse", "cream"), ("top", "shirt", "white"), ("bottom", "trousers", "navy"),
                          ("bottom", "jeans", "denim"), ("shoes", "loafers", "brown")):
        add_item(client, H2, category=cat, subcategory=sub, primary_color=col, formality_score=3, warmth_score=2)
    for n in range(6, -1, -1):
        d = TODAY - timedelta(days=n)
        look = client.get(f"/v1/daily-look?date={d.isoformat()}", headers=H2).json()["looks"][0]
        client.post(f"/v1/daily-look/{look['id']}/feedback", json={"feedback": "worn"}, headers=H2)
    db = SessionLocal()
    u2 = db.scalar(select(User).where(User.email == "seven@x.com"))
    u2.streak_freezes = 1
    db.commit()
    j = refresh(db, u2, TODAY)
    ok(j["streak"] == 7 and j["freezes"] == 2, f"7-day milestone earns a freeze: {j['streak']}, {j['freezes']}")
    j = refresh(db, u2, TODAY)
    ok(j["freezes"] == 2, "capped at two")
    db.close()
h.test("every 7-day milestone earns a freeze (max 2)", t_award_at_seven)


def t_challenge():
    j = client.get("/v1/journey", headers=H).json()
    ch = j["challenge"]
    ok(ch and not ch["accepted"] and ch["points"] == 50, ch)
    ok(ch["item"]["wear_count"] == 0, f"targets a never-worn piece: {ch['item']}")
    before = j["level"]["points"]
    acc = client.post("/v1/journey/challenge/accept", headers=H).json()
    ok(acc["challenge"]["accepted"], "accepted")
    # wear a look that contains the challenge piece today
    item_id = ch["item"]["id"]
    db = SessionLocal()
    from app.models import Outfit, OutfitItem
    import uuid
    u = db.scalar(select(User).where(User.email == "journey@x.com"))
    o = Outfit(user_id=u.id, outfit_date=TODAY, rank=9, user_feedback="worn",
               worn_at=datetime.now(timezone.utc), score_breakdown={}, context={})
    db.add(o); db.flush()
    db.add(OutfitItem(outfit_id=o.id, clothing_item_id=uuid.UUID(item_id), role="top"))
    db.commit(); db.close()
    j = client.get("/v1/journey", headers=H).json()
    ok(j["challenge"]["completed"], "completed")
    ok(j["level"]["points"] >= before + 50, f"bonus points: {before} → {j['level']['points']}")
    again = client.get("/v1/journey", headers=H).json()["level"]["points"]
    ok(again == j["level"]["points"], "bonus credited once")
    ok(any(b["id"] == "challenge" and b["earned"] for b in j["badges"]), "challenge badge")
h.test("weekly challenge: accept, complete, bonus once", t_challenge)


def t_challenge_needs_closet():
    H3 = signup(client, "tiny@x.com")
    add_item(client, H3, category="top", subcategory="shirt", primary_color="white")
    j = client.get("/v1/journey", headers=H3).json()
    ok(j["challenge"] is None and j["streak"] == 0 and j["level"]["name"] == "Starter", j)
    ok(client.post("/v1/journey/challenge/accept", headers=H3).status_code == 409)
h.test("tiny closets get no challenge yet", t_challenge_needs_closet)


if __name__ == "__main__":
    h.report()
