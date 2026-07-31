"""Closet CV pipeline orchestrator (spec §1.1).

bytes → background removal → zero-shot attributes → dominant colour → a single
ClassificationResult the worker persists to `clothing_items`. Every heavy stage
degrades independently, so the pipeline ALWAYS returns a usable result:
  * colour extraction is always real (k-means, no model);
  * if CLIP is absent, category/subcategory fall back to a default and
    `confidence` is low → the client's confirm/correct step handles it;
  * if rembg is absent, colour runs on the raw image (documented trade-off).
"""
from __future__ import annotations

import io
from dataclasses import dataclass, asdict
from PIL import Image

from .bg_removal import remove_background, has_rembg
from .classify import classify_attributes, has_clip
from .color import extract_colors
from .taxonomy import category_for, priors_for


@dataclass
class ClassificationResult:
    s3_key_processed: str | None
    category: str
    subcategory: str | None
    primary_color: str | None
    secondary_color: str | None
    pattern: str
    fit: str
    formality_score: int
    warmth_score: int
    confidence: float
    tags: list[str]
    cutout_png: bytes | None = None    # the bg-removed image bytes (not a DB column)

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("cutout_png", None)       # never persisted to the row
        return d


def classify_garment(image_bytes: bytes, *, processed_key: str | None = None
                     ) -> ClassificationResult:
    img = Image.open(io.BytesIO(image_bytes))
    cutout = remove_background(img)                 # RGBA (or passthrough)

    attrs = classify_attributes(cutout)             # None if CLIP absent
    primary, secondary = extract_colors(cutout)     # always real

    # encode the cut-out so the worker can persist it as s3_key_processed
    cutout_png: bytes | None = None
    try:
        _buf = io.BytesIO()
        cutout.save(_buf, "PNG")
        cutout_png = _buf.getvalue()
    except Exception:
        cutout_png = None

    if attrs is not None:
        subcategory = attrs.subcategory
        category = category_for(subcategory)
        formality, warmth = priors_for(subcategory)
        pattern, fit, confidence = attrs.pattern, attrs.fit, attrs.confidence
    else:
        # no classifier yet → provisional, low confidence, flagged for confirm
        subcategory, category = None, "top"
        formality, warmth = 3, 2
        pattern, fit, confidence = "solid", "regular", 0.3

    tags: list[str] = []
    if not has_clip():
        tags.append("needs-review")
    if not has_rembg():
        tags.append("bg-not-removed")

    return ClassificationResult(
        s3_key_processed=processed_key,
        category=category,
        subcategory=subcategory,
        primary_color=primary,
        secondary_color=secondary,
        pattern=pattern,
        fit=fit,
        formality_score=formality,
        warmth_score=warmth,
        confidence=confidence,
        tags=tags,
        cutout_png=cutout_png,
    )
