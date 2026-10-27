"""Style journey: the daily habit loop around the worn-outfit log.

Streaks count days with a look logged as worn. A streak freeze bridges a missed
day automatically (like a rest day) so one busy morning doesn't erase weeks of
habit; freezes are earned back every 7-day milestone (max 2 held). A weekly
closet challenge nudges the user to wear their least-worn piece. Points, levels
and badges are all derived from the same wear history, so they can never drift
from what actually happened.

The streak maths (`walk_streak`, `longest_streak`, `freezes_to_apply`) are pure
and tested directly; `refresh` applies them to a user and persists.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

MAX_FREEZES = 2
FREEZE_EVERY = 7
POINTS_PER_WEAR = 10
CHALLENGE_POINTS = 50
LEVELS = [(0, "Starter"), (100, "Explorer"), (250, "Stylist"), (450, "Curator"),
          (700, "Tastemaker"), (1000, "Trendsetter"), (1500, "Icon")]


# ── pure streak maths ───────────────────────────────────────────────────────
def walk_streak(worn: set[date], frozen: set[date], today: date) -> int:
    """Current streak. Today not being logged yet doesn't break it; frozen days
    bridge the chain without adding to it."""
    d = today if today in worn else today - timedelta(days=1)
    n = 0
    while d in worn or d in frozen:
        if d in worn:
            n += 1
        d -= timedelta(days=1)
    return n


def longest_streak(worn: set[date], frozen: set[date]) -> int:
    best = run = 0
    if not worn:
        return 0
    d, end = min(worn), max(worn)
    while d <= end:
        if d in worn:
            run += 1
            best = max(best, run)
        elif d not in frozen:
            run = 0
        d += timedelta(days=1)
    return best


def freezes_to_apply(worn: set[date], frozen: set[date], today: date, available: int) -> list[date]:
    """Missed days ending yesterday that freezes can cover: only when the gap
    follows a live streak and the user holds enough freezes for the whole gap."""
    gap: list[date] = []
    d = today - timedelta(days=1)
    while d not in worn and d not in frozen:
        gap.append(d)
        d -= timedelta(days=1)
        if len(gap) > available:
            return []
    if not gap or d not in worn:
        return []          # nothing missed, or no streak to protect
    return gap


def level_for(points: int) -> dict:
    idx = max(i for i, (t, _) in enumerate(LEVELS) if points >= t)
    floor, name = LEVELS[idx]
    nxt = LEVELS[idx + 1] if idx + 1 < len(LEVELS) else None
    return {"level": idx + 1, "name": name, "points": points, "floor": floor,
            "next_at": nxt[0] if nxt else None, "next_name": nxt[1] if nxt else None}


def week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


# ── DB-backed ───────────────────────────────────────────────────────────────
def _worn_rows(db: Session, user_id):
    from ...models import Outfit, OutfitItem
    return list(db.execute(
        select(Outfit.id, Outfit.outfit_date, OutfitItem.clothing_item_id, OutfitItem.role)
        .join(OutfitItem, OutfitItem.outfit_id == Outfit.id)
        .where(Outfit.user_id == user_id, Outfit.user_feedback == "worn")))


def refresh(db: Session, user, today: date) -> dict:
    """Apply automatic freezes and milestone awards, then return the journey."""
    from ...models import ClothingItem
    from ..closet.router import item_out

    rows = _worn_rows(db, user.id)
    worn = {r.outfit_date for r in rows}
    frozen = {date.fromisoformat(x) for x in (user.freeze_dates or [])}
    changed = False

    gap = freezes_to_apply(worn, frozen, today, user.streak_freezes or 0)
    if gap:
        frozen |= set(gap)
        user.freeze_dates = sorted(x.isoformat() for x in frozen)
        user.streak_freezes = (user.streak_freezes or 0) - len(gap)
        changed = True

    current = walk_streak(worn, frozen, today)
    if (today in worn and current and current % FREEZE_EVERY == 0
            and user.freeze_awarded_on != today and (user.streak_freezes or 0) < MAX_FREEZES):
        user.streak_freezes = (user.streak_freezes or 0) + 1
        user.freeze_awarded_on = today
        changed = True

    items = {i.id: i for i in db.scalars(select(ClothingItem).where(ClothingItem.user_id == user.id))}
    active = [i for i in items.values() if i.is_active]
    wear_count: dict = {}
    for r in rows:
        wear_count[r.clothing_item_id] = wear_count.get(r.clothing_item_id, 0) + 1

    # weekly challenge: the least-worn wearable piece, stable for the week
    wk = week_key(today)
    week_start = today - timedelta(days=today.weekday())
    challenge = None
    candidates = [i for i in active if i.category in ("top", "bottom", "dress", "outerwear", "shoes")]
    if len(active) >= 5 and candidates:
        if user.challenge_week == wk and user.challenge_item_id in items and items[user.challenge_item_id].is_active:
            pick = items[user.challenge_item_id]
        else:
            pick = sorted(candidates, key=lambda i: (wear_count.get(i.id, 0), i.created_at or datetime.min.replace(tzinfo=timezone.utc), str(i.id)))[0]
        done = any(r.clothing_item_id == pick.id and week_start <= r.outfit_date <= today for r in rows)
        accepted = user.challenge_week == wk
        if done and accepted and user.challenge_done_week != wk:
            user.challenge_done_week = wk
            user.bonus_points = (user.bonus_points or 0) + CHALLENGE_POINTS
            changed = True
        name = " ".join(x for x in (pick.primary_color, pick.subcategory or pick.category) if x)
        never = wear_count.get(pick.id, 0) == 0
        challenge = {
            "week": wk, "item": item_out(pick).model_dump(mode="json"),
            "title": f"Wear the {name} you’ve never worn" if never else f"Bring back the {name}",
            "points": CHALLENGE_POINTS, "accepted": accepted, "completed": done,
            "days_left": 6 - today.weekday(),
        }

    if changed:
        db.commit()

    # last 14 days, oldest first, with a photo of what was worn
    main_img: dict = {}
    for r in rows:
        it = items.get(r.clothing_item_id)
        if it is None:
            continue
        prio = {"dress": 0, "top": 1, "outerwear": 2, "bottom": 3}.get(r.role, 9)
        cur = main_img.get(r.outfit_date)
        if cur is None or prio < cur[0]:
            main_img[r.outfit_date] = (prio, it)
    days = []
    for k in range(13, -1, -1):
        d = today - timedelta(days=k)
        state = "worn" if d in worn else "frozen" if d in frozen else "today" if d == today else "missed"
        image = None
        if state == "worn" and d in main_img:
            image = item_out(main_img[d][1]).image_url
        days.append({"date": d.isoformat(), "state": state, "image_url": image})

    points = len(worn) * POINTS_PER_WEAR + (user.bonus_points or 0)
    longest = longest_streak(worn, frozen)
    worn_30 = {r.clothing_item_id for r in rows if r.outfit_date > today - timedelta(days=30)}
    util = round(len(worn_30 & {i.id for i in active}) / len(active), 2) if active else 0.0

    def badge(bid, title, earned, progress, img_item=None):
        return {"id": bid, "title": title, "earned": earned, "progress": round(min(1.0, progress), 2),
                "image_url": item_out(img_item).image_url if img_item is not None else None}

    sample = (sorted(active, key=lambda i: -wear_count.get(i.id, 0)) or [None])[0]
    badges = [
        badge("first_look", "First look", bool(worn), 1.0 if worn else 0.0, sample),
        badge("first_week", "First week", longest >= 7, longest / 7, sample),
        badge("challenge", "Challenge champion", bool(user.challenge_done_week), 1.0 if user.challenge_done_week else 0.0,
              items.get(user.challenge_item_id) if user.challenge_item_id else None),
        badge("explorer", "Closet explorer", util >= 0.8 and len(active) >= 10, util / 0.8 if active else 0.0, sample),
        badge("streak_30", "30-day streak", longest >= 30, longest / 30, sample),
    ]

    return {
        "streak": current,
        "longest": longest,
        "freezes": user.streak_freezes or 0,
        "max_freezes": MAX_FREEZES,
        "worn_today": today in worn,
        "days": days,
        "level": level_for(points),
        "challenge": challenge,
        "badges": badges,
        "reveal_hour": user.reveal_hour if user.reveal_hour is not None else 7,
    }


def accept_challenge(db: Session, user, today: date) -> None:
    j = refresh(db, user, today)
    if not j["challenge"]:
        raise ValueError("no challenge this week")
    import uuid as _uuid
    user.challenge_week = j["challenge"]["week"]
    user.challenge_item_id = _uuid.UUID(j["challenge"]["item"]["id"])
    db.commit()


def next_reveal_at(user, today: date) -> str:
    """Tomorrow at the user's reveal hour, in their timezone, as ISO 8601."""
    hour = user.reveal_hour if user.reveal_hour is not None else 7
    tz = timezone.utc
    if getattr(user, "timezone", None):
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(user.timezone)
        except Exception:
            pass
    return datetime.combine(today + timedelta(days=1), datetime.min.time(), tz).replace(hour=hour).isoformat()
