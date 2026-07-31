"""
Sylia — Daily Look scorer.

A faithful Python port of the tested outfit engine, restructured to the
architecture spec §4.2 (four weighted subscores) and §4.3 (prune-then-score).

Design contract (do not break these — the whole transparency layer depends on it):
  * Deterministic given (wardrobe, body, identity, context, recent, seed).
  * Pure: no I/O, no DB, no clock. `now`/`seed` are injected.
  * The scorer RANKS and returns score_breakdowns. It never calls an LLM.
    Claude only later narrates the winning breakdown (service layer), so the
    explanation always describes real subscores.

Everything here is stdlib-only so it can be unit-tested without installing a thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import random

# ── weights (spec §4.2) ────────────────────────────────────────────────────
W_CONTEXT = 0.30   # weather/occasion — highest: the most visible failure mode
W_COLOR = 0.25
W_BODY = 0.25
W_IDENTITY = 0.20

ROLES = ("top", "bottom", "dress", "outerwear", "shoes", "accessory")

# default neutrals if a body profile doesn't specify its own
DEFAULT_NEUTRALS = {"black", "white", "navy", "grey", "gray", "beige", "cream",
                    "charcoal", "ecru", "bone", "tan", "brown", "stone", "sand"}


# ── input types ─────────────────────────────────────────────────────────────
@dataclass
class Garment:
    id: str
    category: str                    # one of ROLES
    subcategory: str                 # "blazer", "sneaker", ...
    primary_color: str
    formality_score: int             # 1–5
    warmth_score: int                # 1–5
    fit: str = "regular"             # slim | regular | oversized
    pattern: str = "solid"
    secondary_color: Optional[str] = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ColorPalette:
    best_colors: list[str] = field(default_factory=list)
    avoid_colors: list[str] = field(default_factory=list)
    neutrals: list[str] = field(default_factory=list)


@dataclass
class BodyProfile:
    silhouette_category: str = "rectangle"
    skin_undertone: str = "neutral"
    palette: ColorPalette = field(default_factory=ColorPalette)
    fit_rules: list[str] = field(default_factory=list)   # e.g. ["define waist"]


@dataclass
class IdentityProfile:
    aspirations: list[str] = field(default_factory=list)       # ["authoritative"]
    insecurities: list[str] = field(default_factory=list)      # ["arms"]
    activity_level: str = "desk"                               # desk | on_feet
    risk_tolerance: float = 0.3                                # 0–1
    confidence_baseline: float = 0.5                           # 0–1


@dataclass
class Context:
    temp_f: float
    formality_signal: int             # 1–5 (from the single calendar category)
    precipitation: bool = False
    context_kind: str = "work"        # work | weekend | ...


@dataclass
class WornRecord:
    item_ids: frozenset[str]
    days_ago: int


@dataclass
class ScoreBreakdown:
    context: float
    color: float
    body: float
    identity: float
    total: float


@dataclass
class Candidate:
    pieces: list[Garment]
    breakdown: ScoreBreakdown


# ── knowledge tables (MVP heuristics — calibrate once real data exists) ──────
ASPIRATION_RULES = {
    "authoritative": dict(tags={"structured", "tailored", "blazer"},
                          colors={"navy", "black", "charcoal"}, context="work"),
    "approachable":  dict(tags={"soft", "knit", "relaxed"},
                          colors={"cream", "blue", "sage"}, context=None),
    "creative":      dict(tags={"print", "textured", "statement"},
                          colors={"rust", "olive", "clay"}, context=None),
    "polished":      dict(tags={"tailored", "crisp", "structured"},
                          colors=set(), context=None),
}

INSECURITY_RULES = {
    "arms":       dict(penalize={"sleeveless", "tank", "short-sleeve"},
                       boost={"3/4-sleeve", "long-sleeve", "jacket", "blazer"}),
    "midsection": dict(penalize={"cropped", "clingy"},
                       boost={"structured", "flowy", "wrap"}),
    "legs":       dict(penalize={"mini", "short"},
                       boost={"midi", "wide-leg", "tailored-trouser"}),
}

# lifestyle exclusions (§4.1 — prune the candidate set, don't just down-rank)
LIFESTYLE_EXCLUDE = {
    "on_feet": {"heel", "heels", "stiletto", "pump"},
}


# ── temperature → allowed garment warmth band ────────────────────────────────
def temp_to_warmth_band(temp_f: float) -> set[int]:
    if temp_f >= 82:
        return {1, 2}
    if temp_f >= 68:
        return {1, 2, 3}
    if temp_f >= 52:
        return {2, 3, 4}
    if temp_f >= 38:
        return {3, 4, 5}
    return {4, 5}


def needs_outerwear(ctx: Context) -> bool:
    return ctx.temp_f < 58 or ctx.precipitation


# ── hard exclusions (spec §4.3 step 2) ───────────────────────────────────────
def hard_excluded(g: Garment, ctx: Context, identity: IdentityProfile) -> bool:
    band = temp_to_warmth_band(ctx.temp_f)
    # warmth wildly off (2+ steps outside the band) → exclude, not down-rank
    if min(abs(g.warmth_score - w) for w in band) >= 2:
        return True
    # formality mismatch beyond threshold
    if abs(g.formality_score - ctx.formality_signal) > 2:
        return True
    # lifestyle exclusions
    excl = LIFESTYLE_EXCLUDE.get(identity.activity_level, set())
    hay = {g.subcategory.lower(), *(t.lower() for t in g.tags)}
    if hay & excl:
        return True
    return False


# ── candidate generation (spec §4.3 step 1) ──────────────────────────────────
def build_candidates(wardrobe: list[Garment], ctx: Context,
                     identity: IdentityProfile, cap: int = 400) -> list[list[Garment]]:
    pool = [g for g in wardrobe if not hard_excluded(g, ctx, identity)]
    by = {r: [g for g in pool if g.category == r] for r in ROLES}

    outfits: list[list[Garment]] = []
    add_outer = needs_outerwear(ctx)

    def finish(base: list[Garment]) -> list[Garment]:
        outfit = list(base)
        if by["shoes"]:
            outfit.append(by["shoes"][0])          # cheap default; refined by scoring across shoe options below
        if add_outer and by["outerwear"]:
            outfit.append(by["outerwear"][0])
        return outfit

    # top + bottom combinations, each shoe option considered
    for top in by["top"]:
        for bottom in by["bottom"]:
            for shoe in (by["shoes"] or [None]):
                outfit = [top, bottom]
                if shoe:
                    outfit.append(shoe)
                if add_outer and by["outerwear"]:
                    outfit.append(by["outerwear"][0])
                outfits.append(outfit)
                if len(outfits) >= cap:
                    return outfits
    # dresses
    for dress in by["dress"]:
        for shoe in (by["shoes"] or [None]):
            outfit = [dress]
            if shoe:
                outfit.append(shoe)
            if add_outer and by["outerwear"]:
                outfit.append(by["outerwear"][0])
            outfits.append(outfit)
            if len(outfits) >= cap:
                return outfits
    return outfits


# ── subscores (0–100) ────────────────────────────────────────────────────────
def _is_neutral(color: str, body: BodyProfile) -> bool:
    c = color.lower()
    return c in DEFAULT_NEUTRALS or c in {n.lower() for n in body.palette.neutrals}


def score_context(outfit: list[Garment], ctx: Context) -> float:
    band = temp_to_warmth_band(ctx.temp_f)
    # warmth fit: average distance of each piece from the band
    warmth_pen = sum(min(abs(g.warmth_score - w) for w in band) for g in outfit) / len(outfit)
    warmth_fit = max(0.0, 1 - warmth_pen / 2)
    # formality fit: outfit mean vs signal
    avg_form = sum(g.formality_score for g in outfit) / len(outfit)
    form_fit = max(0.0, 1 - abs(avg_form - ctx.formality_signal) / 4)
    # rain: reward having outerwear when wet
    rain_fit = 1.0
    if ctx.precipitation:
        rain_fit = 1.0 if any(g.category == "outerwear" for g in outfit) else 0.6
    return 100 * (0.5 * warmth_fit + 0.35 * form_fit + 0.15 * rain_fit)


def score_color(outfit: list[Garment], body: BodyProfile) -> float:
    best = {c.lower() for c in body.palette.best_colors}
    avoid = {c.lower() for c in body.palette.avoid_colors}
    colors = [g.primary_color.lower() for g in outfit]

    base = 0.0
    for c in colors:
        if c in avoid:
            base -= 0.5
        elif c in best:
            base += 0.4
        elif _is_neutral(c, body):
            base += 0.15
    base = base / len(colors)                     # normalise per piece

    # inter-garment harmony: neutrals + at most one accent reads intentional
    accents = [c for c in colors if not _is_neutral(c, body)]
    uniq = set(colors)
    if len(uniq) == 1:
        harmony = 1.0                              # monochrome
    elif len(accents) == 0:
        harmony = 0.9                              # all neutral
    elif len(accents) == 1:
        harmony = 0.85                             # neutrals + one accent = ideal
    elif len(set(accents)) == 1:
        harmony = 0.6
    else:
        harmony = 0.3

    return max(0.0, min(100.0, 100 * (0.55 * harmony + 0.45 * (0.5 + base))))


def score_body(outfit: list[Garment], body: BodyProfile) -> float:
    rules = {r.lower() for r in body.fit_rules}
    score = 0.6                                    # neutral baseline
    fits = [g.fit for g in outfit if g.category in ("top", "bottom", "dress")]

    if "define waist" in rules or "define the waist" in rules:
        defines = any(g.fit == "slim" for g in outfit if g.category in ("top", "dress")) \
            or any("belt" in g.subcategory.lower() or "belt" in " ".join(g.tags).lower()
                   for g in outfit if g.category == "accessory")
        score += 0.25 if defines else -0.15
        if fits and all(f == "oversized" for f in fits):
            score -= 0.2                            # all-oversized hides the waist
    if "elongate" in rules:
        if any(g.fit in ("slim", "regular") for g in outfit if g.category == "bottom"):
            score += 0.15
    if "balance shoulders" in rules:
        if any(g.category == "bottom" and g.fit != "slim" for g in outfit):
            score += 0.1

    return max(0.0, min(100.0, 100 * score))


def score_identity(outfit: list[Garment], identity: IdentityProfile, ctx: Context,
                   recent: list[WornRecord], now_seed: random.Random) -> float:
    score = 0.55
    tags_all = {t.lower() for g in outfit for t in g.tags}
    subs = {g.subcategory.lower() for g in outfit}
    colors = {g.primary_color.lower() for g in outfit}
    present = tags_all | subs

    # aspirations — context-scoped boosts
    for asp in identity.aspirations:
        rule = ASPIRATION_RULES.get(asp.lower())
        if not rule:
            continue
        if rule["context"] and rule["context"] != ctx.context_kind:
            continue
        if present & rule["tags"]:
            score += 0.12
        if colors & rule["colors"]:
            score += 0.06

    # insecurities — targeted penalty + compensator boost, scoped to the named area
    for area in identity.insecurities:
        rule = INSECURITY_RULES.get(area.lower())
        if not rule:
            continue
        if present & rule["penalize"]:
            score -= 0.25
        if present & rule["boost"]:
            score += 0.12

    # novelty-decay: penalise items worn inside a rolling window
    item_ids = {g.id for g in outfit}
    for rec in recent:
        if rec.days_ago <= 7 and (item_ids & rec.item_ids):
            overlap = len(item_ids & rec.item_ids) / len(item_ids)
            score -= 0.3 * overlap * (1 - rec.days_ago / 7)

    # risk tolerance gates a small novelty reward for un-worn stretch pieces
    if identity.risk_tolerance >= 0.6:
        worn_ids = {i for r in recent for i in r.item_ids}
        if not (item_ids & worn_ids):
            score += 0.05 * identity.risk_tolerance

    return max(0.0, min(100.0, 100 * score))


# ── scoring + ranking (spec §4.3 step 3) ─────────────────────────────────────
def score_outfit(outfit: list[Garment], body: BodyProfile, identity: IdentityProfile,
                 ctx: Context, recent: list[WornRecord], rng: random.Random) -> ScoreBreakdown:
    ctx_s = score_context(outfit, ctx)
    col_s = score_color(outfit, body)
    bod_s = score_body(outfit, body)
    idn_s = score_identity(outfit, identity, ctx, recent, rng)
    total = W_CONTEXT * ctx_s + W_COLOR * col_s + W_BODY * bod_s + W_IDENTITY * idn_s
    return ScoreBreakdown(round(ctx_s, 1), round(col_s, 1), round(bod_s, 1),
                          round(idn_s, 1), round(total, 1))


def generate_daily_looks(
    wardrobe: list[Garment],
    body: BodyProfile,
    identity: IdentityProfile,
    ctx: Context,
    recent: Optional[list[WornRecord]] = None,
    *,
    top_n: int = 3,
    seed: int = 0,
) -> list[Candidate]:
    """Spec §4.3: prune → score every survivor → return the top N distinct outfits.

    The winning candidate's `breakdown` is what the service layer hands to Claude
    for a one-sentence explanation. Claude never sees the raw wardrobe.
    """
    recent = recent or []
    rng = random.Random(seed)
    candidates = build_candidates(wardrobe, ctx, identity)

    scored: list[Candidate] = []
    for outfit in candidates:
        bd = score_outfit(outfit, body, identity, ctx, recent, rng)
        scored.append(Candidate(pieces=outfit, breakdown=bd))

    scored.sort(key=lambda c: c.breakdown.total, reverse=True)

    # de-duplicate by the top+bottom (or dress) signature so results are varied
    seen: set[frozenset[str]] = set()
    out: list[Candidate] = []
    for c in scored:
        sig = frozenset(g.id for g in c.pieces
                        if g.category in ("top", "bottom", "dress"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(c)
        if len(out) >= top_n:
            break
    return out
