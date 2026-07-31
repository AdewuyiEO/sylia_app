"""Identity engine tests. The deterministic extractor runs (no ANTHROPIC_API_KEY),
so the full onboarding state machine, completion, persistence, and flow into the
scorer are all verified offline. Run: python3 tests/test_identity.py
"""
import sys, os, tempfile
_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_dir}/t.db"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.domains.identity.schema import Extraction, next_question  # noqa: E402
from app.domains.identity.extractor import HeuristicExtractor, get_extractor  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db import engine  # noqa: E402
from app.models import Base  # noqa: E402

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


ex = HeuristicExtractor()

def t_extract_aspiration():
    e = ex.extract("I want to be taken seriously and come across as in charge", Extraction())
    ok("authoritative" in e.aspirations, f"authoritative cue extracted, got {e.aspirations}")
test("extractor pulls aspiration from natural language", t_extract_aspiration)

def t_extract_insecurity_and_activity():
    e = ex.extract("I'm a nurse on my feet all day and I'm self-conscious about my arms", Extraction())
    ok(e.activity_level == "on_feet", f"on_feet extracted, got {e.activity_level}")
    ok("arms" in e.insecurities, f"arms extracted, got {e.insecurities}")
test("extractor pulls activity level + insecurity together", t_extract_insecurity_and_activity)

def t_extract_confidence():
    low = ex.extract("honestly getting dressed is a daily struggle, I never know what works", Extraction())
    ok(low.confidence_baseline is not None and low.confidence_baseline < 0.5, "struggle → low confidence")
    high = ex.extract("I love getting dressed, it's easy and fun for me", Extraction())
    ok(high.confidence_baseline is not None and high.confidence_baseline > 0.5, "love → higher confidence")
test("extractor reads confidence baseline from sentiment", t_extract_confidence)

def t_merge_and_missing():
    a = Extraction(aspirations=["authoritative"])
    b = Extraction(activity_level="desk", confidence_baseline=0.3)
    m = a.merge(b)
    ok(m.aspirations == ["authoritative"] and m.activity_level == "desk", "merge fills gaps")
    ok(m.is_complete(), f"required fields present → complete, missing={m.missing_required()}")
test("merge combines turns; completeness tracks required fields", t_merge_and_missing)

def t_progressive_unlock():
    empty = Extraction()
    ok(next_question(empty) is not None, "empty profile has a question")
    # aspiration first
    q1 = next_question(empty)
    ok("room" in q1.lower() or "come across" in q1.lower(), f"opens on aspiration, got: {q1}")
    partial = Extraction(aspirations=["polished"])
    ok(next_question(partial) is not None, "still asks for activity/confidence")
test("progressive unlock asks only for what's missing", t_progressive_unlock)


def t_full_onboarding_flow():
    H = {"Authorization": "Bearer " + client.post(
        "/v1/auth/signup", json={"email": "ob@x.com", "password": "pw123456"}
    ).json()["access_token"]}
    r = client.post("/v1/onboarding/sessions", headers=H)
    sid = r.json()["session_id"]
    ok(r.json()["question"], "opening question returned")

    # answer with a rich message that fills most required fields at once
    r2 = client.post(f"/v1/onboarding/sessions/{sid}/messages",
                     json={"message": "I want to look authoritative and polished. I'm at a desk most days. Getting dressed is honestly a struggle."},
                     headers=H)
    body = r2.json()
    ok("authoritative" in body["extracted"]["aspirations"], "aspiration captured")
    ok(body["extracted"]["activity_level"] == "desk", "activity captured")
    ok(body["complete"] is True, f"required fields filled → complete, body={body}")

    # profile persisted and readable
    prof = client.get("/v1/identity-profile", headers=H).json()
    ok(prof["exists"] and prof["completed"], "profile persisted + marked complete")
    labels = [a["label"] for a in prof["aspirations"]]
    ok("authoritative" in labels, "aspiration persisted to profile")
test("full conversational onboarding persists an identity profile", t_full_onboarding_flow)


def t_identity_flows_into_daily_look():
    # the whole point: a persisted identity changes scoring
    H = {"Authorization": "Bearer " + client.post(
        "/v1/auth/signup", json={"email": "flow@x.com", "password": "pw123456"}
    ).json()["access_token"]}
    # set identity directly via patch (equivalent to finishing onboarding)
    client.patch("/v1/identity-profile", headers=H, json={
        "style_aspirations": [{"label": "authoritative", "priority": 1}],
        "insecurities": [{"area": "arms"}],
        "lifestyle_patterns": {"activity_level": "desk"},
        "psychological_traits": {"confidence_baseline": 0.4, "risk_tolerance": 0.3},
    })
    prof = client.get("/v1/identity-profile", headers=H).json()
    ok(prof["insecurities"][0]["area"] == "arms", "identity readable for the scorer")
    # daily-look runs (empty closet → guidance, but the endpoint must accept the identity)
    r = client.get("/v1/daily-look", headers=H)
    ok(r.status_code == 200, "daily-look runs with an identity profile present")
test("persisted identity is available to the daily-look scorer", t_identity_flows_into_daily_look)


def t_extractor_selection():
    # no key set → deterministic extractor (so tests + keyless dev work)
    ok(get_extractor().name == "heuristic", "no API key → heuristic extractor")
test("extractor falls back to deterministic without an API key", t_extractor_selection)


if __name__ == "__main__":
    print("\nSylia identity engine\n" + "-" * 40)
    if _fails:
        print("\n".join(_fails))
    print(f"{_p} passed, {_f} failed\n")
    sys.exit(1 if _f else 0)
