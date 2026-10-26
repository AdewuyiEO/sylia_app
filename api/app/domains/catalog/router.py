"""Discover (users), the Partner API (brands) and brand onboarding (admin).

Discover only ever shows a product that clears the fit gate for THIS user's
closet; ranking is by fit, never by commission. Every response carries the
commission disclosure. Brands get their catalog in through the Partner API and
get back aggregated, k-anonymous demand insights — never individual users.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ...config import get_settings
from ...core.kv import kv
from ...db import get_db
from ...deps import get_current_user
from ...models import (User, Brand, Product, ClothingItem, AffiliateRecommendation,
                       Outfit, OutfitItem)
from ..daily_look import service as look_service
from . import gap
from .service import (CATEGORIES, new_partner_key, hash_key, ships_to, product_card,
                      to_garment)

settings = get_settings()
router = APIRouter(prefix="/v1", tags=["discover"])
partner = APIRouter(prefix="/v1/partner", tags=["partner"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])

AFFILIATE_FIT_THRESHOLD = 0.6
DISCLOSURE = ("Sylia may earn a commission if you buy through these links. "
              "Products are ranked only by how well they work with your closet.")
_MAX_SCAN = 300          # products analysed per Discover request


def gate_affiliate(candidates: list[dict]) -> list[dict]:
    """Keep only products that clear the fit threshold. Applied before anything is
    written or returned, so an under-fit product can never reach the user."""
    return [c for c in candidates if (c.get("fit_score") or 0) >= AFFILIATE_FIT_THRESHOLD]


# ── Discover ────────────────────────────────────────────────────────────────
def _closet_fingerprint(items: list[ClothingItem]) -> str:
    import hashlib
    raw = "|".join(sorted(f"{i.id}:{i.category}:{i.subcategory}:{i.primary_color}:{i.formality_score}"
                          f":{i.warmth_score}" for i in items))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


@router.get("/discover")
def discover(category: str | None = None, limit: int = 12, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    from ..daily_look.router import _inputs
    items, body_row, ident_row = _inputs(db, user)
    limit = max(1, min(limit, 30))
    if category is not None and category not in CATEGORIES:
        raise HTTPException(422, "Unknown category")
    if not items:
        return {"recommendations": [], "disclosure": DISCLOSURE,
                "reason": "Add a few pieces to your closet and we'll find what completes it."}

    day = look_service.local_today(user)
    cache_key = f"discover:{user.id}:{day}:{category}:{_closet_fingerprint(items)}:{user.country}"
    scored = kv.get(cache_key)
    if scored is None:
        wardrobe = [look_service._garment_from_row(i) for i in items]
        body = look_service._body_from_row(body_row)
        ident = look_service._identity_from_row(ident_row)

        stmt = (select(Product, Brand).join(Brand, Brand.id == Product.brand_id)
                .where(Product.in_stock == True, Brand.is_active == True)  # noqa: E712
                .order_by(Product.updated_at.desc()).limit(_MAX_SCAN))
        if category:
            stmt = stmt.where(Product.category == category)
        scored = []
        for product, brand in db.execute(stmt):
            if not ships_to(product, brand, user.country):
                continue
            res = gap.analyze(to_garment(product), wardrobe, body, ident)
            scored.append({"product_id": str(product.id), "brand_id": str(brand.id),
                           "fit_score": res.fit_score, "unlocks": res.unlocks,
                           "pairs_with": res.pairs_with, "rationale": gap.rationale(res)})
        scored = gate_affiliate(scored)
        scored.sort(key=lambda c: (-c["fit_score"], -c["unlocks"], c["product_id"]))
        kv.set(cache_key, scored, ttl=6 * 3600)

    out = []
    for c in scored[:limit]:
        product = db.get(Product, uuid.UUID(c["product_id"]))
        if product is None:
            continue
        brand = db.get(Brand, product.brand_id)
        rec = AffiliateRecommendation(
            user_id=user.id, product_id=product.id, brand_id=brand.id,
            retailer=brand.name, product_url=product.product_url, fit_score=c["fit_score"],
            rationale=c["rationale"], country=user.country, unlocks=c["unlocks"])
        db.add(rec)
        db.flush()
        out.append({**product_card(product, brand, user.country), "recommendation_id": str(rec.id),
                    "fit_score": c["fit_score"], "unlocks": c["unlocks"],
                    "pairs_with": c["pairs_with"], "rationale": c["rationale"]})
    db.commit()
    return {"recommendations": out, "disclosure": DISCLOSURE}


def _tracked(url: str, rec_id: str) -> str:
    parts = urlparse(url)
    q = dict(parse_qsl(parts.query))
    q.setdefault("utm_source", "sylia")
    q.setdefault("utm_medium", "app")
    q["sylia_ref"] = rec_id
    return urlunparse(parts._replace(query=urlencode(q)))


@router.post("/discover/{rec_id}/click")
def click(rec_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        rec = db.get(AffiliateRecommendation, uuid.UUID(rec_id))
    except ValueError:
        rec = None
    if rec is None or rec.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation not found")
    product = db.get(Product, rec.product_id) if rec.product_id else None
    if rec.clicked_at is None:
        rec.clicked_at = datetime.now(timezone.utc)
        db.commit()
    url = (product.affiliate_url or product.product_url) if product else rec.product_url
    return {"url": _tracked(url, rec_id)}


class FromProductIn(BaseModel):
    product_id: str
    size: str | None = Field(default=None, max_length=20)


@router.post("/wardrobe/items/from-product", status_code=201)
def add_from_product(body: FromProductIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Bought it? It goes straight into the closet with catalog-accurate tags — no
    photo, no CV, no confirm step."""
    from ..closet.router import item_out
    try:
        product = db.get(Product, uuid.UUID(body.product_id))
    except ValueError:
        product = None
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    brand = db.get(Brand, product.brand_id)
    item = ClothingItem(
        user_id=user.id, category=product.category, subcategory=product.subcategory,
        primary_color=product.primary_color, secondary_color=product.secondary_color,
        pattern=product.pattern, fit=product.fit, formality_score=product.formality_score,
        warmth_score=product.warmth_score, tags=list(product.tags or []) + ([f"size:{body.size}"] if body.size else []),
        classification_confidence=1.0, brand=brand.name if brand else None,
        brand_id=product.brand_id, product_id=product.id, external_image_url=product.image_url,
        is_active=True)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_out(item)


# ── Partner API (brands) ────────────────────────────────────────────────────
def current_brand(x_partner_key: str | None = Header(default=None), db: Session = Depends(get_db)) -> Brand:
    if not x_partner_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-Partner-Key")
    brand = db.scalar(select(Brand).where(Brand.api_key_hash == hash_key(x_partner_key)))
    if brand is None or not brand.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid partner key")
    return brand


class PriceIn(BaseModel):
    country: str | None = Field(default=None, min_length=2, max_length=2)
    currency: str = Field(min_length=3, max_length=3)
    amount_minor: int = Field(ge=0)


class ProductIn(BaseModel):
    external_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    category: str
    subcategory: str | None = Field(default=None, max_length=60)
    primary_color: str | None = Field(default=None, max_length=40)
    secondary_color: str | None = Field(default=None, max_length=40)
    pattern: str = "solid"
    fit: str = Field(default="regular", pattern="^(slim|regular|oversized)$")
    formality_score: int = Field(default=3, ge=1, le=5)
    warmth_score: int = Field(default=3, ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=30)
    prices: list[PriceIn] = Field(default_factory=list, max_length=60)
    regions: list[str] = Field(default_factory=list, max_length=250)
    sizes: list[str] = Field(default_factory=list, max_length=40)
    image_url: str | None = None
    product_url: str
    affiliate_url: str | None = None
    in_stock: bool = True
    attributes: dict = Field(default_factory=dict)

    @field_validator("category")
    @classmethod
    def _cat(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {sorted(CATEGORIES)}")
        return v

    @field_validator("product_url", "affiliate_url", "image_url")
    @classmethod
    def _https(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://"):
            raise ValueError("URLs must be https")
        return v


class ProductBatchIn(BaseModel):
    products: list[ProductIn] = Field(max_length=500)


@partner.get("/me")
def partner_me(brand: Brand = Depends(current_brand), db: Session = Depends(get_db)):
    n = db.scalar(select(func.count()).select_from(Product).where(Product.brand_id == brand.id))
    return {"brand": {"id": str(brand.id), "name": brand.name, "slug": brand.slug,
                      "regions": brand.regions}, "products": n}


@partner.put("/products")
def upsert_products(body: ProductBatchIn, brand: Brand = Depends(current_brand),
                    db: Session = Depends(get_db)):
    created = updated = 0
    for p in body.products:
        row = db.scalar(select(Product).where(Product.brand_id == brand.id,
                                              Product.external_id == p.external_id))
        data = p.model_dump()
        data["prices"] = [pr.model_dump() for pr in p.prices]
        data["regions"] = [r.upper() for r in p.regions]
        data["subcategory"] = (p.subcategory or "").lower() or None
        data["primary_color"] = (p.primary_color or "").lower() or None
        data["secondary_color"] = (p.secondary_color or "").lower() or None
        if row is None:
            db.add(Product(brand_id=brand.id, **data))
            created += 1
        else:
            for k, v in data.items():
                setattr(row, k, v)
            updated += 1
    db.commit()
    return {"created": created, "updated": updated}


@partner.delete("/products/{external_id}", status_code=204)
def remove_product(external_id: str, brand: Brand = Depends(current_brand), db: Session = Depends(get_db)):
    row = db.scalar(select(Product).where(Product.brand_id == brand.id, Product.external_id == external_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    row.in_stock = False   # keep the row: closets and history may reference it
    db.commit()
    return None


def _k_anon(rows: dict[str, set], k: int) -> dict[str, int]:
    """Only report buckets backed by at least k distinct users."""
    return {key: len(users) for key, users in rows.items() if len(users) >= k}


@partner.get("/insights")
def insights(days: int = 30, brand: Brand = Depends(current_brand), db: Session = Depends(get_db)):
    """Aggregated performance + demand. Every breakdown is k-anonymous: a bucket
    with fewer than INSIGHTS_MIN_COHORT distinct users is suppressed."""
    k = settings.insights_min_cohort
    since = datetime.now(timezone.utc) - timedelta(days=min(max(days, 1), 365))
    recs = list(db.execute(
        select(AffiliateRecommendation.user_id, AffiliateRecommendation.product_id,
               AffiliateRecommendation.country, AffiliateRecommendation.clicked_at,
               AffiliateRecommendation.fit_score, AffiliateRecommendation.unlocks)
        .where(AffiliateRecommendation.brand_id == brand.id, AffiliateRecommendation.shown_at >= since)))

    users_all = {r.user_id for r in recs}
    clickers = {r.user_id for r in recs if r.clicked_at}
    by_country: dict[str, set] = {}
    by_product: dict[str, set] = {}
    for r in recs:
        by_country.setdefault(r.country or "unknown", set()).add(r.user_id)
        by_product.setdefault(str(r.product_id), set()).add(r.user_id)

    # post-purchase: pieces from this brand in closets, and how often they're worn
    closet_rows = list(db.execute(select(ClothingItem.id, ClothingItem.user_id)
                                  .where(ClothingItem.brand_id == brand.id, ClothingItem.is_active == True)))  # noqa: E712
    owners = {u for _, u in closet_rows}
    wears = db.scalar(
        select(func.count()).select_from(OutfitItem)
        .join(Outfit, Outfit.id == OutfitItem.outfit_id)
        .join(ClothingItem, ClothingItem.id == OutfitItem.clothing_item_id)
        .where(ClothingItem.brand_id == brand.id, Outfit.user_feedback == "worn",
               Outfit.outfit_date >= since.date())) or 0

    enough = len(users_all) >= k
    return {
        "window_days": days, "min_cohort": k,
        "reach": {"users": len(users_all) if enough else None,
                  "impressions": len(recs) if enough else None,
                  "click_through_users": len(clickers) if enough else None,
                  "avg_fit_score": round(sum(float(r.fit_score or 0) for r in recs) / len(recs), 3)
                  if enough and recs else None},
        "by_country": _k_anon(by_country, k),
        "top_products_by_reach": dict(sorted(_k_anon(by_product, k).items(), key=lambda kv_: -kv_[1])[:20]),
        "in_closets": {"items": len(closet_rows), "owners": len(owners)} if len(owners) >= k else None,
        "wears_logged": wears if len(owners) >= k else None,
    }


# ── Admin: brand onboarding ─────────────────────────────────────────────────
def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    import hmac
    if not settings.admin_token or not x_admin_token or \
            not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin token required")


class BrandIn(BaseModel):
    slug: str = Field(pattern="^[a-z0-9-]{2,60}$")
    name: str = Field(min_length=1, max_length=120)
    website: str | None = None
    logo_url: str | None = None
    regions: list[str] = Field(default_factory=list)
    commission_bps: int | None = Field(default=None, ge=0, le=10000)


@admin.post("/brands", status_code=201, dependencies=[Depends(require_admin)])
def create_brand(body: BrandIn, db: Session = Depends(get_db)):
    if db.scalar(select(Brand).where(Brand.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug taken")
    key, key_hash = new_partner_key()
    brand = Brand(**body.model_dump(), api_key_hash=key_hash)
    brand.regions = [r.upper() for r in body.regions]
    db.add(brand)
    db.commit()
    return {"brand_id": str(brand.id), "partner_key": key,
            "note": "Store this key now — it is shown only once."}


@admin.post("/brands/{brand_id}/rotate-key", dependencies=[Depends(require_admin)])
def rotate_key(brand_id: str, db: Session = Depends(get_db)):
    brand = db.get(Brand, uuid.UUID(brand_id))
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    key, brand.api_key_hash = new_partner_key()
    db.commit()
    return {"brand_id": brand_id, "partner_key": key}
