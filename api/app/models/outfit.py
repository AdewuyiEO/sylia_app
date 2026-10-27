"""outfits, outfit_items (spec §2.5, §2.6)."""
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import DateTime, Date, Uuid, ForeignKey, Numeric, JSON, String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class Outfit(Base):
    __tablename__ = "outfits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    outfit_date: Mapped[date] = mapped_column(Date, index=True)
    rank: Mapped[int] = mapped_column(SmallInteger, default=1)            # 1 = the day's top pick
    context: Mapped[dict] = mapped_column(JSON, default=dict)         # weather snapshot, event_category, event_time
    score_total: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)  # color/body/context/identity subscores
    explanation: Mapped[str | None] = mapped_column(String, nullable=True)  # Claude-generated, grounded in breakdown
    user_feedback: Mapped[str] = mapped_column(String, default="pending")   # pending|worn|skipped|loved|disliked
    feedback_note: Mapped[str | None] = mapped_column(String, nullable=True)
    worn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OutfitItem(Base):
    __tablename__ = "outfit_items"

    outfit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("outfits.id"), primary_key=True)
    clothing_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clothing_items.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String)   # top|bottom|dress|outerwear|shoes|accessory
