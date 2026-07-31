"""identity_profiles, body_profiles (spec §2.2, §2.3)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, ForeignKey, Numeric, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class IdentityProfile(Base):
    __tablename__ = "identity_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)  # 1:1
    psychological_traits: Mapped[dict] = mapped_column(JSON, default=dict)  # confidence_baseline, risk_tolerance, decision_fatigue_level
    style_aspirations: Mapped[list] = mapped_column(JSON, default=list)     # [{label, priority}]
    insecurities: Mapped[list] = mapped_column(JSON, default=list)          # [{area, note}]
    lifestyle_patterns: Mapped[dict] = mapped_column(JSON, default=dict)    # work_setting, activity_level, travel_frequency, social_density
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class BodyProfile(Base):
    __tablename__ = "body_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    intake_image_s3_key: Mapped[str | None] = mapped_column(String, nullable=True)  # deleted post-analysis unless retained
    shoulder_hip_ratio: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    torso_leg_ratio: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    silhouette_category: Mapped[str | None] = mapped_column(String, nullable=True)  # hourglass|rectangle|triangle|inverted_triangle|oval
    skin_undertone: Mapped[str | None] = mapped_column(String, nullable=True)       # warm|cool|neutral
    color_palette: Mapped[dict] = mapped_column(JSON, default=dict)                 # best_colors[], avoid_colors[], neutrals[]
    fit_rules: Mapped[list] = mapped_column(JSON, default=list)
    analysis_method: Mapped[str | None] = mapped_column(String, nullable=True)      # full_scan|quiz_fallback
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
