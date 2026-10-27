"""Try-on: fit engine maths, the 2D renderer, the fitting-room profile (consent,
validation, retention purge, wipe), Pro gating, renders for closet pieces and
Discover products in different sizes, and account deletion.
Run: python tests/test_tryon.py
"""
import io, os, sys, tempfile
from datetime import datetime, timedelta, timezone
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
os.environ["LOCAL_STORAGE_DIR"] = os.path.join(_dir, "storage")
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine, SessionLocal  # noqa: E402
from app.models import Base, User, Brand, Product, TryOnProfile, TryOnRender  # noqa: E402
from app.core.storage import storage  # noqa: E402
from app.domains.tryon import fit as F, render as R, service as S  # noqa: E402
from support import Harness, ok, signup, upload, add_item  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
h = Harness("Sylia try-on")
BODY = F.Body(168, 88, 70, 96)
LM = {"head": [0.5, 0.06], "l_shoulder": [0.40, 0.22], "r_shoulder": [0.60, 0.22],
      "l_hip": [0.42, 0.50], "r_hip": [0.58, 0.50], "feet": [0.5, 0.95]}


def person_jpeg() -> bytes:
    """A light backdrop with a dark standing figure (head, torso, legs)."""
    a = np.full((900, 600, 3), 225, np.uint8)
    a[54:150, 270:330] = (120, 90, 70)          # head
    a[150:450, 230:370] = (60, 60, 70)          # torso
    a[450:855, 245:295] = (60, 60, 70)          # legs
    a[450:855, 305:355] = (60, 60, 70)
    buf = io.BytesIO(); Image.fromarray(a).save(buf, format="JPEG"); return buf.getvalue()


def garment_png(rgb=(200, 40, 40)) -> bytes:
    """A T-shape on white, like a flat-lay product shot."""
    a = np.full((400, 400, 3), 255, np.uint8)
    a[40:120, 40:360] = rgb                     # shoulders + sleeves
    a[40:380, 120:280] = rgb                    # body
    buf = io.BytesIO(); Image.fromarray(a).save(buf, format="PNG"); return buf.getvalue()


def red_width(jpeg: bytes, row: float) -> int:
    a = np.asarray(Image.open(io.BytesIO(jpeg)).convert("RGB")).astype(int)
    y = int(row * a.shape[0])
    red = (a[y, :, 0] > 150) & (a[y, :, 1] < 110)
    return int(red.sum())


def red_bottom(jpeg: bytes) -> float:
    a = np.asarray(Image.open(io.BytesIO(jpeg)).convert("RGB")).astype(int)
    red = (a[..., 0] > 150) & (a[..., 1] < 110)
    return float(np.where(red.any(1))[0].max()) / a.shape[0]


# ---------- fit engine ----------

def t_labels():
    ok(F.label_for(-5) == "too_tight" and F.label_for(0) == "fitted" and F.label_for(5) == "comfortable")
    ok(F.label_for(12) == "relaxed" and F.label_for(25) == "oversized")
h.test("ease → fit label bands", t_labels)


def t_standard_chart_and_recommend():
    chart = F.standard_chart(["XS", "S", "M", "L", "XL", "UK 12", "EU 40", "weird"], "dress")
    ok("weird" not in chart and "UK 12" in chart and "EU 40" in chart, list(chart))
    ok(chart["XL"]["bust"] > chart["M"]["bust"] > chart["XS"]["bust"])
    table = F.fit_table(BODY, {k: chart[k] for k in ("XS", "S", "M", "L", "XL")}, "dress")
    xs = next(f for f in table if f.size == "XS")
    ok(not xs.tight, "XS (cut for 82 cm + ease) is fitted, not too tight")
    xxs = F.fit_size(BODY, "XXS", F.standard_chart(["XXS"], "dress")["XXS"], "dress")
    ok(xxs.tight and any(z.label == "too_tight" for z in xxs.zones), "XXS is too tight on an 88 cm bust")
    best = F.recommend(table)
    ok(best.size == "S", f"S is cut for an 88 cm bust, got {best.size}")
    ok("Size S" in F.explain(best, "dress", BODY) and "room" in F.explain(best, "dress", BODY))
h.test("standard chart (alpha/UK/EU), too-tight flag, recommended size", t_standard_chart_and_recommend)


def t_lengths():
    ok("mini" in F._length_note(60, "dress", BODY))
    ok("maxi" in F._length_note(130, "dress", BODY))
    ok("cropped" in F._length_note(50, "top", BODY))
h.test("length read-out follows the body's height", t_lengths)


# ---------- renderer ----------

def t_render_sizes_differ():
    p, g = person_jpeg(), garment_png()
    chart = F.standard_chart(["S", "XL"], "top")
    small = R.render(p, LM, BODY, g, "top", chart["S"])
    big = R.render(p, LM, BODY, g, "top", {**chart["XL"], "length": 80})
    ok(red_width(big, 0.40) > red_width(small, 0.40) + 8, (red_width(small, 0.40), red_width(big, 0.40)))
    ok(red_bottom(big) > red_bottom(small) + 0.05, "longer size hangs lower")
    head = np.asarray(Image.open(io.BytesIO(small)).convert("RGB"))[80:140, 280:320].astype(int)
    ok(not ((head[..., 0] > 150) & (head[..., 1] < 110)).any(), "the face is never covered")
h.test("renderer: bigger size draws wider and longer; face untouched", t_render_sizes_differ)


def t_render_rejects():
    p = person_jpeg()
    blank = io.BytesIO(); Image.new("RGB", (200, 200), "white").save(blank, format="PNG")
    for bad, why in ((lambda: R.render(p, LM, BODY, blank.getvalue(), "top", {"bust": 96}), "blank garment"),
                     (lambda: R.render(p, LM, BODY, garment_png(), "shoes", {}), "shoes"),
                     (lambda: R.render(p, {k: v for k, v in LM.items() if k != "feet"}, BODY, garment_png(), "top", {}), "landmark")):
        try:
            bad(); ok(False, f"should reject {why}")
        except R.RenderError:
            pass
h.test("renderer: clear errors for no garment, unsupported category, missing landmark", t_render_rejects)


# ---------- API ----------

def profile_body(key=None, **over):
    b = {"consent": True, "confirm_self": True, "height_cm": 168, "bust_cm": 88, "waist_cm": 70,
         "hips_cm": 96, "landmarks": LM, "retention": "30d"}
    if key:
        b["photo_key"] = key
    b.update(over)
    return b


_ctx = {}


def t_profile_setup():
    hd = signup(client, "fit@example.com")
    _ctx["h"] = hd
    ok(client.get("/v1/tryon/profile", headers=hd).json() == {"exists": False})
    key = upload(client, hd, "tryon", person_jpeg())
    ok(client.put("/v1/tryon/profile", json=profile_body(key, consent=False), headers=hd).status_code == 422, "consent")
    ok(client.put("/v1/tryon/profile", json=profile_body(None), headers=hd).status_code == 422, "photo needed first time")
    bad = dict(LM, feet=[0.5, 0.1])
    ok(client.put("/v1/tryon/profile", json=profile_body(key, landmarks=bad), headers=hd).status_code == 422, "landmark order")
    other = signup(client, "other@example.com")
    other_key = upload(client, other, "tryon", person_jpeg())
    ok(client.put("/v1/tryon/profile", json=profile_body(other_key), headers=hd).status_code == 422,
       "cannot use another user's upload")
    r = client.put("/v1/tryon/profile", json=profile_body(key), headers=hd)
    ok(r.status_code == 200, r.text)
    j = r.json()
    ok(j["exists"] and j["expires_at"] and j["photo_url"], j)
    ok(not storage.exists(key), "raw upload removed after copy")
    with SessionLocal() as db:
        p = db.scalar(select(TryOnProfile))
        ok(p.photo_key.startswith("tryon/") and storage.exists(p.photo_key))
        _ctx["photo"] = p.photo_key
    # update measurements only, keep photo
    r = client.put("/v1/tryon/profile", json=profile_body(None, bust_cm=90, retention="keep"), headers=hd)
    ok(r.status_code == 200 and r.json()["bust_cm"] == 90 and r.json()["expires_at"] is None, r.text)
h.test("profile: consent, own upload only, landmark checks, photo moved private, edit", t_profile_setup)


def t_fit_and_render_product():
    hd = _ctx["h"]
    with SessionLocal() as db:
        b = Brand(slug="maison", name="Maison"); db.add(b); db.flush()
        pr = Product(brand_id=b.id, external_id="d1", title="Wrap dress", category="dress", fit="regular",
                     sizes=["S", "M", "L"], image_url="https://cdn.example.com/d1.png", product_url="https://example.com/d1",
                     attributes={"size_chart": {"S": {"bust": 92, "waist": 74, "hips": 100, "length": 100},
                                                "M": {"bust": 98, "waist": 80, "hips": 106, "length": 102},
                                                "L": {"bust": 104, "waist": 86, "hips": 112, "length": 104}}})
        db.add(pr); db.commit(); _ctx["pid"] = str(pr.id)
    S.fetch_remote_image = lambda url: garment_png((30, 30, 200))     # no network in tests
    f = client.get(f"/v1/tryon/fit?product_id={_ctx['pid']}", headers=hd).json()
    ok(f["chart_source"] == "brand" and [s["size"] for s in f["sizes"]] == ["S", "M", "L"], f)
    ok(f["recommended"] == "M", f"bust 90 → M, got {f['recommended']}")
    ok(all(s["explanation"].startswith(f"Size {s['size']}") for s in f["sizes"]))
    urls = []
    for size in ("S", "L"):
        r = client.post("/v1/tryon/renders", json={"product_id": _ctx["pid"], "size": size}, headers=hd)
        ok(r.status_code == 202, r.text)
        job = client.get(f"/v1/tryon/renders/jobs/{r.json()['job_id']}", headers=hd).json()
        ok(job["status"] == "done", job)
        ok(job["result"]["size"] == size and job["result"]["fit"]["chart_source"] == "brand")
        urls.append(job["result"]["image_url"])
    ok(urls[0] != urls[1])
    ok(client.post("/v1/tryon/renders", json={"product_id": _ctx["pid"], "size": "XXL"}, headers=hd).json()
       and client.get(f"/v1/tryon/renders/jobs/{client.post('/v1/tryon/renders', json={'product_id': _ctx['pid'], 'size': 'XXL'}, headers=hd).json()['job_id']}", headers=hd).json()["status"] == "failed",
       "unknown size fails cleanly")
    lst = client.get("/v1/tryon/renders", headers=hd).json()["renders"]
    ok(len(lst) == 2 and {x["size"] for x in lst} == {"S", "L"}, lst)
h.test("Discover product: brand size chart, suggested size, render S and L", t_fit_and_render_product)


def t_closet_item():
    hd = _ctx["h"]
    iid = add_item(client, hd, category="top", fit="regular")
    f = client.get(f"/v1/tryon/fit?item_id={iid}", headers=hd).json()
    ok(f["chart_source"] == "estimated" and f["sizes"][0]["size"] == "Yours", f)
    r = client.put(f"/v1/tryon/items/{iid}/size", json={"size_label": "M", "measurements": {"bust": 100, "length": 64, "junk": 9999}}, headers=hd)
    ok(r.status_code == 200 and r.json()["measurements"] == {"bust": 100.0, "length": 64.0}, r.text)
    f = client.get(f"/v1/tryon/fit?item_id={iid}", headers=hd).json()
    ok(f["chart_source"] == "measured" and f["sizes"][0]["size"] == "M", f)
    other = signup(client, "nosy@example.com")
    ok(client.get(f"/v1/tryon/fit?item_id={iid}", headers=other).status_code in (404, 409), "not someone else's piece")
    ok(client.get(f"/v1/tryon/fit?item_id={iid}&product_id={_ctx['pid']}", headers=hd).status_code == 422)
h.test("closet piece: estimated fit, then measured from its label", t_closet_item)


def t_pro_gate():
    hd = signup(client, "free@example.com")
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "free@example.com"))
        u.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    key = upload(client, hd, "tryon", person_jpeg())
    ok(client.put("/v1/tryon/profile", json=profile_body(key), headers=hd).status_code == 200, "setup is free")
    ok(client.get(f"/v1/tryon/fit?product_id={_ctx['pid']}", headers=hd).status_code == 402)
    ok(client.post("/v1/tryon/renders", json={"product_id": _ctx["pid"], "size": "M"}, headers=hd).status_code == 402)
h.test("Pro only: set-up free, fit + render return 402 for a lapsed trial", t_pro_gate)


def t_retention_purge():
    hd = signup(client, "expire@example.com")
    key = upload(client, hd, "tryon", person_jpeg())
    client.put("/v1/tryon/profile", json=profile_body(key), headers=hd)
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.email == "expire@example.com"))
        p = db.scalar(select(TryOnProfile).where(TryOnProfile.user_id == u.id))
        photo = p.photo_key
        p.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    ok(client.get("/v1/tryon/profile", headers=hd).json() == {"exists": False}, "expired profile purged on read")
    ok(not storage.exists(photo), "photo deleted")
h.test("30-day retention: expired photo is purged", t_retention_purge)


def t_wipe_and_account_delete():
    hd = _ctx["h"]
    with SessionLocal() as db:
        keys = [r.image_key for r in db.scalars(select(TryOnRender))]
    ok(keys and all(storage.exists(k) for k in keys))
    rid = client.get("/v1/tryon/renders", headers=hd).json()["renders"][0]["id"]
    ok(client.delete(f"/v1/tryon/renders/{rid}", headers=hd).status_code == 204)
    ok(client.delete("/v1/tryon/profile", headers=hd).status_code == 204)
    ok(client.get("/v1/tryon/profile", headers=hd).json() == {"exists": False})
    ok(not storage.exists(_ctx["photo"]) and not any(storage.exists(k) for k in keys), "photo + renders gone")
    # account deletion also takes try-on data
    hd2 = signup(client, "leaver@example.com")
    key = upload(client, hd2, "tryon", person_jpeg())
    client.put("/v1/tryon/profile", json=profile_body(key), headers=hd2)
    exp = client.get("/v1/me/export", headers=hd2).json()
    ok(len(exp["tryon_profile"]) == 1, "export includes try-on data")
    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.email == "leaver@example.com"))
        photo = db.scalar(select(TryOnProfile.photo_key).where(TryOnProfile.user_id == uid))
    ok(client.delete("/v1/me", headers=hd2).status_code == 204)
    with SessionLocal() as db:
        ok(db.scalar(select(TryOnProfile).where(TryOnProfile.user_id == uid)) is None, "profile row gone")
    ok(not storage.exists(photo), "photo gone with the account")
h.test("wipe: delete a try, delete everything; export + account deletion cover try-on", t_wipe_and_account_delete)


h.report()
