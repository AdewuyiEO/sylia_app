"""Auth hardening + account: password policy, refresh rotation/revocation,
logout, rate limiting, Sign in with Apple, regional profile, export, deletion.
Run: python tests/test_auth_account.py
"""
import os, sys, tempfile, time
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
os.environ["LOCAL_STORAGE_DIR"] = os.path.join(_dir, "storage")
os.environ["AUTH_RATE_LIMIT_PER_MIN"] = "1000"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"     # force the in-memory KV
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import jwt  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.core.storage import storage  # noqa: E402
from support import Harness, ok, signup, upload, add_item  # noqa: E402

Base.metadata.create_all(bind=engine)
client = TestClient(app)
h = Harness("Sylia auth + account")


def t_password_policy():
    r = client.post("/v1/auth/signup", json={"email": "short@x.com", "password": "abc"})
    ok(r.status_code == 422, f"short password rejected, got {r.status_code}")
    r = client.post("/v1/auth/signup", json={"email": "nopw@x.com"})
    ok(r.status_code == 422, "password is required for email signup")
h.test("signup enforces a password policy", t_password_policy)


def t_email_case_insensitive():
    signup(client, "Case@X.com")
    r = client.post("/v1/auth/login", json={"email": "case@x.com", "password": "pw123456"})
    ok(r.status_code == 200, "login ignores email case")
    r = client.post("/v1/auth/signup", json={"email": "CASE@x.com", "password": "pw123456"})
    ok(r.status_code == 409, "duplicate detection ignores case")
h.test("emails are case-insensitive", t_email_case_insensitive)


def t_refresh_rotation():
    r = client.post("/v1/auth/signup", json={"email": "rot@x.com", "password": "pw123456"}).json()
    first = r["refresh_token"]
    r2 = client.post("/v1/auth/refresh", json={"refresh_token": first})
    ok(r2.status_code == 200, r2.text)
    second = r2.json()["refresh_token"]
    ok(second != first, "a new refresh token is issued")
    reuse = client.post("/v1/auth/refresh", json={"refresh_token": first})
    ok(reuse.status_code == 401, "a used refresh token cannot be replayed")
    ok(client.post("/v1/auth/refresh", json={"refresh_token": second}).status_code == 200, "new one works")
h.test("refresh tokens rotate and can't be replayed", t_refresh_rotation)


def t_logout_revokes():
    r = client.post("/v1/auth/signup", json={"email": "out@x.com", "password": "pw123456"}).json()
    ok(client.post("/v1/auth/logout", json={"refresh_token": r["refresh_token"]}).status_code == 204)
    ok(client.post("/v1/auth/refresh", json={"refresh_token": r["refresh_token"]}).status_code == 401,
       "logged-out refresh token is dead")
    ok(client.post("/v1/auth/refresh", json={"refresh_token": r["access_token"]}).status_code == 401,
       "an access token is not a refresh token")
h.test("logout revokes the refresh token", t_logout_revokes)


def t_rate_limit():
    from app.config import get_settings
    from app.core.ratelimit import limit
    from fastapi import FastAPI, Depends
    mini = FastAPI()

    @mini.post("/x", dependencies=[Depends(limit("t", 3))])
    def x():
        return {}
    c = TestClient(mini)
    codes = [c.post("/x").status_code for _ in range(5)]
    ok(codes[:3] == [200] * 3 and codes[3:] == [429, 429], f"4th+ call limited: {codes}")
    ok(get_settings().auth_rate_limit_per_min > 0)
h.test("rate limiter returns 429 past the per-minute budget", t_rate_limit)


# Sign in with Apple, against a locally generated key standing in for Apple's
_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
from app.domains.auth import apple as apple_mod  # noqa: E402
apple_mod.signing_key_for = lambda token: _key.public_key()


def _apple_token(sub, email=None, verified=True, aud="com.sylia.stylist"):
    claims = {"iss": "https://appleid.apple.com", "aud": aud, "sub": sub,
              "iat": int(time.time()), "exp": int(time.time()) + 600}
    if email:
        claims.update(email=email, email_verified="true" if verified else "false")
    return jwt.encode(claims, _key, algorithm="RS256")


def t_apple_signin():
    r = client.post("/v1/auth/apple", json={"identity_token": _apple_token("apple-1", "a1@privaterelay.appleid.com"),
                                             "display_name": "Ada", "country": "FR"})
    ok(r.status_code == 200, r.text)
    H = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = client.get("/v1/me", headers=H).json()
    ok(me["auth_provider"] == "apple" and me["display_name"] == "Ada", me)
    ok(me["country"] == "FR" and me["units"] == "metric", "region defaults from country")
    again = client.post("/v1/auth/apple", json={"identity_token": _apple_token("apple-1")})
    H2 = {"Authorization": f"Bearer {again.json()['access_token']}"}
    ok(client.get("/v1/me", headers=H2).json()["id"] == me["id"], "same Apple sub → same account")
    bad = client.post("/v1/auth/apple", json={"identity_token": _apple_token("apple-2", aud="com.evil.app")})
    ok(bad.status_code == 401, "token for another app's audience is rejected")
h.test("Sign in with Apple creates, re-finds and verifies audience", t_apple_signin)


def t_apple_links_verified_email_only():
    signup(client, "linkme@x.com")
    r = client.post("/v1/auth/apple", json={"identity_token": _apple_token("apple-3", "linkme@x.com", verified=False)})
    ok(r.status_code == 200)
    me = client.get("/v1/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    ok(me["email"] != "linkme@x.com", "unverified Apple email must not take over an existing account")
    r = client.post("/v1/auth/apple", json={"identity_token": _apple_token("apple-4", "linkme@x.com")})
    me = client.get("/v1/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    ok(me["email"] == "linkme@x.com", "verified Apple email links to the existing account")
h.test("Apple sign-in links accounts only on a verified email", t_apple_links_verified_email_only)


def t_profile_regions():
    H = signup(client, "us@x.com", country="US", timezone="America/New_York", locale="en-US")
    me = client.get("/v1/me", headers=H).json()
    ok(me["units"] == "imperial", "US defaults to imperial")
    r = client.patch("/v1/me", json={"units": "metric", "country": "gb", "timezone": "Europe/London"}, headers=H)
    ok(r.status_code == 200 and r.json()["country"] == "GB" and r.json()["units"] == "metric", r.text)
    ok(client.patch("/v1/me", json={"timezone": "Mars/Olympus"}, headers=H).status_code == 422, "bad tz")
    ok(client.patch("/v1/me", json={"units": "cubits"}, headers=H).status_code == 422, "bad units")
h.test("regional profile defaults and validation", t_profile_regions)


def t_export_and_delete():
    H = signup(client, "gone@x.com")
    item_id = add_item(client, H, category="top", primary_color="navy")
    client.post("/v1/body-profile/quiz-fallback", json={"undertone": "warm", "silhouette": "rectangle"}, headers=H)
    exp = client.get("/v1/me/export", headers=H)
    ok(exp.status_code == 200, exp.text)
    data = exp.json()
    ok(data["user"]["email"] == "gone@x.com" and "password_hash" not in data["user"], "no secrets exported")
    ok(len(data["closet"]) == 1 and data["closet"][0]["id"] == item_id, "closet exported")
    ok(len(data["body_profile"]) == 1, "body profile exported")
    key = data["closet"][0]["s3_key_original"]
    ok(storage.exists(key), "photo exists before deletion")

    ok(client.delete("/v1/me", headers=H).status_code == 204, "account deleted")
    ok(not storage.exists(key), "photos deleted with the account")
    ok(client.get("/v1/me", headers=H).status_code == 401, "old token no longer works")
    r = client.post("/v1/auth/login", json={"email": "gone@x.com", "password": "pw123456"})
    ok(r.status_code == 401, "can't log in to a deleted account")
    ok(client.post("/v1/auth/signup", json={"email": "gone@x.com", "password": "pw123456"}).status_code == 201,
       "email is free to re-register")
h.test("export returns everything; delete removes rows and photos", t_export_and_delete)


def t_upload_guards():
    H = signup(client, "up@x.com")
    r = client.post("/v1/uploads", json={"purpose": "closet", "content_type": "application/pdf"}, headers=H)
    ok(r.status_code == 422, "non-image content type rejected")
    r = client.post("/v1/uploads", json={"purpose": "selfies", "content_type": "image/png"}, headers=H)
    ok(r.status_code == 422, "unknown purpose rejected")
    body = client.post("/v1/uploads", json={"purpose": "closet", "content_type": "image/png"}, headers=H).json()
    bad = client.put(body["upload"]["url"], content=b"x", headers={"Content-Type": "image/jpeg"})
    ok(bad.status_code == 415, "content type must match the signed one")
    tampered = client.put(body["upload"]["url"].replace("token=", "token=x"), content=b"x",
                          headers={"Content-Type": "image/png"})
    ok(tampered.status_code == 403, "tampered upload token rejected")
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": body["key"]}, headers=H)
    ok(r.status_code == 422, "a key that was never uploaded is rejected")
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": "uploads/../../etc/passwd"}, headers=H)
    ok(r.status_code == 422, "path traversal rejected")
h.test("upload URLs are scoped, typed and tamper-proof", t_upload_guards)


def t_body_scan_consent_and_cleanup():
    H = signup(client, "body@x.com")
    key = upload(client, H, purpose="body")
    r = client.post("/v1/body-scan", json={"s3_keys": [key]}, headers=H)
    ok(r.status_code == 422, "no consent → refused")
    closet_key = upload(client, H, purpose="closet")
    r = client.post("/v1/body-scan", json={"s3_keys": [closet_key], "consent": True}, headers=H)
    ok(r.status_code == 422, "a closet photo can't be used as a body photo")
    r = client.post("/v1/body-scan", json={"s3_keys": [key], "consent": True}, headers=H)
    ok(r.status_code == 202, r.text)
    job = client.get(f"/v1/body-scan/jobs/{r.json()['job_id']}", headers=H).json()
    ok(job["status"] in ("done", "failed"), f"inline job finished: {job}")
    ok(not storage.exists(key), "body photo deleted after analysis")
    other = signup(client, "peek@x.com")
    ok(client.get(f"/v1/body-scan/jobs/{r.json()['job_id']}", headers=other).status_code == 404,
       "another user can't read the job")
h.test("body scan needs consent, owned keys, and deletes the photo", t_body_scan_consent_and_cleanup)


if __name__ == "__main__":
    h.report()
