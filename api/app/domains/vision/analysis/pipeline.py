"""Body-analysis pipeline orchestrator (spec §1.1, §3.3).

image bytes → geometry (Pose) + undertone (FaceMesh) → derive silhouette/palette
→ a BodyAnalysis the worker persists to `body_profiles`. Every heavy stage
degrades independently; if neither CV signal is usable we return an explicitly
low-confidence, neutral-palette result that routes the user to the quiz — never
a confident guess.
"""
from __future__ import annotations

import io
import numpy as np
from PIL import Image

from .geometry import estimate_geometry, has_mediapipe
from .undertone import estimate_undertone
from .derive import classify_silhouette, assemble, from_quiz, BodyAnalysis


def analyze_body_images(front_bytes: bytes, face_bytes: bytes | None = None) -> BodyAnalysis:
    """Front photo drives geometry; the face crop (or the same photo) drives
    undertone. Returns a BodyAnalysis with per-signal confidence."""
    front_rgb = _to_rgb(front_bytes)
    face_rgb = _to_rgb(face_bytes) if face_bytes else front_rgb

    geo = estimate_geometry(front_rgb)
    ut = estimate_undertone(face_rgb)

    if geo is not None:
        silhouette, sil_conf = classify_silhouette(geo.ratios)
        # fold in the geometry confidence (a clean silhouette from noisy
        # landmarks is still uncertain)
        sil_conf = round(sil_conf * geo.confidence, 3)
    else:
        silhouette, sil_conf = None, 0.0

    undertone = ut.undertone if ut else None
    ut_conf = ut.confidence if ut else 0.0

    return assemble(silhouette, sil_conf, undertone, ut_conf, method="full_scan")


def analyze_from_quiz(undertone: str | None, silhouette: str | None) -> BodyAnalysis:
    return from_quiz(undertone, silhouette)


def cv_available() -> bool:
    return has_mediapipe()


def _to_rgb(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return np.asarray(img)
