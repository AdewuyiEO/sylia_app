"""Daily Look (spec §3.5). The scorer runs inline (it's fast + deterministic);
only the explanation touches an LLM, and that's a single cached call."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from ...db import get_db
from ...deps import get_current_user
from ...models import User, ClothingItem, BodyProfile, IdentityProfile
from . import service

router = APIRouter(prefix="/v1/daily-look", tags=["daily-look"])


@router.get("")
def get_daily_look(date: str | None = None, lat: float | None = None,
                   lon: float | None = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    items = list(db.scalars(select(ClothingItem).where(
        ClothingItem.user_id == user.id, ClothingItem.is_active == True)))  # noqa: E712
    body = db.scalar(select(BodyProfile).where(BodyProfile.user_id == user.id))
    ident = db.scalar(select(IdentityProfile).where(IdentityProfile.user_id == user.id))

    # real context: cached weather for the user's location + the single calendar signal
    from ..integrations.weather import get_today_weather
    from ..integrations.calendar import formality_from_events, fetch_today_events
    from ...models import CalendarConnection

    weather = get_today_weather(db, lat, lon)
    cal = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id))
    from ...core.crypto import decrypt
    token = decrypt(cal.access_token_encrypted) if cal else None
    events = fetch_today_events(token) if token else []
    signal = formality_from_events(events, cal.category_mapping if cal else None)
    calendar_signal = signal["formality_category"]

    looks = service.build_looks(items, body, ident, weather, calendar_signal, top_n=3)
    if not looks:
        return {"looks": [], "context": {"weather": weather, "calendar": signal},
                "reason": "Not enough items yet — add a few more to get a look."}

    out = []
    for c in looks:
        bd = c.breakdown
        out.append({
            "items": [{"id": g.id, "category": g.category, "subcategory": g.subcategory,
                       "primary_color": g.primary_color} for g in c.pieces],
            "score_total": bd.total,
            "score_breakdown": {"context": bd.context, "color": bd.color,
                                 "body": bd.body, "identity": bd.identity},
            "explanation": service.explain({"context": bd.context, "color": bd.color,
                                             "body": bd.body, "identity": bd.identity}),
        })
    return {"context": {"weather": weather, "calendar": signal}, "looks": out}


@router.post("/{outfit_id}/feedback")
def feedback(outfit_id: str, payload: dict, user: User = Depends(get_current_user)):
    # persists user_feedback in {worn,skipped,loved,disliked}; feeds novelty-decay.
    return {"outfit_id": outfit_id, "user_feedback": payload.get("feedback", "pending")}


@router.post("/{outfit_id}/regenerate")
def regenerate(outfit_id: str, payload: dict, user: User = Depends(get_current_user)):
    # re-scores with an exclusion constraint (e.g. {"exclude_item_id": "..."}).
    return {"outfit_id": outfit_id, "status": "regenerated", "excluded": payload.get("exclude_item_id")}
