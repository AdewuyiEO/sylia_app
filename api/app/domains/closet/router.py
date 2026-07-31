"""Closet (spec §3.4) — real DB-backed reads/writes.

Upload creates a placeholder row immediately (status implied by NULL fields +
low confidence) and enqueues the CV job that fills it in. This means the item
shows up in the closet the instant it's uploaded, in a 'processing' visual
state — the client never waits on the worker to see the item exist.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import get_db
from ...deps import get_current_user
from ...models import User, ClothingItem
from ...core.jobs import jobs
from ...workers import tasks
from ...schemas.closet import (
    ItemUploadIn, ItemPatchIn, ItemOut, ItemListOut, JobAccepted,
)

router = APIRouter(prefix="/v1/wardrobe", tags=["closet"])


def _owned_item(db: Session, user: User, item_id: str) -> ClothingItem:
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    item = db.get(ClothingItem, iid)
    if not item or item.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.post("/items", status_code=202, response_model=JobAccepted)
def upload_item(body: ItemUploadIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> JobAccepted:
    # create the row now so it appears in the closet immediately, pre-classification
    item = ClothingItem(
        user_id=user.id,
        s3_key_original=body.s3_key_original,
        category="top",                       # provisional; the worker overwrites
        classification_confidence=None,        # NULL confidence == "still processing"
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    job = jobs.create("classify_item", user_id=str(user.id), item_id=str(item.id))
    tasks.process_garment.delay(job.id, str(item.id), body.s3_key_original)
    return JobAccepted(job_id=job.id, status=job.status)


@router.get("/items/jobs/{job_id}")
def item_job(job_id: str, user: User = Depends(get_current_user)):
    job = jobs.get(job_id)
    return {"job_id": job_id, "status": job.status if job else "unknown",
            "result": job.result if job else None}


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
    return ItemListOut(items=[ItemOut.model_validate(i) for i in items], count=len(items))


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: str, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)) -> ItemOut:
    return ItemOut.model_validate(_owned_item(db, user, item_id))


@router.patch("/items/{item_id}", response_model=ItemOut)
def correct_tags(item_id: str, body: ItemPatchIn, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)) -> ItemOut:
    item = _owned_item(db, user, item_id)
    patch = body.model_dump(exclude_unset=True)
    for field, value in patch.items():
        setattr(item, field, value)
    # a manual correction is ground truth → mark fully confident
    if patch:
        item.classification_confidence = 1.0
    db.commit()
    db.refresh(item)
    return ItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
def soft_delete(item_id: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> None:
    item = _owned_item(db, user, item_id)
    item.is_active = False          # soft delete (spec §2.4)
    db.commit()
    return None
