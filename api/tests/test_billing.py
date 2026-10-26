"""Billing + affiliate tests. No Stripe key here, so checkout returns a stub URL
and entitlement is driven by the local trial window — the flow is fully testable.
The fit-gate is pure logic and always enforced. Run: python3 tests/test_billing.py
"""
import sys, os, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.domains.catalog.router import gate_affiliate, AFFILIATE_FIT_THRESHOLD  # noqa: E402

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


def _auth(email):
    return {"Authorization": "Bearer " + client.post(
        "/v1/auth/signup", json={"email": email, "password": "pw123456"}).json()["access_token"]}


def t_new_user_gets_trial():
    H = _auth("bill1@x.com")
    s = client.get("/v1/billing/status", headers=H).json()
    ok(s["status"] == "trial", f"new user in trial, got {s['status']}")
    ok(s["entitled"] is True, "trial user is entitled")
    ok(s["in_trial"] is True, "in_trial flag set")
    ok(s["trial_ends_at"] is not None, "trial end date set")
    ok(s["price_usd"] == 19, f"price is 19, got {s['price_usd']}")
test("new user starts a time-boxed trial and is entitled", t_new_user_gets_trial)


def t_checkout_returns_url():
    H = _auth("bill2@x.com")
    r = client.post("/v1/billing/checkout-session", headers=H)
    ok(r.status_code == 200, r.text)
    ok(r.json()["checkout_url"].startswith("http"), "returns a checkout url")
    ok(r.json()["mode"] == "stub", "stub mode without a Stripe key")
test("checkout session returns a URL (stub without a key)", t_checkout_returns_url)


def t_webhook_unverified_without_secret():
    # no webhook secret configured → we don't trust the event, but don't crash
    r = client.post("/v1/billing/webhook", json={"type": "customer.subscription.created"})
    ok(r.status_code == 200, r.text)
    ok(r.json()["verified"] is False, "unsigned event is not trusted")
test("webhook rejects unverifiable events safely", t_webhook_unverified_without_secret)


def t_fit_gate_blocks_low_fit():
    cands = [{"product": "A", "fit_score": 0.9}, {"product": "B", "fit_score": 0.4},
             {"product": "C", "fit_score": 0.61}, {"product": "D"}]  # D has no score
    kept = gate_affiliate(cands)
    names = {c["product"] for c in kept}
    ok(names == {"A", "C"}, f"only above-threshold products pass, got {names}")
    ok(all(c["fit_score"] >= AFFILIATE_FIT_THRESHOLD for c in kept), "gate enforced")
test("affiliate fit-gate blocks under-threshold products at write time", t_fit_gate_blocks_low_fit)


def t_affiliate_endpoint_gated_and_disclosed():
    H = _auth("bill3@x.com")
    r = client.get("/v1/discover", headers=H)
    ok(r.status_code == 200, r.text)
    ok("disclosure" in r.json(), "affiliate disclosure always present")
    ok(isinstance(r.json()["recommendations"], list), "returns a (gated) list")
test("affiliate endpoint always carries a disclosure and a gated list", t_affiliate_endpoint_gated_and_disclosed)


if __name__ == "__main__":
    print("\nSylia billing + affiliate\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
