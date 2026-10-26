"""users, subscriptions (spec §2.1, §2.8)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()

def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)  # null for OAuth-only
    auth_provider: Mapped[str] = mapped_column(String, default="email")       # email|apple|google
    subscription_status: Mapped[str] = mapped_column(String, default="trial") # trial|active|past_due|canceled
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    apple_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)  # Sign in with Apple subject
    # worldwide: display + regional preferences (drive units, catalog region, currency)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    locale: Mapped[str] = mapped_column(String, default="en")             # BCP-47, e.g. fr-FR
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    units: Mapped[str] = mapped_column(String, default="metric")           # metric|imperial
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)    # IANA, e.g. Europe/Paris
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)    # app_store|play_store|stripe
    product_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="trial")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RevokedToken(Base):
    """Refresh tokens that were logged out or rotated. Rows can be purged once expired."""
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
