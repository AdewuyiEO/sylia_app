"""Daily Look (spec §3.5). The scorer runs inline (it's fast + deterministic);
only the explanation touches an LLM, and that's a single cached call.

A day's looks are generated once and persisted, so reopening the app shows the
same pick. Logging a look as worn feeds the scorer's novelty-decay and the
north-star metric (Weekly Worn Outfits).
"""
import uuid
from datetime import date as date_cls, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user, require_entitled
from ...models import (User, ClothingItem, BodyProfile, IdentityProfile, Outfit, OutfitItem,
                       CalendarConnection)
from ..closet.router import item_out
from . import service
from .scorer import WornRecord

router = APIRouter(prefix="/v1/daily-look", tags=["daily-look"])

FEEDBACK = ("worn", "skipped", "loved", "disliked", "pending")


class FeedbackIn(BaseModel):
    feedback: str = Field(pattern="^(worn|skipped|loved|disliked|pending)$")
    note: str | None = Field(default=None, max_length=500)


class RegenerateIn(BaseModel):
    exclude_item_id: str | None = None


def _owned_outfit(db: Session, user: User, outfit_id: str) -> Outfit:
    try:
        o = db.get(Outfit, uuid.UUID(outfit_id))
    except ValueError:
        o = None
    if o is None or o.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Look not found")
    return o


def _inputs(db: Session, user: User):
    items = list(db.scalars(select(ClothingItem).where(
        ClothingItem.user_id == user.id, ClothingItem.is_active == True)))  # noqa: E712
    body = db.scalar(select(BodyProfile).where(BodyProfile.user_id == user.id))
    ident = db.scalar(select(IdentityProfile).where(IdentityProfile.user_id == user.id))
    return items, body, ident


def _context(db: Session, user: User, day: date_cls, lat: float | None, lon: float | None) -> dict:
    from ..integrations.weather import get_today_weather
    from ..integrations.calendar import formality_from_events, events_for_user

    weather = get_today_weather(db, lat, lon)
    cal = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == user.id))
    signal = formality_from_events(events_for_user(db, cal), cal.category_mapping if cal else None)
    kind = service.context_kind(day, signal["formality_category"], signal["driver"])
    return {"weather": weather, "calendar": signal, "context_kind": kind}


def _recent_worn(db: Session, user: User, day: date_cls) -> list[WornRecord]:
    since = day - timedelta(days=14)
    rows = db.execute(
        select(Outfit.id, Outfit.outfit_date, OutfitItem.clothing_item_id)
        .join(OutfitItem, OutfitItem.outfit_id == Outfit.id)
        .where(Outfit.user_id == user.id, Outfit.user_feedback == "worn",
               Outfit.outfit_date >= since, Outfit.outfit_date < day))
    by_outfit: dict = {}
    for oid, odate, iid in rows:
        by_outfit.setdefault(oid, (odate, set()))[1].add(str(iid))
    return [WornRecord(item_ids=frozenset(ids), days_ago=(day - odate).days)
            for odate, ids in by_outfit.values()]


def _persist(db: Session, user: User, day: date_cls, ctx: dict, cand, rank: int) -> Outfit:
    bd = cand.breakdown
    breakdown = {"context": bd.context, "color": bd.color, "body": bd.body, "identity": bd.identity}
    outfit = Outfit(
        user_id=user.id, outfit_date=day, rank=rank, context=ctx,
        score_total=bd.total, score_breakdown=breakdown,
        explanation=service.explain(breakdown, context=ctx, pieces=cand.pieces, locale=user.locale),
    )
    db.add(outfit)
    db.flush()
    for g in cand.pieces:
        db.add(OutfitItem(outfit_id=outfit.id, clothing_item_id=uuid.UUID(g.id), role=g.category))
    return outfit


def _look_out(db: Session, outfit: Outfit, items_by_id: dict) -> dict:
    pieces = [items_by_id.get(oi.clothing_item_id) for oi in db.scalars(
        select(OutfitItem).where(OutfitItem.outfit_id == outfit.id))]
    return {
        "id": str(outfit.id), "rank": outfit.rank, "date": outfit.outfit_date.isoformat(),
        "items": [item_out(p).model_dump(mode="json") for p in pieces if p is not None],
        "score_total": float(outfit.score_total or 0),
        "score_breakdown": outfit.score_breakdown,
        "explanation": outfit.explanation,
        "user_feedback": outfit.user_feedback,
        "worn_at": outfit.worn_at.isoformat() if outfit.worn_at else None,
    }


def _day_outfits(db: Session, user: User, day: date_cls) -> list[Outfit]:
    return list(db.scalars(select(Outfit).where(
        Outfit.user_id == user.id, Outfit.outfit_date == day).order_by(Outfit.rank)))


def _still_wearable(db: Session, outfit: Outfit, active_ids: set) -> bool:
    ids = set(db.scalars(select(OutfitItem.clothing_item_id).where(OutfitItem.outfit_id == outfit.id)))
    return ids <= active_ids


@router.get("")
def get_daily_look(date: str | None = None, lat: float | None = None,
                   lon: float | None = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    day = date_cls.fromisoformat(date) if date else service.local_today(user)
    items, body, ident = _inputs(db, user)
    items_by_id = {i.id: i for i in items}
    active_ids = set(items_by_id)

    existing = _day_outfits(db, user, day)
    # keep the day's looks stable unless the user removed a piece from their closet
    if existing and all(_still_wearable(db, o, active_ids) for o in existing):
        ctx = existing[0].context or {}
        return {"date": day.isoformat(), "context": ctx,
                "looks": [_look_out(db, o, items_by_id) for o in existing if o.user_feedback != "skipped"]}

    for o in existing:   # stale: a piece was deleted — drop unworn looks and rebuild
        if o.user_feedback in ("pending", "skipped"):
            db.query(OutfitItem).filter(OutfitItem.outfit_id == o.id).delete()
            db.delete(o)
    db.flush()

    ctx = _context(db, user, day, lat, lon)
    looks = service.build_looks(items, body, ident, ctx, recent=_recent_worn(db, user, day),
                                top_n=3, seed=day.toordinal())
    if not looks:
        db.commit()
        return {"date": day.isoformat(), "looks": [], "context": ctx,
                "reason": "Not enough items yet — add a top, a bottom and shoes (or a dress) to get a look."}

    saved = [_persist(db, user, day, ctx, c, rank) for rank, c in enumerate(looks, start=1)]
    db.commit()
    return {"date": day.isoformat(), "context": ctx,
            "looks": [_look_out(db, o, items_by_id) for o in saved]}


@router.post("/{outfit_id}/feedback")
def feedback(outfit_id: str, body: FeedbackIn, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    outfit = _owned_outfit(db, user, outfit_id)
    if body.feedback == "worn":
        # one worn look per day: wearing this one un-wears any other
        for other in _day_outfits(db, user, outfit.outfit_date):
            if other.id != outfit.id and other.user_feedback == "worn":
                other.user_feedback, other.worn_at = "pending", None
        outfit.worn_at = datetime.now(timezone.utc)
    elif outfit.user_feedback == "worn":
        outfit.worn_at = None
    outfit.user_feedback = body.feedback
    if body.note is not None:
        outfit.feedback_note = body.note
    db.commit()
    return {"outfit_id": outfit_id, "user_feedback": outfit.user_feedback,
            "worn_at": outfit.worn_at.isoformat() if outfit.worn_at else None}


@router.post("/{outfit_id}/regenerate")
def regenerate(outfit_id: str, body: RegenerateIn | None = None, db: Session = Depends(get_db),
               user: User = Depends(require_entitled)):
    """Swap: skip this look and score a new one, optionally without one item."""
    from .scorer import look_signature, Garment

    outfit = _owned_outfit(db, user, outfit_id)
    day = outfit.outfit_date
    items, body_row, ident = _inputs(db, user)
    items_by_id = {i.id: i for i in items}

    shown = []
    for o in _day_outfits(db, user, day):
        ids = list(db.scalars(select(OutfitItem.clothing_item_id).where(OutfitItem.outfit_id == o.id)))
        shown.append(look_signature([Garment(str(i), items_by_id[i].category, "", "", 3, 3)
                                     for i in ids if i in items_by_id]))
    exclude = {body.exclude_item_id} if body and body.exclude_item_id else set()

    ctx = outfit.context or _context(db, user, day, None, None)
    looks = service.build_looks(items, body_row, ident, ctx, recent=_recent_worn(db, user, day),
                                top_n=1, seed=day.toordinal(), exclude_ids=exclude,
                                exclude_signatures=set(shown))
    if not looks:
        raise HTTPException(status.HTTP_409_CONFLICT, "No other look fits today — add more pieces to get swaps.")

    if outfit.user_feedback == "pending":
        outfit.user_feedback = "skipped"
    rank = max(o.rank for o in _day_outfits(db, user, day)) + 1
    new = _persist(db, user, day, ctx, looks[0], rank)
    db.commit()
    return _look_out(db, new, items_by_id)


@router.get("/history")
def history(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    since = service.local_today(user) - timedelta(days=min(max(days, 1), 365))
    worn = list(db.scalars(select(Outfit).where(
        Outfit.user_id == user.id, Outfit.user_feedback == "worn", Outfit.outfit_date >= since)
        .order_by(Outfit.outfit_date.desc())))
    items_by_id = {i.id: i for i in db.scalars(select(ClothingItem).where(ClothingItem.user_id == user.id))}
    return {"looks": [_look_out(db, o, items_by_id) for o in worn]}


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.wear_stats(db, user, service.local_today(user))
