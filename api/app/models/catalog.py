"""brands, products — the partner catalog behind Discover (fit-gated affiliate)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (DateTime, Uuid, ForeignKey, JSON, String, Integer, SmallInteger,
                        Boolean, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    regions: Mapped[list] = mapped_column(JSON, default=list)        # ISO countries shipped to; [] = worldwide
    commission_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)  # basis points
    api_key_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # sha256 of partner key
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("brand_id", "external_id", name="uq_product_brand_external"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), index=True)
    external_id: Mapped[str] = mapped_column(String)                 # the brand's SKU / style id
    title: Mapped[str] = mapped_column(String)
    # same vocabulary as clothing_items so the scorer reasons over both
    category: Mapped[str] = mapped_column(String, index=True)
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String, nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String, nullable=True)
    pattern: Mapped[str] = mapped_column(String, default="solid")
    fit: Mapped[str] = mapped_column(String, default="regular")
    formality_score: Mapped[int] = mapped_column(SmallInteger, default=3)
    warmth_score: Mapped[int] = mapped_column(SmallInteger, default=3)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    # per-region pricing: [{"country": "FR", "currency": "EUR", "amount_minor": 8900}]
    prices: Mapped[list] = mapped_column(JSON, default=list)
    regions: Mapped[list] = mapped_column(JSON, default=list)        # [] = wherever the brand ships
    sizes: Mapped[list] = mapped_column(JSON, default=list)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    product_url: Mapped[str] = mapped_column(String)
    affiliate_url: Mapped[str | None] = mapped_column(String, nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)     # materials, certifications, ...
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
