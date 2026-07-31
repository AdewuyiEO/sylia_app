"""
Sylia scorer tests. Stdlib-only harness so it runs with `python3 tests/test_scorer.py`
before any dependency is installed — the scorer is the one piece we never ship
un-verified.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.domains.daily_look.scorer import (  # noqa: E402
    Garment, BodyProfile, ColorPalette, IdentityProfile, Context, WornRecord,
    generate_daily_looks, score_context, score_identity, hard_excluded,
    temp_to_warmth_band, build_candidates,
)
import random  # noqa: E402

_p, _f, _fails = 0, 0, []
def test(name, fn):
    global _p, _f
    try:
        fn(); _p += 1
    except Exception as e:
        _f += 1; _fails.append(f"  x {name}\n      {e}")
def eq(a, b, m=""): assert a == b, f"{m} expected {b}, got {a}"
def ok(c, m=""): assert c, m


# ── fixtures ─────────────────────────────────────────────────────────────────
def demo_wardrobe():
    return [
        Garment("t1", "top", "blouse", "cream", formality_score=3, warmth_score=2,
                fit="regular", tags=["3/4-sleeve", "soft"]),
        Garment("t2", "top", "tank", "white", formality_score=2, warmth_score=1,
                fit="slim", tags=["sleeveless"]),
        Garment("t3", "top", "blazer", "navy", formality_score=4, warmth_score=3,
                fit="slim", tags=["structured", "tailored", "blazer"]),
        Garment("b1", "bottom", "trousers", "navy", formality_score=4, warmth_score=2,
                fit="slim", tags=["tailored-trouser"]),
        Garment("b2", "bottom", "jeans", "blue", formality_score=2, warmth_score=2,
                fit="regular", tags=[]),
        Garment("s1", "shoes", "loafer", "brown", formality_score=3, warmth_score=2),
        Garment("s2", "shoes", "heel", "black", formality_score=4, warmth_score=2,
                tags=["heels"]),
        Garment("o1", "outerwear", "coat", "camel", formality_score=3, warmth_score=5),
    ]

def demo_body():
    return BodyProfile(
        silhouette_category="hourglass", skin_undertone="cool",
        palette=ColorPalette(best_colors=["navy", "cream"], avoid_colors=["orange"],
                             neutrals=["navy", "cream", "black"]),
        fit_rules=["define waist"])

def demo_identity(**kw):
    base = dict(aspirations=["authoritative"], insecurities=["arms"],
                activity_level="desk", risk_tolerance=0.3, confidence_baseline=0.5)
    base.update(kw)
    return IdentityProfile(**base)


# ── tests ────────────────────────────────────────────────────────────────────
def t_warmth_band():
    ok(temp_to_warmth_band(90) == {1, 2}, "hot band")
    ok(5 in temp_to_warmth_band(20), "cold band includes heaviest")
test("temperature maps to a warmth band", t_warmth_band)

def t_exclusions():
    ctx = Context(temp_f=90, formality_signal=3)      # hot day
    coat = Garment("c", "outerwear", "coat", "camel", formality_score=3, warmth_score=5)
    ok(hard_excluded(coat, ctx, demo_identity()), "coat excluded at 90F")
    tee = Garment("t", "top", "tee", "white", formality_score=2, warmth_score=1)
    ok(not hard_excluded(tee, ctx, demo_identity()), "tee fine at 90F")
test("hard exclusions drop weather-wrong pieces", t_exclusions)

def t_lifestyle_exclusion():
    ctx = Context(temp_f=68, formality_signal=4)
    heel = Garment("h", "shoes", "heel", "black", formality_score=4, warmth_score=2, tags=["heels"])
    ok(hard_excluded(heel, ctx, demo_identity(activity_level="on_feet")), "heels excluded on_feet")
    ok(not hard_excluded(heel, ctx, demo_identity(activity_level="desk")), "heels fine desk")
test("lifestyle prunes the candidate set (on-feet drops heels)", t_lifestyle_exclusion)

def t_context_responds_to_temp():
    warm_outfit = [Garment("a", "top", "tank", "white", formality_score=3, warmth_score=1),
                   Garment("b", "bottom", "shorts", "beige", formality_score=3, warmth_score=1),
                   Garment("c", "shoes", "sandal", "tan", formality_score=3, warmth_score=1)]
    hot = score_context(warm_outfit, Context(temp_f=88, formality_signal=3))
    cold = score_context(warm_outfit, Context(temp_f=30, formality_signal=3))
    ok(hot > cold, f"light outfit should score higher when hot ({hot} vs {cold})")
test("context subscore rewards weather-appropriate warmth", t_context_responds_to_temp)

def t_insecurity_penalty():
    ctx = Context(temp_f=68, formality_signal=3)
    ident = demo_identity(insecurities=["arms"])
    sleeveless = [Garment("x", "top", "tank", "cream", formality_score=3, warmth_score=2, tags=["sleeveless"]),
                  Garment("y", "bottom", "trousers", "navy", formality_score=3, warmth_score=2)]
    covered = [Garment("z", "top", "blouse", "cream", formality_score=3, warmth_score=2, tags=["3/4-sleeve"]),
               Garment("y", "bottom", "trousers", "navy", formality_score=3, warmth_score=2)]
    rng = random.Random(0)
    s_bad = score_identity(sleeveless, ident, ctx, [], rng)
    s_good = score_identity(covered, ident, ctx, [], rng)
    ok(s_good > s_bad, f"covered arms should beat sleeveless ({s_good} vs {s_bad})")
test("insecurity applies a targeted penalty to the named area", t_insecurity_penalty)

def t_aspiration_context_scoped():
    ident = demo_identity(aspirations=["authoritative"], insecurities=[])
    blazer = [Garment("t3", "top", "blazer", "navy", formality_score=4, warmth_score=3,
                      tags=["structured", "tailored", "blazer"]),
              Garment("b1", "bottom", "trousers", "navy", formality_score=4, warmth_score=2)]
    rng = random.Random(0)
    at_work = score_identity(blazer, ident, Context(temp_f=68, formality_signal=4, context_kind="work"), [], rng)
    at_wknd = score_identity(blazer, ident, Context(temp_f=68, formality_signal=4, context_kind="weekend"), [], rng)
    ok(at_work > at_wknd, f"authoritative boost applies only in work context ({at_work} vs {at_wknd})")
test("aspiration boost is context-scoped (work, not weekend)", t_aspiration_context_scoped)

def t_novelty_decay():
    ident = demo_identity(insecurities=[])
    ctx = Context(temp_f=68, formality_signal=3)
    outfit = [Garment("t1", "top", "blouse", "cream", formality_score=3, warmth_score=2),
              Garment("b1", "bottom", "trousers", "navy", formality_score=3, warmth_score=2)]
    rng = random.Random(0)
    fresh = score_identity(outfit, ident, ctx, [], rng)
    worn_yday = score_identity(outfit, ident, ctx,
                               [WornRecord(frozenset({"t1", "b1"}), days_ago=1)], rng)
    ok(worn_yday < fresh, f"recently-worn outfit should be penalised ({worn_yday} vs {fresh})")
test("novelty-decay penalises recently-worn items", t_novelty_decay)

def t_generate_ranks_and_dedupes():
    looks = generate_daily_looks(demo_wardrobe(), demo_body(), demo_identity(),
                                 Context(temp_f=66, formality_signal=4, context_kind="work"),
                                 top_n=3, seed=1)
    ok(len(looks) > 0, "should return at least one look")
    ok(len(looks) <= 3, "respects top_n")
    totals = [c.breakdown.total for c in looks]
    ok(totals == sorted(totals, reverse=True), f"looks must be sorted by total {totals}")
    sigs = [frozenset(g.id for g in c.pieces if g.category in ("top", "bottom", "dress")) for c in looks]
    ok(len(sigs) == len(set(sigs)), "no duplicate top/bottom signatures")
    for c in looks:
        b = c.breakdown
        ok(0 <= b.total <= 100, "total in range")
        ok(all(0 <= s <= 100 for s in (b.context, b.color, b.body, b.identity)), "subscores in range")
test("generate_daily_looks ranks, bounds, and de-dupes", t_generate_ranks_and_dedupes)

def t_deterministic():
    args = (demo_wardrobe(), demo_body(), demo_identity(),
            Context(temp_f=66, formality_signal=4))
    a = generate_daily_looks(*args, seed=7)
    b = generate_daily_looks(*args, seed=7)
    ok([c.breakdown.total for c in a] == [c.breakdown.total for c in b],
       "same seed → same result")
test("scoring is deterministic given a seed", t_deterministic)

def t_authoritative_pick_makes_sense():
    # the Maya journey: cool-toned, authoritative, arm-conscious, client meeting
    looks = generate_daily_looks(demo_wardrobe(), demo_body(),
                                 demo_identity(aspirations=["authoritative"], insecurities=["arms"]),
                                 Context(temp_f=66, formality_signal=4, context_kind="work"),
                                 top_n=1, seed=1)
    top = looks[0]
    subs = {g.subcategory for g in top.pieces}
    ok("tank" not in subs, "arm-conscious winner should not be sleeveless")
    ok(top.breakdown.total > 60, f"a good match should clear 60 ({top.breakdown.total})")
test("winning look reflects identity (no sleeveless for arm-conscious user)", t_authoritative_pick_makes_sense)


if __name__ == "__main__":
    print("\nSylia scorer\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
