"""calendar_connections, weather_cache, affiliate_recommendations (spec §2.8)."""
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import DateTime, Date, Uuid, ForeignKey, JSON, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    provider: Mapped[str] = mapped_column(String, default="google")
    access_token_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(String, nullable=True)
    category_mapping: Mapped[dict] = mapped_column(JSON, default=dict)  # keyword -> formality category (the 1-category signal)


class WeatherCache(Base):
    __tablename__ = "weather_cache"
    location_key: Mapped[str] = mapped_column(String, primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AffiliateRecommendation(Base):
    __tablename__ = "affiliate_recommendations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    outfit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("outfits.id"), nullable=True)
    retailer: Mapped[str | None] = mapped_column(String, nullable=True)
    product_url: Mapped[str | None] = mapped_column(String, nullable=True)
    fit_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # gate enforced at WRITE time
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    shown_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
