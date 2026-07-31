"""Body geometry from a photo (spec §1.1: MediaPipe Pose → ratios → silhouette).

Emits ratios WITH a confidence that reflects how trustworthy the landmarks are:
low visibility, an angled/partial body, or a clothed waist all pull confidence
down. The waist estimate from a clothed photo is the weakest signal, so we
approximate it from hip/shoulder geometry and never let it alone decide.

Optional heavy dep. Without mediapipe, returns None → the pipeline falls back to
the quiz path (which is fine, often better).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from .derive import Ratios

try:
    import mediapipe as mp
    _HAS_MP = True
except Exception:
    _HAS_MP = False


@dataclass
class GeometryResult:
    ratios: Ratios
    confidence: float


def has_mediapipe() -> bool:
    return _HAS_MP


def _dist(a, b) -> float:
    return float(np.hypot(a.x - b.x, a.y - b.y))


def estimate_geometry(image_rgb: np.ndarray) -> GeometryResult | None:
    if not _HAS_MP:
        return None
    try:
        mp_pose = mp.solutions.pose
        with mp_pose.Pose(static_image_mode=True, model_complexity=1,
                          enable_segmentation=False) as pose:
            res = pose.process(image_rgb)
    except Exception:
        # any MediaPipe/runtime failure → degrade to the quiz path, never raise
        return None
    if not res.pose_landmarks:
        return None

    L = mp_pose.PoseLandmark
    lm = res.pose_landmarks.landmark

    def pt(i): return lm[i.value]
    l_sh, r_sh = pt(L.LEFT_SHOULDER), pt(L.RIGHT_SHOULDER)
    l_hip, r_hip = pt(L.LEFT_HIP), pt(L.RIGHT_HIP)
    l_knee, r_knee = pt(L.LEFT_KNEE), pt(L.RIGHT_KNEE)
    l_ank, r_ank = pt(L.LEFT_ANKLE), pt(L.RIGHT_ANKLE)

    shoulder_w = _dist(l_sh, r_sh)
    hip_w = _dist(l_hip, r_hip)
    if hip_w < 1e-4 or shoulder_w < 1e-4:
        return None

    # torso: shoulder-mid → hip-mid; leg: hip-mid → ankle-mid
    sh_mid = ((l_sh.x + r_sh.x) / 2, (l_sh.y + r_sh.y) / 2)
    hip_mid = ((l_hip.x + r_hip.x) / 2, (l_hip.y + r_hip.y) / 2)
    ank_mid = ((l_ank.x + r_ank.x) / 2, (l_ank.y + r_ank.y) / 2)
    torso_len = float(np.hypot(sh_mid[0] - hip_mid[0], sh_mid[1] - hip_mid[1]))
    leg_len = float(np.hypot(hip_mid[0] - ank_mid[0], hip_mid[1] - ank_mid[1]))

    shoulder_hip = shoulder_w / hip_w
    torso_leg = torso_len / leg_len if leg_len > 1e-4 else 1.0
    # waist is not directly landmarked from a clothed photo — approximate as a
    # point between shoulder and hip width, and mark this the low-confidence part
    waist_hip = float(np.clip((0.45 * shoulder_w + 0.55 * hip_w) / hip_w, 0.6, 1.05))

    # confidence from landmark visibility + how frontal/complete the pose is
    key_vis = np.mean([l_sh.visibility, r_sh.visibility, l_hip.visibility,
                       r_hip.visibility, l_knee.visibility, r_knee.visibility])
    # penalise asymmetry (angled body) — left/right shoulder y should be close
    asymmetry = abs(l_sh.y - r_sh.y) + abs(l_hip.y - r_hip.y)
    confidence = float(np.clip(key_vis * (1 - min(asymmetry * 2, 0.5)), 0, 1))
    # cap: clothed-photo geometry is never high-certainty
    confidence = round(min(confidence, 0.75), 3)

    return GeometryResult(
        ratios=Ratios(shoulder_hip=round(shoulder_hip, 3),
                      waist_hip=round(waist_hip, 3),
                      torso_leg=round(torso_leg, 3)),
        confidence=confidence,
    )
