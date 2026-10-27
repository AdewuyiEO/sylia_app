"""Fit engine: body measurements vs a garment's size chart → per-zone ease, a
fit label per zone, and a suggested size. Pure functions, no I/O.

Ease = garment circumference - body circumference (cm). It is what makes size M
and size L look different on the same person, so the renderer uses the same
numbers. Sylia suggests a size and explains why; the user picks.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict

ZONES_BY_CATEGORY = {
    "top": ("bust", "waist"),
    "outerwear": ("bust", "waist"),
    "dress": ("bust", "waist", "hips"),
    "bottom": ("waist", "hips"),
}
RENDERABLE = set(ZONES_BY_CATEGORY)

# ease the garment is cut for, by intended fit (cm over the body)
TARGET_EASE = {"slim": 3.0, "regular": 7.0, "oversized": 16.0}

# Standard chart, used when a brand sends no size chart (labelled as an estimate).
# Body measurements each size is cut for, in cm.
_ALPHA = {
    "XXS": (78, 60, 86), "XS": (82, 64, 90), "S": (88, 70, 96), "M": (94, 76, 102),
    "L": (100, 82, 108), "XL": (106, 90, 114), "XXL": (114, 98, 122), "3XL": (122, 106, 130),
}
_UK = {str(n): (78 + (n - 4) * 2.5, 60 + (n - 4) * 2.5, 86 + (n - 4) * 2.5) for n in range(4, 28, 2)}
_EU = {str(n): v for n, v in zip(range(32, 56, 2), _UK.values())}
_LENGTH = {"top": 66, "outerwear": 80, "dress": 105, "bottom": 100}   # nominal, cm


@dataclass
class Body:
    height_cm: float
    bust_cm: float
    waist_cm: float
    hips_cm: float
    inseam_cm: float | None = None

    def zone(self, z: str) -> float:
        return {"bust": self.bust_cm, "waist": self.waist_cm, "hips": self.hips_cm}[z]


@dataclass
class ZoneFit:
    zone: str
    ease_cm: float
    label: str          # too_tight|fitted|comfortable|relaxed|oversized


@dataclass
class SizeFit:
    size: str
    zones: list[ZoneFit]
    length_cm: float
    score: float
    tight: bool
    garment: dict = field(default_factory=dict)   # cm the renderer draws: bust/waist/hips/length

    def as_dict(self) -> dict:
        return asdict(self)


def label_for(ease: float) -> str:
    if ease < -2:
        return "too_tight"
    if ease < 2:
        return "fitted"
    if ease < 8:
        return "comfortable"
    if ease < 16:
        return "relaxed"
    return "oversized"


def standard_chart(sizes: list[str], category: str, fit: str = "regular") -> dict:
    """Garment measurements for the given labels from the standard tables: the body
    a size is cut for, plus the ease of the garment's intended fit."""
    ease = TARGET_EASE.get(fit, TARGET_EASE["regular"])
    out = {}
    for s in sizes:
        key = s.strip().upper()
        body = _ALPHA.get(key) or _UK.get(key) or _EU.get(key)
        if body is None and key.startswith(("UK", "EU")):
            body = (_UK if key.startswith("UK") else _EU).get(key[2:].strip())
        if body is None:
            continue
        out[s] = {"bust": body[0] + ease, "waist": body[1] + ease, "hips": body[2] + ease,
                  "length": _LENGTH.get(category, 70)}
    return out


def estimate_own_garment(body: Body, category: str, fit: str | None) -> dict:
    """A closet piece with no measurements: assume it was bought to fit, so model
    it as the owner's body plus the ease of its fit."""
    ease = TARGET_EASE.get(fit or "regular", TARGET_EASE["regular"])
    return {"bust": body.bust_cm + ease, "waist": body.waist_cm + ease, "hips": body.hips_cm + ease,
            "length": _LENGTH.get(category, 70)}


def fit_size(body: Body, size: str, garment: dict, category: str, fit: str = "regular") -> SizeFit:
    target = TARGET_EASE.get(fit, TARGET_EASE["regular"])
    zones, score, tight = [], 0.0, False
    for z in ZONES_BY_CATEGORY.get(category, ("bust",)):
        g = garment.get(z)
        if g is None:
            continue
        e = round(float(g) - body.zone(z), 1)
        lab = label_for(e)
        tight = tight or lab == "too_tight"
        score += abs(e - target) + (40 if lab == "too_tight" else 0)
        zones.append(ZoneFit(z, e, lab))
    return SizeFit(size=size, zones=zones, length_cm=float(garment.get("length") or _LENGTH.get(category, 70)),
                   score=round(score, 1), tight=tight, garment={k: float(v) for k, v in garment.items() if v is not None})


def fit_table(body: Body, chart: dict, category: str, fit: str = "regular") -> list[SizeFit]:
    return [fit_size(body, s, g, category, fit) for s, g in chart.items()]


def recommend(table: list[SizeFit]) -> SizeFit | None:
    return min(table, key=lambda f: f.score) if table else None


_WORDS = {"too_tight": "too tight", "fitted": "close to the body", "comfortable": "comfortable",
          "relaxed": "relaxed", "oversized": "roomy"}


def explain(f: SizeFit, category: str, body: Body) -> str:
    """Plain-words read-out for one size. Explains; never decides for the user."""
    parts = []
    for z in f.zones:
        cm = abs(z.ease_cm)
        if z.label == "too_tight":
            parts.append(f"{z.zone} {cm:.0f} cm smaller than you")
        else:
            parts.append(f"{z.zone} {_WORDS[z.label]} ({cm:.0f} cm room)")
    length = _length_note(f.length_cm, category, body)
    return f"Size {f.size}: " + ", ".join(parts) + (f"; {length}" if length else "") + "."


def _length_note(length_cm: float, category: str, body: Body) -> str:
    h = body.height_cm
    if category == "dress":
        # length measured from the shoulder; knee sits ~0.47h below the shoulder line
        drop = length_cm / h
        return ("mini length" if drop < 0.40 else "falls around the knee" if drop < 0.52
                else "midi length" if drop < 0.66 else "maxi length")
    if category == "bottom":
        leg = body.inseam_cm or h * 0.45
        rise = 25
        return "cropped above the ankle" if length_cm - rise < leg - 4 else "full length" if length_cm - rise < leg + 3 else "pools at the ankle"
    if category in ("top", "outerwear"):
        return "cropped" if length_cm / h < 0.34 else "hip length" if length_cm / h < 0.46 else "long line"
    return ""
