"""Body-analysis derivations (spec §1.1) — the PURE, testable core.

Two hard design decisions, both driven by the accuracy/fairness caution:

  1. Every output carries a CONFIDENCE and the method that produced it. A single
     clothed photo is a noisy instrument (waist landmarks especially), so we never
     present a silhouette or undertone as a verdict — the client shows it as an
     editable guess, and low confidence routes to the quiz cross-check.

  2. The scorer consumes these as *wide-uncertainty priors*, not facts. Silhouette
     drives fit_rules gently; undertone drives a palette that is mostly neutrals
     (which flatter everyone) plus a few tone-leaning accents. If undertone is
     low-confidence we widen the palette rather than commit to warm/cool — a
     wrong strong palette is worse than a cautious neutral one.

This module maps geometry ratios → silhouette and undertone → palette/fit_rules.
The CV extraction (MediaPipe) lives in geometry.py / undertone.py and feeds this.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ── silhouette from ratios ───────────────────────────────────────────────────
# thresholds are deliberately generous; near a boundary we return low confidence
@dataclass
class Ratios:
    shoulder_hip: float       # shoulder width / hip width
    waist_hip: float          # waist width / hip width (least reliable clothed)
    torso_leg: float          # torso length / leg length


def classify_silhouette(r: Ratios) -> tuple[str, float]:
    """Return (silhouette_category, confidence 0-1).

    Categories: hourglass, rectangle, triangle, inverted_triangle, oval.
    Confidence drops near category boundaries and when the waist signal (the
    noisiest from a clothed photo) is doing the deciding.
    """
    sh, wh = r.shoulder_hip, r.waist_hip
    scores = {
        "hourglass":          _bell(sh, 1.0, 0.10) * _bell(wh, 0.72, 0.10),
        "rectangle":          _bell(sh, 1.0, 0.08) * _bell(wh, 0.86, 0.08),
        "triangle":           _bell(sh, 0.85, 0.10) * _bell(wh, 0.80, 0.12),
        "inverted_triangle":  _bell(sh, 1.18, 0.12) * _bell(wh, 0.82, 0.12),
        "oval":               _bell(sh, 1.0, 0.12) * _bell(wh, 0.95, 0.10),
    }
    best = max(scores, key=scores.get)
    top = scores[best]
    ranked = sorted(scores.values(), reverse=True)
    # confidence = how much the winner beats the runner-up, scaled by absolute fit
    margin = (ranked[0] - ranked[1]) / (ranked[0] + 1e-6)
    confidence = round(min(1.0, top) * (0.4 + 0.6 * margin), 3)
    return best, confidence


def _bell(x: float, mu: float, sigma: float) -> float:
    import math
    return math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))


# silhouette → gentle fit guidance (never prescriptive, never about "flaws")
SILHOUETTE_FIT_RULES: dict[str, list[str]] = {
    "hourglass":          ["define waist"],
    "rectangle":          ["define waist", "add structure"],
    "triangle":           ["balance shoulders"],
    "inverted_triangle":  ["soften shoulders", "add volume below"],
    "oval":               ["elongate", "vertical lines"],
}


# ── undertone → palette ──────────────────────────────────────────────────────
# neutrals flatter across undertones, so every palette leans on them. The
# tone-specific part is a SMALL set of accents, and it shrinks when confidence
# is low (we'd rather be cautious than confidently wrong across skin tones).
_TONE_ACCENTS = {
    "warm":    ["rust", "olive", "sand", "clay", "cream"],
    "cool":    ["navy", "burgundy", "slate", "sage", "charcoal"],
    "neutral": ["navy", "olive", "sand", "sage", "stone"],
}
_UNIVERSAL_NEUTRALS = ["navy", "charcoal", "grey", "cream", "stone", "white"]
_TONE_AVOID = {
    "warm":    ["cool grey"],
    "cool":    ["orange"],
    "neutral": [],
}


@dataclass
class BodyAnalysis:
    silhouette_category: str | None
    silhouette_confidence: float
    skin_undertone: str | None
    undertone_confidence: float
    color_palette: dict = field(default_factory=dict)
    fit_rules: list[str] = field(default_factory=list)
    analysis_method: str = "full_scan"     # full_scan | quiz_fallback
    needs_confirmation: bool = True

    def as_dict(self) -> dict:
        return asdict(self)


def build_palette(undertone: str | None, confidence: float) -> dict:
    """Neutrals always; tone accents scaled by confidence. Low confidence → wide,
    mostly-neutral palette instead of a committed warm/cool one."""
    neutrals = list(_UNIVERSAL_NEUTRALS)
    if not undertone or confidence < 0.45:
        return {"best_colors": neutrals[:4], "neutrals": neutrals,
                "avoid_colors": [], "basis": "low-confidence: neutral-leaning"}
    accents = _TONE_ACCENTS.get(undertone, [])
    n_accents = 5 if confidence >= 0.7 else 3       # commit less when less sure
    best = accents[:n_accents] + neutrals[:2]
    best = list(dict.fromkeys(best))                # dedupe, preserve order
    return {
        "best_colors": best,
        "neutrals": neutrals,
        "avoid_colors": _TONE_AVOID.get(undertone, []),
        "basis": f"{undertone} undertone (confidence {confidence})",
    }


def assemble(silhouette: str | None, sil_conf: float,
             undertone: str | None, ut_conf: float,
             method: str = "full_scan") -> BodyAnalysis:
    fit_rules = SILHOUETTE_FIT_RULES.get(silhouette or "", []) if sil_conf >= 0.4 else []
    palette = build_palette(undertone, ut_conf)
    # any low-confidence signal → send the user through the quiz cross-check
    needs = sil_conf < 0.55 or ut_conf < 0.55 or method == "quiz_fallback"
    return BodyAnalysis(
        silhouette_category=silhouette if sil_conf >= 0.4 else None,
        silhouette_confidence=sil_conf,
        skin_undertone=undertone if ut_conf >= 0.45 else None,
        undertone_confidence=ut_conf,
        color_palette=palette,
        fit_rules=fit_rules,
        analysis_method=method,
        needs_confirmation=needs,
    )


# ── quiz fallback (non-camera path) ──────────────────────────────────────────
# self-report is often MORE reliable than a photo heuristic — treat it as such:
# a confident result, not a degraded one.
def from_quiz(undertone: str | None, silhouette: str | None) -> BodyAnalysis:
    return assemble(
        silhouette=silhouette, sil_conf=0.8 if silhouette else 0.0,
        undertone=undertone, ut_conf=0.8 if undertone else 0.0,
        method="quiz_fallback",
    )
