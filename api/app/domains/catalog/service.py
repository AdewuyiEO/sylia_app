"""Catalog helpers: partner keys, regional availability/pricing, product → Garment."""
from __future__ import annotations

import hashlib
import secrets
from typing import Any

from ..daily_look.scorer import Garment

CATEGORIES = {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}


def new_partner_key() -> tuple[str, str]:
    """(plaintext key shown once to the brand, sha256 we store)."""
    key = "sylia_pk_" + secrets.token_urlsafe(32)
    return key, hash_key(key)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def ships_to(product: Any, brand: Any, country: str | None) -> bool:
    """Empty region lists mean worldwide; product regions override the brand's."""
    regions = product.regions or brand.regions or []
    if not regions or country is None:
        return True
    return country.upper() in {r.upper() for r in regions}


def price_for(product: Any, country: str | None) -> dict | None:
    prices = product.prices or []
    if country:
        for p in prices:
            if str(p.get("country", "")).upper() == country.upper():
                return p
    for p in prices:
        if not p.get("country"):          # a brand-wide default price
            return p
    return None


def to_garment(product: Any) -> Garment:
    return Garment(
        id=f"product:{product.id}",
        category=product.category,
        subcategory=product.subcategory or "",
        primary_color=product.primary_color or "",
        secondary_color=product.secondary_color,
        pattern=product.pattern or "solid",
        fit=product.fit or "regular",
        formality_score=int(product.formality_score or 3),
        warmth_score=int(product.warmth_score or 3),
        tags=list(product.tags or []),
    )


def product_card(product: Any, brand: Any, country: str | None) -> dict:
    return {
        "product_id": str(product.id),
        "title": product.title,
        "brand": {"name": brand.name, "slug": brand.slug, "logo_url": brand.logo_url},
        "category": product.category, "subcategory": product.subcategory,
        "primary_color": product.primary_color,
        "image_url": product.image_url,
        "price": price_for(product, country),
        "sizes": product.sizes or [],
        "attributes": product.attributes or {},
    }
