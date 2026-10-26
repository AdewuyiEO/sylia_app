"""clothing_items (spec §2.4)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, ForeignKey, SmallInteger, Numeric, JSON, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    s3_key_original: Mapped[str | None] = mapped_column(String, nullable=True)
    s3_key_processed: Mapped[str | None] = mapped_column(String, nullable=True)   # background removed
    category: Mapped[str] = mapped_column(String)          # top|bottom|dress|outerwear|shoes|accessory
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String, nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String, nullable=True)
    pattern: Mapped[str | None] = mapped_column(String, nullable=True)
    fit: Mapped[str | None] = mapped_column(String, nullable=True)                # slim|regular|oversized
    formality_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 1-5
    warmth_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)      # 1-5
    classification_confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # drives confirm step
    tags: Mapped[list] = mapped_column(JSON, default=list)
    # provenance: free-text brand from the user, or a catalog link when bought via Sylia
    brand: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"), nullable=True, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    external_image_url: Mapped[str | None] = mapped_column(String, nullable=True)  # catalog image when added from a product
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)                # soft delete
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
