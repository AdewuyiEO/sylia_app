"""Closet-gap analysis: how much would one product add to THIS user's closet?

Pure and deterministic, built on the daily-look scorer, so a recommendation is
held to the same standard as a daily look. A product earns a fit_score only by
creating new, well-scoring outfits with pieces the user already owns ("pairs
with 6 things you own"); one that duplicates what they have, or only works in
looks the scorer rates poorly, scores low and is gated out. The product's
commission never enters the score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..daily_look.scorer import (
    Garment, BodyProfile, IdentityProfile, Context, generate_daily_looks, look_signature,
)

# a look has to be genuinely good to count as "unlocked"
LOOK_THRESHOLD = 62.0
# unlocks at which the breadth component saturates; breadth is measured against
# what this closet makes possible (a 3-piece closet can't yield 6 looks), but
# never against fewer than BREADTH_FLOOR so one lucky pairing isn't "versatile"
UNLOCK_SATURATION = 6
BREADTH_FLOOR = 3
# representative days the product is tested against (plus the user's real today)
REFERENCE_CONTEXTS = (
    Context(temp_f=70, formality_signal=3, context_kind="work"),
    Context(temp_f=70, formality_signal=2, context_kind="weekend"),
    Context(temp_f=50, formality_signal=3, context_kind="work"),
    Context(temp_f=84, formality_signal=2, context_kind="weekend"),
)


@dataclass
class GapResult:
    fit_score: float                       # 0-1; the affiliate gate reads this
    unlocks: int                           # new distinct looks it enables
    pairs_with: list[str] = field(default_factory=list)   # closet item ids it combines with
    best_look: float = 0.0                 # best look total that includes it
    duplicate_of: str | None = None        # closet item it would duplicate
    contexts: list[str] = field(default_factory=list)


def _duplicate(product: Garment, wardrobe: list[Garment]) -> str | None:
    for g in wardrobe:
        if (g.category == product.category and g.subcategory.lower() == product.subcategory.lower()
                and g.primary_color.lower() == product.primary_color.lower()):
            return g.id
    return None


def analyze(product: Garment, wardrobe: list[Garment], body: BodyProfile,
            identity: IdentityProfile, today: Context | None = None) -> GapResult:
    contexts = ([today] if today else []) + list(REFERENCE_CONTEXTS)
    dup = _duplicate(product, wardrobe)
    # only looks that contain the product matter: let it stand alone in its
    # category so every top/bottom/shoe/outerwear candidate includes it (and the
    # search stays small enough to run per product per request)
    pool = [g for g in wardrobe if g.category != product.category] + [product]

    unlocked: set[frozenset[str]] = set()
    possible: set[frozenset[str]] = set()
    partners: set[str] = set()
    good_contexts: list[str] = []
    best = 0.0
    for ctx in contexts:
        looks = generate_daily_looks(pool, body, identity, ctx, top_n=12)
        hit = False
        for c in looks:
            ids = {g.id for g in c.pieces}
            if product.id not in ids:
                continue
            possible.add(look_signature(c.pieces) | {product.id})
            best = max(best, c.breakdown.total)
            if c.breakdown.total < LOOK_THRESHOLD:
                continue
            unlocked.add(look_signature(c.pieces) | {product.id})
            partners |= ids - {product.id}
            hit = True
        if hit:
            label = f"{ctx.context_kind}, {'cold' if ctx.temp_f < 58 else 'hot' if ctx.temp_f >= 82 else 'mild'}"
            if label not in good_contexts:
                good_contexts.append(label)

    n = len(unlocked)
    if n == 0:
        return GapResult(fit_score=0.0, unlocks=0, best_look=round(best, 1), duplicate_of=dup)

    reachable = max(BREADTH_FLOOR, min(UNLOCK_SATURATION, len(possible)))
    breadth = min(n, reachable) / reachable
    quality = (best - LOOK_THRESHOLD) / (100 - LOOK_THRESHOLD)
    versatility = min(len(good_contexts), 3) / 3
    score = 0.45 * breadth + 0.35 * quality + 0.20 * versatility
    if dup:
        score *= 0.4          # you already own this; it adds little
    return GapResult(fit_score=round(max(0.0, min(1.0, score)), 3), unlocks=n,
                     pairs_with=sorted(partners), best_look=round(best, 1),
                     duplicate_of=dup, contexts=good_contexts)


_COPY = {
    "en": {"none": "Doesn't pair well with your closet yet.",
           "main": "Pairs with {pieces} piece{ps} you own — {looks} new look{ls}",
           "work": "work", "weekend": "weekends", "cold": "cold days", "hot": "hot days", "and": "and", "for": "for"},
    "fr": {"none": "Ne s'accorde pas encore avec votre dressing.",
           "main": "S'accorde avec {pieces} pièce{ps} de votre dressing — {looks} nouvelle{ls} tenue{ls}",
           "work": "le travail", "weekend": "le week-end", "cold": "les jours froids", "hot": "les jours chauds",
           "and": "et", "for": "pour"},
    "es": {"none": "Aún no combina bien con tu armario.",
           "main": "Combina con {pieces} prenda{ps} que tienes — {looks} look{ls} nuevo{ls}",
           "work": "el trabajo", "weekend": "el fin de semana", "cold": "días fríos", "hot": "días de calor",
           "and": "y", "for": "para"},
}


def rationale(result: GapResult, locale: str | None = None) -> str:
    """Template copy grounded in the analysis numbers (no LLM needed)."""
    cp = _COPY.get((locale or "en").split("-")[0].lower(), _COPY["en"])
    if result.unlocks == 0:
        return cp["none"]
    pieces, looks = len(result.pairs_with), result.unlocks
    s = cp["main"].format(pieces=pieces, ps="s" if pieces != 1 else "", looks=looks, ls="s" if looks != 1 else "")
    kinds = []
    for label in result.contexts:                      # e.g. "work, mild"
        kind, temp = [x.strip() for x in label.split(",")]
        for k in (kind, temp):
            if k in ("work", "weekend", "cold", "hot") and cp[k] not in kinds:
                kinds.append(cp[k])
    if not kinds:
        return s + "."
    when = kinds[0] if len(kinds) == 1 else f"{', '.join(kinds[:-1])} {cp['and']} {kinds[-1]}"
    return f"{s} {cp['for']} {when}."
