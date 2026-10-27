"""Account: profile + regional preferences, data export, and deletion.

Deletion is immediate and complete (App Store guideline 5.1.1(v); GDPR art. 17):
every row the user owns and every stored photo. Export returns everything we
hold about the user as JSON (GDPR art. 15/20).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.storage import storage
from ...db import get_db
from ...deps import get_current_user
from ...models import (User, Subscription, IdentityProfile, BodyProfile, ClothingItem, Outfit,
                       OutfitItem, CoachConversation, CoachMessage, CalendarConnection,
                       AffiliateRecommendation)

router = APIRouter(prefix="/v1/me", tags=["account"])


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    locale: str | None = Field(default=None, max_length=35)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    units: str | None = Field(default=None, pattern="^(metric|imperial)$")
    timezone: str | None = Field(default=None, max_length=64)
    reveal_hour: int | None = Field(default=None, ge=0, le=23)


def _profile(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name,
            "auth_provider": user.auth_provider, "locale": user.locale, "country": user.country,
            "units": user.units, "timezone": user.timezone,
            "reveal_hour": user.reveal_hour if user.reveal_hour is not None else 7,
            "created_at": user.created_at.isoformat() if user.created_at else None}


@router.get("")
def me(user: User = Depends(get_current_user)):
    return _profile(user)


@router.patch("")
def update_me(body: ProfilePatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    patch = body.model_dump(exclude_unset=True)
    if patch.get("timezone"):
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(patch["timezone"])
        except Exception:
            raise HTTPException(422, "Unknown timezone")
    if patch.get("country"):
        patch["country"] = patch["country"].upper()
    for k, v in patch.items():
        setattr(user, k, v)
    db.commit()
    return _profile(user)


def _rows(db: Session, model, user_id) -> list:
    return list(db.scalars(select(model).where(model.user_id == user_id)))


def _plain(row) -> dict:
    out = {}
    for col in row.__table__.columns:
        if col.name.endswith("_encrypted") or col.name in ("password_hash", "api_key_hash"):
            continue
        v = getattr(row, col.name)
        out[col.name] = v.isoformat() if hasattr(v, "isoformat") else (str(v) if hasattr(v, "hex") else v)
    return out


@router.get("/export")
def export(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    outfits = _rows(db, Outfit, user.id)
    convos = _rows(db, CoachConversation, user.id)
    return {
        "user": _plain(user),
        "subscription": [_plain(r) for r in _rows(db, Subscription, user.id)],
        "identity_profile": [_plain(r) for r in _rows(db, IdentityProfile, user.id)],
        "body_profile": [_plain(r) for r in _rows(db, BodyProfile, user.id)],
        "closet": [_plain(r) for r in _rows(db, ClothingItem, user.id)],
        "outfits": [{**_plain(o), "items": [_plain(i) for i in db.scalars(
            select(OutfitItem).where(OutfitItem.outfit_id == o.id))]} for o in outfits],
        "coach": [{**_plain(c), "messages": [_plain(m) for m in db.scalars(
            select(CoachMessage).where(CoachMessage.conversation_id == c.id))]} for c in convos],
        "calendar": [_plain(r) for r in _rows(db, CalendarConnection, user.id)],
        "recommendations": [_plain(r) for r in _rows(db, AffiliateRecommendation, user.id)],
    }


@router.delete("", status_code=204)
def delete_account(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    keys = []
    for item in _rows(db, ClothingItem, user.id):
        keys += [k for k in (item.s3_key_original, item.s3_key_processed) if k]
    for bp in _rows(db, BodyProfile, user.id):
        if bp.intake_image_s3_key:
            keys.append(bp.intake_image_s3_key)

    outfit_ids = [o.id for o in _rows(db, Outfit, user.id)]
    convo_ids = [c.id for c in _rows(db, CoachConversation, user.id)]
    if outfit_ids:
        db.query(OutfitItem).filter(OutfitItem.outfit_id.in_(outfit_ids)).delete(synchronize_session=False)
    if convo_ids:
        db.query(CoachMessage).filter(CoachMessage.conversation_id.in_(convo_ids)).delete(synchronize_session=False)
    for model in (AffiliateRecommendation, Outfit, CoachConversation, ClothingItem, CalendarConnection,
                  BodyProfile, IdentityProfile, Subscription):
        db.query(model).filter(model.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()

    for k in keys:   # after the commit: a storage hiccup must not resurrect the account
        try:
            storage.delete(k)
        except Exception:
            pass
    return None
