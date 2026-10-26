"""Closet data-layer integration test. Drives the real DB path end to end:
upload (row created) → worker persists classification → list → get → correct
tags → soft-delete. Run: python3 tests/test_closet_db.py
"""
import os, sys, tempfile, io

_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
_storage_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["ENV"] = "dev"
os.environ["SYLIA_STORAGE_DIR"] = _storage_dir     # (legacy) 
os.environ["LOCAL_STORAGE_DIR"] = _storage_dir     # the storage module reads this
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402
import numpy as np  # noqa: E402


from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402

from support import upload, png_bytes  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)

_p, _f, _fails = 0, 0, []
def test(name, fn):
    global _p, _f
    try:
        fn(); _p += 1
    except Exception as e:
        _f += 1; _fails.append(f"  x {name}\n      {e}")
def ok(c, m=""): assert c, m


# auth
r = client.post("/v1/auth/signup", json={"email": "closet@example.com", "password": "pw123456"})
H = {"Authorization": f"Bearer {r.json()['access_token']}"}
_ctx = {}


def t_upload_creates_row_and_persists():
    key = upload(client, H, data=png_bytes((44, 54, 72)))
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": key}, headers=H)
    ok(r.status_code == 202, r.text)
    ok("job_id" in r.json())
    # eager worker ran inline → the row should now be classified
    lst = client.get("/v1/wardrobe/items", headers=H).json()
    ok(lst["count"] == 1, f"expected 1 item, got {lst['count']}")
    item = lst["items"][0]
    _ctx["id"] = item["id"]
    ok(item["s3_key_processed"] and "cutouts/" in item["s3_key_processed"], "bg-removed key persisted")
    ok(item["primary_color"] is not None, "colour persisted by worker")
    ok(item["classification_confidence"] is not None, "confidence flipped from NULL (processing) to a value")
    ok(item["image_url"], "item carries a signed image URL")
    img = client.get(item["image_url"])
    ok(img.status_code == 200 and img.content[1:4] == b"PNG", "image URL serves the cut-out")
test("upload creates a row and the worker persists classification", t_upload_creates_row_and_persists)


def t_list_filters_by_category():
    # add a bottom by uploading again then patching its category
    key = upload(client, H, data=png_bytes((60, 90, 130)))
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": key}, headers=H)
    ok(r.status_code == 202)
    lst = client.get("/v1/wardrobe/items", headers=H).json()
    ok(lst["count"] == 2, f"expected 2, got {lst['count']}")
    # both classified as 'top' by the stub; filter should reflect that
    tops = client.get("/v1/wardrobe/items?category=top", headers=H).json()
    ok(tops["count"] == 2, f"expected 2 tops, got {tops['count']}")
    bottoms = client.get("/v1/wardrobe/items?category=bottom", headers=H).json()
    ok(bottoms["count"] == 0, "no bottoms yet")
test("list filters by category", t_list_filters_by_category)


def t_patch_corrects_tags_and_confidence():
    iid = _ctx["id"]
    r = client.patch(f"/v1/wardrobe/items/{iid}",
                     json={"category": "bottom", "primary_color": "indigo", "tags": ["denim"]},
                     headers=H)
    ok(r.status_code == 200, r.text)
    item = r.json()
    ok(item["category"] == "bottom", "category corrected")
    ok(item["primary_color"] == "indigo", "colour corrected")
    ok(item["tags"] == ["denim"], "tags corrected")
    ok(item["classification_confidence"] == 1.0, "manual correction → full confidence")
    # now findable as a bottom
    bottoms = client.get("/v1/wardrobe/items?category=bottom", headers=H).json()
    ok(bottoms["count"] == 1, "corrected item now lists as a bottom")
test("PATCH corrects tags and marks the item fully confident", t_patch_corrects_tags_and_confidence)


def t_get_single_item():
    r = client.get(f"/v1/wardrobe/items/{_ctx['id']}", headers=H)
    ok(r.status_code == 200, r.text)
    ok(r.json()["id"] == _ctx["id"])
test("GET a single item by id", t_get_single_item)


def t_soft_delete_hides_but_keeps():
    iid = _ctx["id"]
    r = client.delete(f"/v1/wardrobe/items/{iid}", headers=H)
    ok(r.status_code == 204, r.text)
    active = client.get("/v1/wardrobe/items", headers=H).json()
    ok(all(i["id"] != iid for i in active["items"]), "soft-deleted item hidden from active list")
    allitems = client.get("/v1/wardrobe/items?active_only=false", headers=H).json()
    ok(any(i["id"] == iid for i in allitems["items"]), "row still exists (soft delete, not hard)")
test("DELETE soft-deletes (hidden from active, row retained)", t_soft_delete_hides_but_keeps)


def t_ownership_isolation():
    # a second user must not see or touch the first user's items
    r2 = client.post("/v1/auth/signup", json={"email": "other@example.com", "password": "pw123456"})
    H2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    lst = client.get("/v1/wardrobe/items?active_only=false", headers=H2).json()
    ok(lst["count"] == 0, "second user sees an empty closet")
    r = client.get(f"/v1/wardrobe/items/{_ctx['id']}", headers=H2)
    ok(r.status_code == 404, "second user cannot fetch first user's item")
    # nor register the first user's photo as their own
    key = upload(client, H)
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": key}, headers=H2)
    ok(r.status_code == 422, f"foreign upload key must be rejected, got {r.status_code}")
test("items are isolated per user (ownership enforced)", t_ownership_isolation)


if __name__ == "__main__":
    print("\nSylia closet data layer\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    try:
        os.unlink(_db)
    except OSError:
        pass
    sys.exit(1 if _f else 0)
