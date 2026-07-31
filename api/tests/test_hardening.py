"""Hardening tests: token encryption at rest + the calendar-connect flow storing
ciphertext, not plaintext. Run: python3 tests/test_hardening.py
"""
import sys, os, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine, SessionLocal  # noqa: E402
from app.models import Base, CalendarConnection, User  # noqa: E402
from app.core.crypto import encrypt, decrypt  # noqa: E402
from sqlalchemy import select  # noqa: E402

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


def t_encrypt_roundtrip():
    secret = "ya29.google-oauth-access-token-xyz"
    ct = encrypt(secret)
    ok(ct != secret, "ciphertext differs from plaintext")
    ok(secret not in ct, "plaintext not embedded in ciphertext")
    ok(decrypt(ct) == secret, "decrypt recovers the original")
test("token encryption round-trips and hides plaintext", t_encrypt_roundtrip)


def t_encrypt_nulls():
    ok(encrypt(None) is None, "encrypt(None) is None")
    ok(decrypt(None) is None, "decrypt(None) is None")
    ok(decrypt("garbage") is None, "decrypt of junk returns None, not a crash")
test("encryption handles nulls and bad input safely", t_encrypt_nulls)


def t_calendar_connect_stores_ciphertext():
    H = {"Authorization": "Bearer " + client.post(
        "/v1/auth/signup", json={"email": "harden@x.com", "password": "pw123456"}).json()["access_token"]}
    r = client.post("/v1/integrations/calendar/connect",
                    json={"access_token": "SECRET_TOKEN_123",
                          "refresh_token": "REFRESH_456",
                          "category_mapping": {"demo": 5}}, headers=H)
    ok(r.status_code == 200, r.text)
    # inspect the row directly — the stored token must be ciphertext
    db = SessionLocal()
    uid = db.scalar(select(User).where(User.email == "harden@x.com")).id
    conn = db.scalar(select(CalendarConnection).where(CalendarConnection.user_id == uid))
    stored = conn.access_token_encrypted
    db.close()
    ok(stored is not None, "token stored")
    ok("SECRET_TOKEN_123" not in stored, "plaintext token is NOT in the database")
    ok(decrypt(stored) == "SECRET_TOKEN_123", "but it decrypts back correctly")
test("calendar connect stores OAuth tokens encrypted, not plaintext", t_calendar_connect_stores_ciphertext)


if __name__ == "__main__":
    print("\nSylia hardening\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
