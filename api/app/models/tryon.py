"""tryon_profiles, tryon_renders — the user's private fitting-room photo + body
measurements, and the try-on previews rendered from them (Sylia Pro)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, ForeignKey, Float, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class TryOnProfile(Base):
    __tablename__ = "tryon_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    photo_key: Mapped[str] = mapped_column(String)              # tryon/{user_id}/person-*.jpg, private
    height_cm: Mapped[float] = mapped_column(Float)
    bust_cm: Mapped[float] = mapped_column(Float)               # chest for menswear
    waist_cm: Mapped[float] = mapped_column(Float)
    hips_cm: Mapped[float] = mapped_column(Float)
    shoulder_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    inseam_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    # normalised [x, y] anchors the user confirmed on their photo:
    # head, l_shoulder, r_shoulder, l_hip, r_hip, feet
    landmarks: Mapped[dict] = mapped_column(JSON, default=dict)
    retention: Mapped[str] = mapped_column(String, default="30d")   # 30d|keep
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class TryOnRender(Base):
    __tablename__ = "tryon_renders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clothing_items.id"), nullable=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    size: Mapped[str] = mapped_column(String)
    image_key: Mapped[str] = mapped_column(String)
    fit: Mapped[dict] = mapped_column(JSON, default=dict)         # the fit read-out at render time
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
