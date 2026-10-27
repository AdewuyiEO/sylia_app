"""Try-on glue: the user's profile → Body, a garment's size chart, garment image
bytes, and rendering one try. Router and worker both call into here."""
from __future__ import annotations
import io
import ipaddress
import socket
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.storage import storage
from ...models import TryOnProfile, TryOnRender, ClothingItem, Product
from . import fit as F
from .render import render, RenderError

LANDMARKS = ("head", "l_shoulder", "r_shoulder", "l_hip", "r_hip", "feet")
RETENTION_DAYS = {"30d": 30, "keep": None}
DAILY_RENDER_CAP = 60
MAX_REMOTE_BYTES = 10 * 1024 * 1024
DEFAULT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


# ---------- profile ----------

def get_profile(db: Session, user_id) -> TryOnProfile | None:
    """The live profile, purging it first if its retention window has passed."""
    p = db.scalar(select(TryOnProfile).where(TryOnProfile.user_id == user_id))
    if p is not None and p.expires_at is not None and _aware(p.expires_at) <= _now():
        delete_profile(db, user_id)
        return None
    return p


def body_of(p: TryOnProfile) -> F.Body:
    return F.Body(p.height_cm, p.bust_cm, p.waist_cm, p.hips_cm, p.inseam_cm)


def store_person_photo(user_id, upload_key: str) -> str:
    """Re-encode the uploaded photo (drops EXIF/GPS, normalises orientation) into the
    private try-on namespace, and delete the raw upload."""
    raw = storage.get_bytes(upload_key)
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    s = 1600 / max(img.size)
    if s < 1:
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    key = f"tryon/{user_id}/person-{uuid.uuid4().hex}.jpg"
    storage.put_bytes(key, buf.getvalue(), "image/jpeg")
    try:
        storage.delete(upload_key)
    except Exception:
        pass
    return key


def expiry_for(retention: str) -> datetime | None:
    days = RETENTION_DAYS[retention]
    return _now() + timedelta(days=days) if days else None


def delete_profile(db: Session, user_id) -> None:
    """Photo, every rendered try, and the rows. Storage errors never block the wipe."""
    keys = [r.image_key for r in db.scalars(select(TryOnRender).where(TryOnRender.user_id == user_id))]
    p = db.scalar(select(TryOnProfile).where(TryOnProfile.user_id == user_id))
    if p is not None:
        keys.append(p.photo_key)
    db.query(TryOnRender).filter(TryOnRender.user_id == user_id).delete(synchronize_session=False)
    db.query(TryOnProfile).filter(TryOnProfile.user_id == user_id).delete(synchronize_session=False)
    db.commit()
    for k in keys:
        try:
            storage.delete(k)
        except Exception:
            pass


# ---------- garments ----------

def _clean_chart(raw) -> dict:
    out = {}
    if not isinstance(raw, dict):
        return out
    for size, m in list(raw.items())[:40]:
        if not isinstance(m, dict):
            continue
        row = {}
        for k in ("bust", "waist", "hips", "length"):
            v = m.get(k)
            if isinstance(v, (int, float)) and 20 <= v <= 250:
                row[k] = float(v)
        if row:
            out[str(size)[:20]] = row
    return out


def chart_for_product(product: Product) -> tuple[dict, str]:
    brand = _clean_chart((product.attributes or {}).get("size_chart"))
    if brand:
        return brand, "brand"
    sizes = product.sizes or DEFAULT_SIZES
    return F.standard_chart(sizes, product.category, product.fit or "regular"), "standard"


def chart_for_item(item: ClothingItem, body: F.Body) -> tuple[dict, str]:
    label = item.size_label or "Yours"
    measured = _clean_chart({label: item.garment_measurements or {}})
    if measured:
        return measured, "measured"
    return {label: F.estimate_own_garment(body, item.category, item.fit)}, "estimated"


def fit_payload(body: F.Body, chart: dict, category: str, fit: str, source: str) -> dict:
    table = F.fit_table(body, chart, category, fit or "regular")
    best = F.recommend(table)
    return {
        "category": category,
        "renderable": category in F.RENDERABLE,
        "chart_source": source,          # brand|standard|measured|estimated
        "recommended": best.size if best else None,
        "sizes": [{**f.as_dict(), "explanation": F.explain(f, category, body)} for f in table],
    }


def _public_https(url: str) -> bool:
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname:
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, 443, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


def fetch_remote_image(url: str) -> bytes:
    """Brand product images: https only, public hosts only, size-capped."""
    import httpx
    if not _public_https(url):
        raise RenderError("Product image isn't reachable")
    with httpx.Client(timeout=10, follow_redirects=False) as c:
        with c.stream("GET", url) as r:
            r.raise_for_status()
            buf = bytearray()
            for chunk in r.iter_bytes():
                buf += chunk
                if len(buf) > MAX_REMOTE_BYTES:
                    raise RenderError("Product image too large")
    return bytes(buf)


def garment_bytes(item: ClothingItem | None, product: Product | None) -> bytes:
    if item is not None:
        key = item.s3_key_processed or item.s3_key_original
        if key:
            return storage.get_bytes(key)
        if item.external_image_url:
            return fetch_remote_image(item.external_image_url)
        raise RenderError("This piece has no photo yet")
    if product is not None and product.image_url:
        return fetch_remote_image(product.image_url)
    raise RenderError("This product has no image")


# ---------- rendering ----------

def renders_today(db: Session, user_id) -> int:
    start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    return len(db.scalars(select(TryOnRender.id).where(TryOnRender.user_id == user_id,
                                                       TryOnRender.created_at >= start)).all())


def run_render(db: Session, user_id, item_id: str | None, product_id: str | None, size: str) -> TryOnRender:
    prof = get_profile(db, user_id)
    if prof is None:
        raise RenderError("Set up your fitting-room photo first")
    body = body_of(prof)
    item = product = None
    if item_id:
        item = db.get(ClothingItem, uuid.UUID(item_id))
        if item is None or item.user_id != user_id or not item.is_active:
            raise RenderError("Piece not found")
        chart, source = chart_for_item(item, body)
        category, fit = item.category, item.fit or "regular"
    else:
        product = db.get(Product, uuid.UUID(product_id))
        if product is None:
            raise RenderError("Product not found")
        chart, source = chart_for_product(product)
        category, fit = product.category, product.fit or "regular"
    if size not in chart:
        raise RenderError(f"Size {size} isn't available")
    if category not in F.RENDERABLE:
        raise RenderError("Try-on covers tops, dresses, outerwear and bottoms for now")

    f = F.fit_size(body, size, chart[size], category, fit)
    jpeg = render(storage.get_bytes(prof.photo_key), prof.landmarks, body,
                  garment_bytes(item, product), category, chart[size])
    key = f"tryon/{user_id}/render-{uuid.uuid4().hex}.jpg"
    storage.put_bytes(key, jpeg, "image/jpeg")
    row = TryOnRender(user_id=user_id, item_id=item.id if item else None,
                      product_id=product.id if product else None, size=size, image_key=key,
                      fit={**f.as_dict(), "explanation": F.explain(f, category, body),
                           "chart_source": source, "category": category})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def render_out(r: TryOnRender) -> dict:
    return {"id": str(r.id), "item_id": str(r.item_id) if r.item_id else None,
            "product_id": str(r.product_id) if r.product_id else None, "size": r.size,
            "image_url": storage.presign_get(r.image_key), "fit": r.fit,
            "created_at": _aware(r.created_at).isoformat()}
