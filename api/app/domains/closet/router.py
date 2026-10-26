"""Closet (spec §3.4) — real DB-backed reads/writes.

Upload creates a placeholder row immediately (status implied by NULL fields +
low confidence) and enqueues the CV job that fills it in. This means the item
shows up in the closet the instant it's uploaded, in a 'processing' visual
state — the client never waits on the worker to see the item exist.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User, ClothingItem, Outfit, OutfitItem
from ...core.jobs import jobs
from ...core.storage import storage
from ...workers import tasks
from ...schemas.closet import (
    ItemUploadIn, ItemPatchIn, ItemOut, ItemListOut, JobAccepted,
)
from ..uploads.router import assert_owned_key

router = APIRouter(prefix="/v1/wardrobe", tags=["closet"])

CATEGORIES = {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}


def _owned_item(db: Session, user: User, item_id: str) -> ClothingItem:
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    item = db.get(ClothingItem, iid)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


def wear_stats(db: Session, user_id) -> dict[uuid.UUID, tuple[int, datetime | None]]:
    """item_id -> (times worn, last worn) from outfits the user logged as worn."""
    rows = db.execute(
        select(OutfitItem.clothing_item_id, func.count(), func.max(Outfit.worn_at))
        .join(Outfit, Outfit.id == OutfitItem.outfit_id)
        .where(Outfit.user_id == user_id, Outfit.user_feedback == "worn")
        .group_by(OutfitItem.clothing_item_id))
    return {iid: (n, last) for iid, n, last in rows}


def item_out(item: ClothingItem, wear: dict | None = None) -> ItemOut:
    out = ItemOut.model_validate(item)
    key = item.s3_key_processed or item.s3_key_original
    if key:
        try:
            out.image_url = storage.presign_get(key)
        except Exception:
            out.image_url = None
    elif item.external_image_url:
        out.image_url = item.external_image_url
    if wear and item.id in wear:
        out.wear_count, out.last_worn_at = wear[item.id]
    return out


@router.post("/items", status_code=202, response_model=JobAccepted)
def upload_item(body: ItemUploadIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> JobAccepted:
    key = assert_owned_key(user, body.s3_key_original, "closet")
    # create the row now so it appears in the closet immediately, pre-classification
    item = ClothingItem(
        user_id=user.id,
        s3_key_original=key,
        category="top",                       # provisional; the worker overwrites
        classification_confidence=None,        # NULL confidence == "still processing"
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    job = jobs.create("classify_item", user_id=str(user.id), item_id=str(item.id))
    tasks.process_garment.delay(job.id, str(item.id), key)
    return JobAccepted(job_id=job.id, status=job.status, item_id=str(item.id))


@router.get("/items/jobs/{job_id}")
def item_job(job_id: str, user: User = Depends(get_current_user)):
    job = jobs.get_owned(job_id, str(user.id))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return {"job_id": job_id, "status": job.status, "result": job.result, "error": job.error}


@router.get("/items", response_model=ItemListOut)
def list_items(category: str | None = None, active_only: bool = True,
               db: Session = Depends(get_db),
               user: User = Depends(get_current_user)) -> ItemListOut:
    stmt = select(ClothingItem).where(ClothingItem.user_id == user.id)
    if active_only:
        stmt = stmt.where(ClothingItem.is_active == True)  # noqa: E712
    if category:
        stmt = stmt.where(ClothingItem.category == category)
    stmt = stmt.order_by(ClothingItem.created_at.desc())
    items = list(db.scalars(stmt))
    wear = wear_stats(db, user.id)
    return ItemListOut(items=[item_out(i, wear) for i in items], count=len(items))


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: str, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)) -> ItemOut:
    return item_out(_owned_item(db, user, item_id), wear_stats(db, user.id))


@router.patch("/items/{item_id}", response_model=ItemOut)
def correct_tags(item_id: str, body: ItemPatchIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)) -> ItemOut:
    item = _owned_item(db, user, item_id)
    patch = body.model_dump(exclude_unset=True)
    if "category" in patch and patch["category"] not in CATEGORIES:
        raise HTTPException(422,
                            f"category must be one of {sorted(CATEGORIES)}")
    for field in ("formality_score", "warmth_score"):
        if patch.get(field) is not None and not 1 <= patch[field] <= 5:
            raise HTTPException(422, f"{field} must be 1-5")
    for field, value in patch.items():
        setattr(item, field, value)
    # a manual correction is ground truth → mark fully confident
    if patch:
        item.classification_confidence = 1.0
        item.tags = [t for t in (item.tags or []) if t != "needs-review"]
    db.commit()
    db.refresh(item)
    return item_out(item, wear_stats(db, user.id))


@router.delete("/items/{item_id}", status_code=204)
def soft_delete(item_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> None:
    item = _owned_item(db, user, item_id)
    item.is_active = False          # soft delete (spec §2.4)
    db.commit()
    return None
