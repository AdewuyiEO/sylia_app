"""Skin undertone from a photo (spec §1.1: FaceMesh cheek/forehead → RGB/HSV heuristic).

The fairness-critical stage. Undertone from a phone selfie in uncontrolled light
is unreliable, and RGB/HSV heuristics have historically skewed on darker skin
tones. Mitigations baked in here:

  * grey-world white-balance normalisation before sampling, to reduce the
    lighting/white-balance sensitivity that causes most errors;
  * confidence is LOWERED, not hidden, when the sample is dark, low-saturation,
    or the regions are small/occluded — so the client routes to the quiz, and
    the palette builder widens toward neutrals rather than committing;
  * we classify on a warm/cool axis with a wide 'neutral' dead-zone, because a
    confident wrong warm/cool call is the harmful failure mode.

Without mediapipe → returns None (quiz path).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

try:
    import mediapipe as mp
    _HAS_MP = True
except Exception:
    _HAS_MP = False


@dataclass
class UndertoneResult:
    undertone: str          # warm | cool | neutral
    confidence: float


def has_mediapipe() -> bool:
    return _HAS_MP


# FaceMesh landmark indices for cheek + forehead sample patches
_CHEEK_L, _CHEEK_R, _FOREHEAD = 234, 454, 10


def _grey_world(rgb: np.ndarray) -> np.ndarray:
    """Cheap white-balance: scale channels so the mean is grey. Cuts the biggest
    source of undertone error (colour cast from lighting)."""
    means = rgb.reshape(-1, 3).mean(axis=0) + 1e-6
    grey = means.mean()
    scaled = rgb * (grey / means)
    return np.clip(scaled, 0, 255).astype(np.float64)


def estimate_undertone(image_rgb: np.ndarray) -> UndertoneResult | None:
    if not _HAS_MP:
        return None
    h, w = image_rgb.shape[:2]
    try:
        mp_fm = mp.solutions.face_mesh
        with mp_fm.FaceMesh(static_image_mode=True, max_num_faces=1,
                            refine_landmarks=False) as fm:
            res = fm.process(image_rgb)
    except Exception:
        return None
    if not res.multi_face_landmarks:
        return None
    lms = res.multi_face_landmarks[0].landmark

    balanced = _grey_world(image_rgb.astype(np.float64))
    samples = []
    for idx in (_CHEEK_L, _CHEEK_R, _FOREHEAD):
        x, y = int(lms[idx].x * w), int(lms[idx].y * h)
        patch = balanced[max(0, y - 6):y + 6, max(0, x - 6):x + 6].reshape(-1, 3)
        if len(patch):
            samples.append(patch)
    if not samples:
        return None
    skin = np.concatenate(samples, axis=0)
    r, g, b = skin[:, 0].mean(), skin[:, 1].mean(), skin[:, 2].mean()

    # warm/cool axis: red-vs-blue balance, with a wide neutral dead-zone
    rb = (r - b) / (r + b + 1e-6)          # >0 warm, <0 cool
    brightness = (r + g + b) / 3
    saturation = (max(r, g, b) - min(r, g, b)) / (max(r, g, b) + 1e-6)

    if rb > 0.10:
        tone = "warm"
    elif rb < -0.04:
        tone = "cool"
    else:
        tone = "neutral"

    # confidence: strong only with clear rb signal, adequate brightness & saturation.
    # dark or low-saturation samples (where the heuristic is least reliable and
    # historically biased) get LOWER confidence, not a forced guess.
    signal = min(abs(rb) / 0.15, 1.0)
    bright_ok = np.clip((brightness - 30) / 60, 0.3, 1.0)   # don't over-penalise dark skin, but flag uncertainty
    sat_ok = np.clip(saturation / 0.2, 0.3, 1.0)
    confidence = round(float(np.clip(signal * bright_ok * sat_ok, 0, 1)) * 0.7, 3)
    # hard cap: selfie undertone is never high-certainty
    confidence = min(confidence, 0.6)
    return UndertoneResult(undertone=tone, confidence=confidence)
