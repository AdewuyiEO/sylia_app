"""Brand platform: admin onboarding, Partner API catalog sync, closet-gap
analysis, fit-gated Discover, click tracking, add-to-closet, k-anonymous
insights, RevenueCat webhook. Run: python tests/test_catalog.py
"""
import os, sys, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
os.environ["LOCAL_STORAGE_DIR"] = os.path.join(_dir, "storage")
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
os.environ["ADMIN_TOKEN"] = "admin-test-token"
os.environ["INSIGHTS_MIN_COHORT"] = "2"
os.environ["REVENUECAT_WEBHOOK_SECRET"] = "rc-secret"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.domains.catalog import gap  # noqa: E402
from app.domains.daily_look.scorer import Garment, BodyProfile, IdentityProfile  # noqa: E402
from support import Harness, ok, signup, add_item  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
h = Harness("Sylia brand platform")
ADMIN = {"X-Admin-Token": "admin-test-token"}
_ctx = {}


def product(ext, category, sub, color, f=3, w=2, **kw):
    return {"external_id": ext, "title": f"{color} {sub}".title(), "category": category,
            "subcategory": sub, "primary_color": color, "formality_score": f, "warmth_score": w,
            "product_url": f"https://brand.example/p/{ext}",
            "affiliate_url": f"https://aff.example/r?to={ext}",
            "image_url": f"https://cdn.example/{ext}.jpg",
            "prices": [{"country": "FR", "currency": "EUR", "amount_minor": 8900},
                       {"currency": "USD", "amount_minor": 9900}], **kw}


def t_gap_pure():
    wardrobe = [Garment("t1", "top", "shirt", "white", 3, 2), Garment("t2", "top", "blouse", "cream", 3, 2),
                Garment("s1", "shoes", "loafers", "brown", 3, 2)]
    trousers = Garment("p1", "bottom", "trousers", "navy", 3, 2)
    res = gap.analyze(trousers, wardrobe, BodyProfile(), IdentityProfile())
    ok(res.unlocks >= 2 and res.fit_score >= 0.6, f"missing bottoms are a real gap: {res}")
    ok({"t1", "t2", "s1"} <= set(res.pairs_with), "pairs with the owned pieces")
    ok("Pairs with" in gap.rationale(res), gap.rationale(res))
    dup = gap.analyze(Garment("p2", "top", "shirt", "white", 3, 2),
                      wardrobe + [trousers], BodyProfile(), IdentityProfile())
    ok(dup.duplicate_of == "t1" and dup.fit_score < res.fit_score, f"duplicate scores lower: {dup}")
    gown = gap.analyze(Garment("p3", "dress", "gown", "black", 5, 1), wardrobe, BodyProfile(), IdentityProfile())
    ok(gown.fit_score < 0.6, f"a black-tie gown for a smart-casual closet stays gated: {gown}")
h.test("gap analysis rewards real gaps, punishes duplicates", t_gap_pure)


def t_admin_onboards_brand():
    ok(client.post("/v1/admin/brands", json={"slug": "maison", "name": "Maison"}).status_code == 401,
       "admin token required")
    r = client.post("/v1/admin/brands", json={"slug": "maison", "name": "Maison", "regions": ["fr", "gb", "us"]},
                    headers=ADMIN)
    ok(r.status_code == 201, r.text)
    _ctx["key"] = r.json()["partner_key"]
    _ctx["brand_id"] = r.json()["brand_id"]
    ok(client.post("/v1/admin/brands", json={"slug": "maison", "name": "X"}, headers=ADMIN).status_code == 409)
h.test("admin onboards a brand and issues a one-time partner key", t_admin_onboards_brand)


def t_partner_catalog_sync():
    P = {"X-Partner-Key": _ctx["key"]}
    ok(client.get("/v1/partner/me", headers={"X-Partner-Key": "nope"}).status_code == 401)
    batch = {"products": [
        product("TRS-1", "bottom", "trousers", "navy"),
        product("SKT-1", "bottom", "skirt", "olive"),
        product("SHT-1", "top", "shirt", "white"),
        product("GWN-1", "dress", "gown", "black", f=5, w=1),
        product("JP-ONLY", "bottom", "chinos", "sand", regions=["JP"]),
    ]}
    r = client.put("/v1/partner/products", json=batch, headers=P)
    ok(r.status_code == 200 and r.json() == {"created": 5, "updated": 0}, r.text)
    batch["products"][0]["title"] = "Navy Wool Trousers"
    r = client.put("/v1/partner/products", json={"products": batch["products"][:1]}, headers=P)
    ok(r.json() == {"created": 0, "updated": 1}, "upsert by external_id")
    bad = client.put("/v1/partner/products", json={"products": [product("X", "hat", "fedora", "red")]}, headers=P)
    ok(bad.status_code == 422, "unknown category rejected")
    insecure = product("Y", "top", "shirt", "red")
    insecure["product_url"] = "http://brand.example/y"
    ok(client.put("/v1/partner/products", json={"products": [insecure]}, headers=P).status_code == 422,
       "non-https URLs rejected")
    ok(client.get("/v1/partner/me", headers=P).json()["products"] == 5)
h.test("partner API upserts a validated catalog", t_partner_catalog_sync)


def _closet(email, country="FR"):
    H = signup(client, email, country=country)
    add_item(client, H, category="top", subcategory="shirt", primary_color="white", formality_score=3, warmth_score=2)
    add_item(client, H, category="top", subcategory="blouse", primary_color="cream", formality_score=3, warmth_score=2)
    add_item(client, H, category="shoes", subcategory="loafers", primary_color="brown", formality_score=3, warmth_score=2)
    return H


def t_discover_is_fit_gated_and_regional():
    H = _closet("shopper@x.com")
    _ctx["H"] = H
    r = client.get("/v1/discover", headers=H)
    ok(r.status_code == 200, r.text)
    body = r.json()
    ok("commission" in body["disclosure"], "disclosure always present")
    recs = body["recommendations"]
    titles = [c["title"] for c in recs]
    ok(recs and all(c["fit_score"] >= 0.6 for c in recs), f"only gated products: {recs}")
    ok("Navy Wool Trousers" in titles, f"the missing bottom is recommended: {titles}")
    ok(not any("Gown" in t for t in titles), "the gown that doesn't fit the closet is gated out")
    ok(not any("Chinos" in t for t in titles), "a JP-only product isn't shown in FR")
    ok(not any(c["title"] == "White Shirt" for c in recs), "a duplicate of an owned piece is gated out")
    first = recs[0]
    ok(first["price"] == {"country": "FR", "currency": "EUR", "amount_minor": 8900}, f"FR price: {first['price']}")
    ok(first["rationale"].startswith("Pairs with"), first["rationale"])
    ok([c["fit_score"] for c in recs] == sorted([c["fit_score"] for c in recs], reverse=True), "ranked by fit")
    _ctx["rec"] = first
h.test("Discover shows only fit-gated, region-available products, ranked by fit", t_discover_is_fit_gated_and_regional)


def t_click_tracking():
    rec = _ctx["rec"]
    r = client.post(f"/v1/discover/{rec['recommendation_id']}/click", headers=_ctx["H"])
    ok(r.status_code == 200, r.text)
    ok(r.json()["url"].startswith("https://aff.example/r?") and "sylia_ref=" in r.json()["url"], r.json())
    other = signup(client, "clickjack@x.com")
    ok(client.post(f"/v1/discover/{rec['recommendation_id']}/click", headers=other).status_code == 404,
       "can't click someone else's recommendation")
h.test("clicks are tracked and go to the affiliate URL", t_click_tracking)


def t_add_bought_item_to_closet():
    r = client.post("/v1/wardrobe/items/from-product",
                    json={"product_id": _ctx["rec"]["product_id"], "size": "38"}, headers=_ctx["H"])
    ok(r.status_code == 201, r.text)
    item = r.json()
    ok(item["brand"] == "Maison" and item["classification_confidence"] == 1.0, item)
    ok(item["image_url"].startswith("https://cdn.example/"), "uses the catalog image")
    after = client.get("/v1/discover", headers=_ctx["H"]).json()["recommendations"]
    ok(all(c["product_id"] != _ctx["rec"]["product_id"] for c in after), "owned product no longer recommended")
h.test("bought items join the closet with catalog-accurate tags", t_add_bought_item_to_closet)


def t_insights_are_k_anonymous():
    P = {"X-Partner-Key": _ctx["key"]}
    one = client.get("/v1/partner/insights", headers=P).json()
    ok(one["reach"]["users"] is None and one["by_country"] == {}, f"one user → suppressed: {one}")
    _closet("shopper2@x.com")
    H2 = _closet("shopper4@x.com")
    client.get("/v1/discover", headers=H2)
    two = client.get("/v1/partner/insights", headers=P).json()
    ok(two["reach"]["users"] == 2 and two["by_country"].get("FR") == 2, f"2 users clear k=2: {two}")
    ok(two["reach"]["click_through_users"] == 1, "click-through counted")
    ok(all(isinstance(v, int) for v in two["top_products_by_reach"].values()), "aggregates only")
    ok("user_id" not in str(two), "no user ids ever leave")
h.test("insights are aggregated and k-anonymous", t_insights_are_k_anonymous)


def t_out_of_stock_removed():
    P = {"X-Partner-Key": _ctx["key"]}
    ok(client.delete("/v1/partner/products/SKT-1", headers=P).status_code == 204)
    H = _closet("late@x.com")
    recs = client.get("/v1/discover", headers=H).json()["recommendations"]
    ok(all("Skirt" not in c["title"] for c in recs), "out-of-stock product not shown")
h.test("delisted products leave Discover", t_out_of_stock_removed)


def t_revenuecat_webhook():
    H = signup(client, "iap@x.com")
    uid = client.get("/v1/me", headers=H).json()["id"]
    ev = {"event": {"type": "INITIAL_PURCHASE", "app_user_id": uid, "store": "APP_STORE",
                    "product_id": "sylia_pro_monthly", "entitlement_ids": ["pro"],
                    "expiration_at_ms": 4102444800000}}
    ok(client.post("/v1/billing/revenuecat/webhook", json=ev).status_code == 401, "auth header required")
    ok(client.post("/v1/billing/revenuecat/webhook", json=ev,
                   headers={"Authorization": "Bearer wrong"}).status_code == 401)
    r = client.post("/v1/billing/revenuecat/webhook", json=ev, headers={"Authorization": "Bearer rc-secret"})
    ok(r.json()["applied"], r.text)
    st = client.get("/v1/billing/status", headers=H).json()
    ok(st["status"] == "active" and st["entitled"] and st["provider"] == "app_store", st)
    cancel = {"event": {**ev["event"], "type": "CANCELLATION"}}
    client.post("/v1/billing/revenuecat/webhook", json=cancel, headers={"Authorization": "rc-secret"})
    ok(client.get("/v1/billing/status", headers=H).json()["entitled"], "cancel keeps access until expiry")
    expire = {"event": {**ev["event"], "type": "EXPIRATION", "expiration_at_ms": 1000}}
    client.post("/v1/billing/revenuecat/webhook", json=expire, headers={"Authorization": "rc-secret"})
    st = client.get("/v1/billing/status", headers=H).json()
    ok(st["status"] == "canceled" and not st["entitled"], f"expired → not entitled: {st}")
    unknown = {"event": {**ev["event"], "app_user_id": "$RCAnonymousID:abc"}}
    r = client.post("/v1/billing/revenuecat/webhook", json=unknown, headers={"Authorization": "rc-secret"})
    ok(r.status_code == 200 and not r.json()["applied"], "unknown buyer acknowledged, not applied")
h.test("RevenueCat webhook drives entitlement (purchase, cancel, expire)", t_revenuecat_webhook)


if __name__ == "__main__":
    h.report()
