"""API smoke test. Boots the whole FastAPI app against a throwaway SQLite DB and
exercises the real wiring: health, signup, login, auth guard, and an
authenticated daily-look call. Run: python3 tests/test_api_smoke.py
"""
import os, sys, tempfile

# point the app at a temp sqlite file BEFORE importing it
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402

# create the schema explicitly (don't rely on the startup hook firing under the harness)
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


def t_health():
    r = client.get("/health")
    ok(r.status_code == 200, r.text)
    ok(r.json()["status"] == "ok")
test("health returns ok", t_health)


_tokens = {}

def t_signup():
    r = client.post("/v1/auth/signup", json={"email": "maya@example.com", "password": "s3cret!!"})
    ok(r.status_code == 201, r.text)
    body = r.json()
    ok("access_token" in body and "refresh_token" in body)
    _tokens["access"] = body["access_token"]
    _tokens["refresh"] = body["refresh_token"]
test("signup creates a user and returns tokens", t_signup)


def t_duplicate_signup():
    r = client.post("/v1/auth/signup", json={"email": "maya@example.com", "password": "x"})
    ok(r.status_code == 409, f"expected 409, got {r.status_code}")
test("duplicate email is rejected", t_duplicate_signup)


def t_login():
    r = client.post("/v1/auth/login", json={"email": "maya@example.com", "password": "s3cret!!"})
    ok(r.status_code == 200, r.text)
    ok("access_token" in r.json())
test("login with correct password works", t_login)


def t_bad_login():
    r = client.post("/v1/auth/login", json={"email": "maya@example.com", "password": "wrong"})
    ok(r.status_code == 401, f"expected 401, got {r.status_code}")
test("login with wrong password is rejected", t_bad_login)


def t_auth_guard():
    r = client.get("/v1/daily-look")
    ok(r.status_code == 401, f"unauthed daily-look should be 401, got {r.status_code}")
test("protected route rejects missing token", t_auth_guard)


def t_daily_look_authed():
    h = {"Authorization": f"Bearer {_tokens['access']}"}
    r = client.get("/v1/daily-look", headers=h)
    ok(r.status_code == 200, r.text)
    ok("looks" in r.json(), "response has looks key")
test("authenticated daily-look responds (empty closet → guidance)", t_daily_look_authed)


def t_cv_job_handle():
    h = {"Authorization": f"Bearer {_tokens['access']}"}
    r = client.post("/v1/wardrobe/items", json={"s3_key_original": "uploads/x.jpg"}, headers=h)
    ok(r.status_code == 202, f"CV upload should return 202, got {r.status_code}")
    ok("job_id" in r.json(), "returns a job handle")
test("closet upload returns a 202 job handle (async CV)", t_cv_job_handle)


def t_quiz_fallback():
    h = {"Authorization": f"Bearer {_tokens['access']}"}
    r = client.post("/v1/body-profile/quiz-fallback",
                    json={"undertone": "cool", "silhouette": "hourglass"}, headers=h)
    ok(r.status_code == 200, r.text)
    ok(r.json()["analysis_method"] == "quiz_fallback")
test("non-camera quiz fallback path works", t_quiz_fallback)


if __name__ == "__main__":
    print("\nSylia API smoke\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    try:
        os.unlink(_db)
    except OSError:
        pass
    sys.exit(1 if _f else 0)
