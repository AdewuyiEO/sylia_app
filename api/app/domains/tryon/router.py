"""Try-on (Sylia Pro): the user's private fitting-room photo + measurements, a
per-size fit read-out for any closet piece or Discover product, and rendered
previews of the user wearing it in the size they pick.

Setting up the photo is open to everyone (so the paywall can sell the result);
fit read-outs and renders need Pro (402 → paywall)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.jobs import jobs
from ...core.storage import storage
from ...db import get_db
from ...deps import get_current_user, require_entitled
from ...models import User, TryOnProfile, TryOnRender, ClothingItem, Product
from ...workers import tasks
from ..uploads.router import assert_owned_key
from . import service as S

router = APIRouter(prefix="/v1/tryon", tags=["tryon"])


class ProfileIn(BaseModel):
    photo_key: str | None = None          # required on first set-up; omit to keep the current photo
    consent: bool
    confirm_self: bool                    # "this is me and I'm 18+"
    height_cm: float = Field(ge=120, le=220)
    bust_cm: float = Field(ge=60, le=170)
    waist_cm: float = Field(ge=45, le=170)
    hips_cm: float = Field(ge=60, le=180)
    shoulder_cm: float | None = Field(default=None, ge=25, le=70)
    inseam_cm: float | None = Field(default=None, ge=50, le=110)
    landmarks: dict[str, list[float]]
    retention: str = Field(default="30d", pattern="^(30d|keep)$")

    @field_validator("landmarks")
    @classmethod
    def _lm(cls, v: dict) -> dict:
        missing = [k for k in S.LANDMARKS if k not in v]
        if missing:
            raise ValueError(f"landmarks missing {missing}")
        out = {}
        for k in S.LANDMARKS:
            p = v[k]
            if len(p) != 2 or not all(0 <= c <= 1 for c in p):
                raise ValueError(f"landmark {k} must be [x, y] within the photo (0..1)")
            out[k] = [round(float(p[0]), 4), round(float(p[1]), 4)]
        return out

    @model_validator(mode="after")
    def _order(self):
        L = self.landmarks
        sh = (L["l_shoulder"][1] + L["r_shoulder"][1]) / 2
        hip = (L["l_hip"][1] + L["r_hip"][1]) / 2
        if not L["head"][1] < sh < hip < L["feet"][1]:
            raise ValueError("landmarks must run head → shoulders → hips → feet, top to bottom")
        if L["feet"][1] - L["head"][1] < 0.4:
            raise ValueError("stand further back: head to feet must fill most of the photo")
        return self


def _profile_out(p: TryOnProfile | None) -> dict:
    if p is None:
        return {"exists": False}
    return {"exists": True, "photo_url": storage.presign_get(p.photo_key),
            "height_cm": p.height_cm, "bust_cm": p.bust_cm, "waist_cm": p.waist_cm,
            "hips_cm": p.hips_cm, "shoulder_cm": p.shoulder_cm, "inseam_cm": p.inseam_cm,
            "landmarks": p.landmarks, "retention": p.retention,
            "expires_at": S._aware(p.expires_at).isoformat() if p.expires_at else None}


@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _profile_out(S.get_profile(db, user.id))


@router.put("/profile")
def put_profile(body: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (body.consent and body.confirm_self):
        raise HTTPException(422, "Try-on needs your consent and confirmation that the photo is you")
    p = S.get_profile(db, user.id)
    if p is None and not body.photo_key:
        raise HTTPException(422, "Add a full-length photo of yourself")
    old_photo = None
    if body.photo_key:
        upload = assert_owned_key(user, body.photo_key, "tryon")
        new_key = S.store_person_photo(user.id, upload)
        if p is not None:
            old_photo = p.photo_key
    if p is None:
        p = TryOnProfile(user_id=user.id, photo_key=new_key, landmarks={},
                         height_cm=0, bust_cm=0, waist_cm=0, hips_cm=0)
        db.add(p)
    elif body.photo_key:
        p.photo_key = new_key
    for f in ("height_cm", "bust_cm", "waist_cm", "hips_cm", "shoulder_cm", "inseam_cm", "landmarks", "retention"):
        setattr(p, f, getattr(body, f))
    p.consent_at = S._now()
    p.expires_at = S.expiry_for(body.retention)
    db.commit()
    db.refresh(p)
    if old_photo:
        try:
            storage.delete(old_photo)
        except Exception:
            pass
    return _profile_out(p)


@router.delete("/profile", status_code=204)
def delete_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Wipes the photo, every saved try, and the measurements."""
    S.delete_profile(db, user.id)


def _garment(db: Session, user: User, item_id: str | None, product_id: str | None):
    if bool(item_id) == bool(product_id):
        raise HTTPException(422, "Pass exactly one of item_id or product_id")
    try:
        if item_id:
            item = db.get(ClothingItem, uuid.UUID(item_id))
            if item is None or item.user_id != user.id or not item.is_active:
                raise HTTPException(404, "Piece not found")
            return item, None
        product = db.get(Product, uuid.UUID(product_id))
        if product is None:
            raise HTTPException(404, "Product not found")
        return None, product
    except ValueError:
        raise HTTPException(404, "Not found")


@router.get("/fit")
def fit(item_id: str | None = Query(None), product_id: str | None = Query(None),
        db: Session = Depends(get_db), user: User = Depends(require_entitled)):
    """Per-size fit read-out on this user's body. Sylia suggests; the user picks."""
    prof = S.get_profile(db, user.id)
    if prof is None:
        raise HTTPException(409, "Set up your fitting-room photo first")
    body = S.body_of(prof)
    item, product = _garment(db, user, item_id, product_id)
    if item is not None:
        chart, source = S.chart_for_item(item, body)
        return S.fit_payload(body, chart, item.category, item.fit or "regular", source)
    chart, source = S.chart_for_product(product)
    return S.fit_payload(body, chart, product.category, product.fit or "regular", source)


class RenderIn(BaseModel):
    item_id: str | None = None
    product_id: str | None = None
    size: str = Field(min_length=1, max_length=20)


@router.post("/renders", status_code=202)
def create_render(body: RenderIn, db: Session = Depends(get_db), user: User = Depends(require_entitled)):
    if S.get_profile(db, user.id) is None:
        raise HTTPException(409, "Set up your fitting-room photo first")
    _garment(db, user, body.item_id, body.product_id)
    if S.renders_today(db, user.id) >= S.DAILY_RENDER_CAP:
        raise HTTPException(429, "That's today's try-ons — more tomorrow")
    job = jobs.create("tryon_render", user_id=str(user.id))
    tasks.render_tryon.delay(job.id, str(user.id), body.item_id, body.product_id, body.size)
    return {"job_id": job.id, "status": jobs.get(job.id).status}


@router.get("/renders/jobs/{job_id}")
def render_job(job_id: str, user: User = Depends(get_current_user)):
    job = jobs.get_owned(job_id, str(user.id))
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return {"job_id": job_id, "status": job.status, "result": job.result, "error": job.error}


@router.get("/renders")
def list_renders(db: Session = Depends(get_db), user: User = Depends(require_entitled)):
    rows = db.scalars(select(TryOnRender).where(TryOnRender.user_id == user.id)
                      .order_by(TryOnRender.created_at.desc()).limit(60)).all()
    return {"renders": [S.render_out(r) for r in rows]}


@router.delete("/renders/{render_id}", status_code=204)
def delete_render(render_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        r = db.get(TryOnRender, uuid.UUID(render_id))
    except ValueError:
        r = None
    if r is None or r.user_id != user.id:
        raise HTTPException(404, "Not found")
    key = r.image_key
    db.delete(r)
    db.commit()
    try:
        storage.delete(key)
    except Exception:
        pass


class ItemSizeIn(BaseModel):
    size_label: str | None = Field(default=None, max_length=20)
    measurements: dict[str, float] | None = None    # flat garment measurements, cm


@router.put("/items/{item_id}/size")
def set_item_size(item_id: str, body: ItemSizeIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    item, _ = _garment(db, user, item_id, None)
    item.size_label = body.size_label
    item.garment_measurements = S._clean_chart({"x": body.measurements or {}}).get("x")
    db.commit()
    return {"item_id": str(item.id), "size_label": item.size_label, "measurements": item.garment_measurements}
