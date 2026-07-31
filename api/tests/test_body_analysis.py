"""Body-analysis tests. The derivation logic (silhouette, palette, confidence
gating) runs for real and is the fairness-critical surface, so it's tested
thoroughly. MediaPipe extraction is exercised for its degrade path (a synthetic
image has no detectable body/face → None → quiz route). Run:
python3 tests/test_body_analysis.py
"""
import sys, os, io, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.domains.vision.analysis.derive import (  # noqa: E402
    Ratios, classify_silhouette, build_palette, assemble, from_quiz,
)
from app.domains.vision.analysis.pipeline import analyze_body_images  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

_p, _f, _fails = 0, 0, []
def test(name, fn):
    global _p, _f
    try:
        fn(); _p += 1
    except Exception as e:
        _f += 1; _fails.append(f"  x {name}\n      {e}")
def ok(c, m=""): assert c, m


def t_silhouette_hourglass():
    sil, conf = classify_silhouette(Ratios(shoulder_hip=1.0, waist_hip=0.72, torso_leg=0.8))
    ok(sil == "hourglass", f"balanced shoulders/hips + defined waist → hourglass, got {sil}")
    ok(0 <= conf <= 1, "confidence in range")
test("silhouette: hourglass ratios classify as hourglass", t_silhouette_hourglass)


def t_silhouette_triangle():
    sil, _ = classify_silhouette(Ratios(shoulder_hip=0.82, waist_hip=0.80, torso_leg=0.8))
    ok(sil == "triangle", f"narrow shoulders vs hips → triangle, got {sil}")
test("silhouette: narrow shoulders classify as triangle", t_silhouette_triangle)


def t_boundary_lowers_confidence():
    clear = classify_silhouette(Ratios(1.0, 0.72, 0.8))[1]           # squarely hourglass
    ambiguous = classify_silhouette(Ratios(0.93, 0.80, 0.8))[1]      # between categories
    ok(ambiguous < clear, f"ambiguous ratios → lower confidence ({ambiguous} vs {clear})")
test("ambiguous ratios lower the silhouette confidence", t_boundary_lowers_confidence)


def t_palette_neutral_when_uncertain():
    # low undertone confidence must NOT commit to warm/cool — widen to neutrals
    pal = build_palette("warm", confidence=0.2)
    ok("low-confidence" in pal["basis"], "low confidence → neutral-leaning palette")
    ok(all(c in pal["neutrals"] for c in pal["best_colors"]), "best colours are neutrals when unsure")
test("low undertone confidence yields a cautious neutral palette (fairness)", t_palette_neutral_when_uncertain)


def t_palette_commits_when_confident():
    warm = build_palette("warm", confidence=0.75)
    cool = build_palette("cool", confidence=0.75)
    ok("rust" in warm["best_colors"], "confident warm palette includes warm accents")
    ok("navy" in cool["best_colors"], "confident cool palette includes cool accents")
    ok(warm["best_colors"] != cool["best_colors"], "warm and cool differ when confident")
test("confident undertone commits to a tone-appropriate palette", t_palette_commits_when_confident)


def t_low_confidence_routes_to_quiz():
    a = assemble(silhouette="rectangle", sil_conf=0.3, undertone="warm", ut_conf=0.3)
    ok(a.needs_confirmation, "any low-confidence signal flags confirmation")
    ok(a.silhouette_category is None, "very low silhouette confidence → not asserted")
test("low-confidence scan routes the user to the quiz cross-check", t_low_confidence_routes_to_quiz)


def t_quiz_is_confident():
    a = from_quiz(undertone="cool", silhouette="hourglass")
    ok(a.analysis_method == "quiz_fallback")
    ok(a.skin_undertone == "cool", "quiz undertone is trusted")
    ok(a.silhouette_category == "hourglass", "quiz silhouette is trusted")
    ok("navy" in a.color_palette["best_colors"], "quiz drives a committed palette")
test("quiz fallback is treated as a confident source, not degraded", t_quiz_is_confident)


def t_fit_rules_from_silhouette():
    a = from_quiz(undertone="neutral", silhouette="oval")
    ok("elongate" in a.fit_rules, f"oval → elongate rule, got {a.fit_rules}")
test("silhouette maps to gentle fit rules (never about 'flaws')", t_fit_rules_from_silhouette)


def t_pipeline_degrades_on_no_body():
    # a plain gradient has no detectable body/face → both signals None →
    # neutral, low-confidence result that routes to the quiz (never a guess)
    arr = np.tile(np.linspace(60, 200, 200, dtype=np.uint8)[:, None, None], (1, 200, 3))
    buf = io.BytesIO(); Image.fromarray(arr, "RGB").save(buf, "PNG")
    a = analyze_body_images(buf.getvalue())
    ok(a.needs_confirmation, "no detectable body → needs confirmation")
    ok(a.silhouette_category is None, "no confident silhouette from a non-body image")
    ok("low-confidence" in a.color_palette["basis"], "falls back to neutral palette")
test("pipeline degrades safely when no body/face is detected", t_pipeline_degrades_on_no_body)


if __name__ == "__main__":
    print("\nSylia body analysis\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
