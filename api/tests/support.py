"""Shared helpers for the stdlib-style test files. Import AFTER the test file has
set DATABASE_URL / LOCAL_STORAGE_DIR and imported the app."""
import io
import sys


class Harness:
    def __init__(self, title: str):
        self.title, self.passed, self.failed, self.fails = title, 0, 0, []

    def test(self, name, fn):
        try:
            fn()
            self.passed += 1
        except Exception as e:
            self.failed += 1
            self.fails.append(f"  x {name}\n      {type(e).__name__}: {e}")

    def report(self):
        print(f"\n{self.title}\n" + "-" * 40)
        if self.fails:
            print("\n".join(self.fails))
        print(f"{self.passed} passed, {self.failed} failed\n")
        sys.exit(1 if self.failed else 0)


def ok(cond, msg=""):
    assert cond, msg


def signup(client, email: str, password: str = "pw123456", **extra) -> dict:
    r = client.post("/v1/auth/signup", json={"email": email, "password": password, **extra})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def png_bytes(rgb=(44, 54, 72), size: int = 80) -> bytes:
    from PIL import Image
    import numpy as np
    arr = np.full((size, size, 3), 255, np.uint8)
    q = size // 4
    arr[q:size - q, q:size - q] = rgb
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def upload(client, headers, purpose: str = "closet", data: bytes | None = None) -> str:
    """The real phone flow: ask for a signed URL, PUT the bytes, return the key."""
    r = client.post("/v1/uploads", json={"purpose": purpose, "content_type": "image/png"}, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    put = client.put(body["upload"]["url"], content=data or png_bytes(),
                     headers=body["upload"]["headers"])
    assert put.status_code == 204, put.text
    return body["key"]


def add_item(client, headers, **patch) -> str:
    """Upload a garment photo and correct its tags (as a user would)."""
    key = upload(client, headers)
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": key}, headers=headers)
    assert r.status_code == 202, r.text
    item_id = r.json()["item_id"]
    if patch:
        p = client.patch(f"/v1/wardrobe/items/{item_id}", json=patch, headers=headers)
        assert p.status_code == 200, p.text
    return item_id
