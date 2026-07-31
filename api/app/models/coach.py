"""coach_conversations, coach_messages (spec §2.7)."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Uuid, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


def _uuid() -> uuid.UUID: return uuid.uuid4()
def _now() -> datetime: return datetime.now(timezone.utc)


class CoachConversation(Base):
    __tablename__ = "coach_conversations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)  # auto-summarised after first exchange
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CoachMessage(Base):
    __tablename__ = "coach_messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("coach_conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String)   # user|assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
