"""CV pipeline tests. Colour extraction runs for real (k-means on generated
images). CLIP/rembg are absent in this env, so the pipeline's graceful-degrade
path is what's exercised for classification. Run: python3 tests/test_cv_pipeline.py
"""
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402
from app.domains.closet.cv.color import extract_colors, _nearest_name  # noqa: E402
from app.domains.closet.cv.taxonomy import category_for, priors_for  # noqa: E402
from app.domains.closet.cv.pipeline import classify_garment  # noqa: E402
import numpy as np  # noqa: E402

_p, _f, _fails = 0, 0, []
def test(name, fn):
    global _p, _f
    try:
        fn(); _p += 1
    except Exception as e:
        _f += 1; _fails.append(f"  x {name}\n      {e}")
def ok(c, m=""): assert c, m


def _solid(rgb, size=64, alpha=255):
    a = np.zeros((size, size, 4), dtype=np.uint8)
    a[:, :, :3] = rgb; a[:, :, 3] = alpha
    return Image.fromarray(a, "RGBA")

def _to_bytes(img, fmt="PNG"):
    buf = io.BytesIO(); img.convert("RGBA").save(buf, fmt); return buf.getvalue()


def t_nearest_name():
    ok(_nearest_name(np.array([26, 26, 30])) == "black", "near-black maps to black")
    ok(_nearest_name(np.array([44, 54, 72])) == "navy", "navy maps to navy")
test("nearest-named-colour mapping is correct", t_nearest_name)

def t_solid_color():
    primary, secondary = extract_colors(_solid((44, 54, 72)))
    ok(primary == "navy", f"solid navy → navy, got {primary}")
    ok(secondary is None, "solid colour has no secondary")
test("k-means extracts a solid garment colour", t_solid_color)

def t_two_color():
    a = np.zeros((64, 64, 4), dtype=np.uint8)
    a[:, :32, :3] = (44, 54, 72); a[:, 32:, :3] = (231, 223, 206); a[:, :, 3] = 255
    primary, secondary = extract_colors(Image.fromarray(a, "RGBA"))
    ok({primary, secondary} == {"navy", "cream"}, f"expected navy+cream, got {primary}+{secondary}")
test("k-means finds primary and secondary on a two-tone garment", t_two_color)

def t_ignores_transparent_bg():
    a = np.zeros((64, 64, 4), dtype=np.uint8)
    a[24:40, 24:40, :3] = (231, 223, 206); a[24:40, 24:40, 3] = 255
    primary, _ = extract_colors(Image.fromarray(a, "RGBA"))
    ok(primary == "cream", f"opaque garment colour should win, got {primary}")
test("transparent background is ignored (cut-out aware)", t_ignores_transparent_bg)

def t_taxonomy_derivations():
    ok(category_for("blazer") == "outerwear", "blazer → outerwear")
    ok(category_for("jeans") == "bottom", "jeans → bottom")
    f, w = priors_for("coat")
    ok(f == 4 and w == 5, f"coat priors (4,5), got ({f},{w})")
test("subcategory → category + formality/warmth priors", t_taxonomy_derivations)

def t_pipeline_degrades_without_clip():
    # rembg IS present here (segments the image); CLIP is NOT (classification
    # provisional). We assert on the CLIP-degradation contract + persist shape,
    # not on a colour that depends on U^2-Net's output for a synthetic fixture.
    res = classify_garment(_to_bytes(_solid((44, 54, 72))), processed_key="cutouts/x.png")
    ok(res.category in ("top","bottom","dress","outerwear","shoes","accessory"), "valid category")
    ok(res.confidence <= 0.5, "no classifier → low confidence")
    ok("needs-review" in res.tags, "flagged for the confirm step")
    ok(res.primary_color is not None, "a colour is always produced")
    ok(res.as_dict()["s3_key_processed"] == "cutouts/x.png", "as_dict shape is persist-ready")
test("pipeline degrades gracefully when CLIP is absent (still persist-ready)", t_pipeline_degrades_without_clip)


if __name__ == "__main__":
    print("\nSylia CV pipeline\n" + "-" * 40)
    if _fails: print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
