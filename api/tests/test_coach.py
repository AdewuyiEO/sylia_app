"""Coach + explanation tests. No ANTHROPIC_API_KEY here, so the deterministic
fallback path is exercised — proving the RAG context assembly, message
persistence, SSE streaming, and the explanation swap all work offline. With a
key set, the same code paths call Claude. Run: python3 tests/test_coach.py
"""
import sys, os, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine, SessionLocal  # noqa: E402
from app.models import Base, ClothingItem  # noqa: E402
from app.domains.coach.service import build_context_preamble  # noqa: E402
from app.domains.daily_look.service import explain  # noqa: E402
import uuid as _uuid  # noqa: E402

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


def t_explain_template_fallback():
    # no LLM key → deterministic template, but still grounded in the breakdown
    s = explain({"context": 90, "color": 80, "body": 50, "identity": 85})
    ok(isinstance(s, str) and len(s) > 0, "returns a string")
    ok("weather" in s or "palette" in s or "show up" in s, f"grounded in high subscores: {s}")
test("explanation falls back to a grounded template without a key", t_explain_template_fallback)


def t_explain_localised():
    fr = explain({"context": 90, "color": 80, "body": 50, "identity": 40}, locale="fr-FR")
    ok(fr.startswith("Cette tenue") and "palette" in fr, f"French template: {fr}")
    es = explain({"context": 10, "color": 10, "body": 10, "identity": 10}, locale="es")
    ok(es.startswith("Una elección"), f"Spanish default: {es}")
    ok(explain({"context": 90}, locale="xx").startswith("This look"), "unknown locale falls back to English")
test("template explanations follow the user's language", t_explain_localised)


def t_context_preamble_assembles():
    H = _auth("coach1@x.com")
    # give this user a couple of items + an identity so the preamble has content
    client.patch("/v1/identity-profile", headers=H, json={
        "style_aspirations": [{"label": "authoritative", "priority": 1}],
        "insecurities": [{"area": "arms"}],
        "lifestyle_patterns": {"activity_level": "desk"},
        "psychological_traits": {"confidence_baseline": 0.4},
    })
    # find the user id by signing a row directly
    db = SessionLocal()
    from app.models import User
    from sqlalchemy import select
    uid = db.scalar(select(User).where(User.email == "coach1@x.com")).id
    db.add(ClothingItem(user_id=uid, category="top", primary_color="navy", is_active=True))
    db.add(ClothingItem(user_id=uid, category="bottom", primary_color="cream", is_active=True))
    db.commit()
    preamble = build_context_preamble(db, uid)
    db.close()
    ok("authoritative" in preamble, "identity aspiration in preamble")
    ok("Wardrobe summary" in preamble, "wardrobe section present")
    ok("navy" in preamble or "cream" in preamble, "wardrobe colours summarised")
    ok("body" in preamble.lower(), "includes the coach guardrails")
test("coach RAG preamble assembles identity + wardrobe", t_context_preamble_assembles)


def t_conversation_lifecycle():
    H = _auth("coach2@x.com")
    cid = client.post("/v1/coach/conversations", headers=H).json()["conversation_id"]
    ok(cid, "conversation created")
    r = client.post(f"/v1/coach/conversations/{cid}/messages",
                    json={"message": "What should I wear to a client meeting?"}, headers=H)
    ok(r.status_code == 200, r.text)
    ok(len(r.json()["reply"]) > 0, "got a reply (fallback copy without a key)")
    # history now has the user + assistant turns
    hist = client.get(f"/v1/coach/conversations/{cid}", headers=H).json()
    ok(len(hist["messages"]) == 2, f"user + assistant persisted, got {len(hist['messages'])}")
    ok(hist["messages"][0]["role"] == "user", "first message is the user's")
test("coach conversation persists user + assistant turns", t_conversation_lifecycle)


def t_streaming_endpoint():
    H = _auth("coach3@x.com")
    cid = client.post("/v1/coach/conversations", headers=H).json()["conversation_id"]
    with client.stream("POST", f"/v1/coach/conversations/{cid}/messages/stream",
                       json={"message": "help me pack for a 3-day work trip"}, headers=H) as r:
        ok(r.status_code == 200, "stream opens")
        body = "".join(r.iter_text())
    ok("data:" in body, "SSE frames emitted")
    ok("[DONE]" in body, "stream terminates with done event")
    # assistant turn persisted after stream completes
    hist = client.get(f"/v1/coach/conversations/{cid}", headers=H).json()
    ok(any(m["role"] == "assistant" for m in hist["messages"]), "streamed reply persisted")
test("coach SSE streaming emits frames and persists the reply", t_streaming_endpoint)


def t_ownership():
    Ha = _auth("coacha@x.com"); Hb = _auth("coachb@x.com")
    cid = client.post("/v1/coach/conversations", headers=Ha).json()["conversation_id"]
    r = client.get(f"/v1/coach/conversations/{cid}", headers=Hb)
    ok(r.status_code == 404, "another user cannot read the conversation")
test("coach conversations are private to their owner", t_ownership)


if __name__ == "__main__":
    print("\nSylia coach + explanation\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
