"""Request/response schemas for the closet domain."""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ItemUploadIn(BaseModel):
    """Client uploads the raw photo to storage, then registers its key here."""
    s3_key_original: str


class ItemPatchIn(BaseModel):
    """User corrections to auto-tags. Every field optional — patch semantics.
    These corrections are the labeled data a future classifier trains on."""
    category: str | None = None
    subcategory: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    pattern: str | None = None
    fit: str | None = None
    formality_score: int | None = None
    warmth_score: int | None = None
    tags: list[str] | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    subcategory: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    pattern: str | None = None
    fit: str | None = None
    formality_score: int | None = None
    warmth_score: int | None = None
    classification_confidence: float | None = None
    tags: list = []
    is_active: bool
    s3_key_original: str | None = None
    s3_key_processed: str | None = None
    created_at: datetime


class ItemListOut(BaseModel):
    items: list[ItemOut]
    count: int


class JobAccepted(BaseModel):
    job_id: str
    status: str
