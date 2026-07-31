# Sylia — Repository Structure & Build Continuation

**Monorepo:** `api/` (backend, built + 68 tests) and `mobile/` (Expo app, wired
to the API). One repo, two deploy targets — the server and the App Store.


The monorepo. Backend is built and tested; the mobile app plugs in against it.

```
sylia/
├── README.md
├── REPO_STRUCTURE.md            ← this file
│
├── api/                         FastAPI modular monolith (BUILT — 19 tests green)
│   ├── app/
│   │   ├── main.py              app factory, router mounting, /health
│   │   ├── config.py            env-driven settings (pydantic-settings)
│   │   ├── db.py                engine + session + Base (PG prod / SQLite dev)
│   │   ├── security.py          bcrypt + JWT access/refresh
│   │   ├── deps.py              get_db, get_current_user
│   │   ├── models/              the 12 tables (spec §2)
│   │   │   ├── user.py          users, subscriptions
│   │   │   ├── profiles.py      identity_profiles, body_profiles
│   │   │   ├── closet.py        clothing_items
│   │   │   ├── outfit.py        outfits, outfit_items
│   │   │   ├── coach.py         coach_conversations, coach_messages
│   │   │   └── integrations.py  calendar_connections, weather_cache, affiliate_recommendations
│   │   ├── schemas/             Pydantic request/response models
│   │   ├── core/jobs.py         job-handle store (202 + poll pattern)
│   │   ├── workers/             Celery app + CV/LLM task stubs
│   │   └── domains/             one module per pillar (routers + logic)
│   │       ├── auth/            §3.1  — FULLY WORKING
│   │       ├── identity/        §3.2  — routes stubbed, Claude extraction TODO
│   │       ├── vision/          §3.3  — job handles + quiz fallback working
│   │       ├── closet/          §3.4  — job handles working, DB queries TODO
│   │       ├── daily_look/      §3.5  — SCORER BUILT + WIRED
│   │       │   ├── scorer.py    pure, deterministic, 10 tests (spec §4.2/§4.3)
│   │       │   ├── service.py   DB rows → scorer → explanation
│   │       │   └── router.py    GET /daily-look, feedback, regenerate
│   │       ├── coach/           §3.6  — routes stubbed, SSE + RAG TODO
│   │       └── billing/         §3.7  — routes stubbed, Stripe TODO
│   ├── tests/
│   │   ├── test_scorer.py       10 tests — `python3 tests/test_scorer.py`
│   │   └── test_api_smoke.py    9 tests  — boots app on SQLite
│   ├── alembic/                 migrations (autogenerate from models)
│   ├── requirements.txt · Dockerfile · docker-compose.yml · .env.example
│
└── mobile/                      Expo app (existing Sylia client — move it here)
    ├── app/                     expo-router screens
    ├── src/                     domain (TS engine = scorer's client twin), design, data
    └── ...                      (see the mobile SETUP.md)
```

## What's done vs. what's next

**Done & tested (33 backend tests):**
- The Alembic migration (12 tables, applies clean) and full closet data layer (CRUD + ownership + worker persistence, 6 tests). The deterministic scorer — the hard, high-value part — ported from the TS engine to the four-subscore spec, with exclusions, context/color/body/identity subscores, novelty-decay, and ranking.
- Auth (signup/login/refresh, JWT, bcrypt), the DB models for all 12 tables, the job-handle pattern for every CV/LLM endpoint, and a bootable app that runs on SQLite with zero infra.

**Next, in dependency order (mirrors the 12-week plan):**
1. ~~Alembic initial migration~~ **DONE** — `alembic/versions/*_initial_schema.py` creates all 12 tables; applies clean; `alembic upgrade head`.
2. ~~Closet DB wiring~~ **DONE** — full DB-backed CRUD (`upload → row → worker persists → list/filter/get/patch/soft-delete`), per-user ownership enforced, 6 tests. Daily-look now reads real closet rows.
3. ~~CV workers (garments)~~ **DONE** — `workers/cv/`: rembg background removal + k-means dominant-colour are **real and verified** (rembg produces a proper RGBA cut-out; a navy image → "navy", rust → "rust"). CLIP zero-shot is written to the real open-clip API with an injectable embedder + heuristic fallback (torch/weights not present in CI → low-confidence fallback fires). 8 CV tests + full worker path verified end to end.
4. **CV workers (body)** — MediaPipe Pose/FaceMesh → silhouette/undertone/palette (`analyze_body` stub).
5. ~~Integrations~~ **DONE** — `app/domains/integrations/` (weather · calendar).
   OpenWeatherMap fetch + `weather_cache` (per location+day, 3h TTL) → scorer
   Context; Google Calendar read-only → the single formality signal (most formal
   event wins, user keyword-mapping overrides). Both degrade to sensible defaults
   with no API key. **Daily-look now scores against real weather + calendar**
   instead of placeholders and returns the resolved context. 7 tests.
6. ~~Identity engine~~ **DONE** — `app/domains/identity/` (schema · extractor · router).
   Text-first conversational onboarding with progressive unlock: each turn
   extracts structured fields (aspirations/insecurities/activity/confidence) and
   asks only what's missing, stopping when required fields are filled. Real
   Anthropic extraction (prompt-cached schema) with a deterministic keyword
   fallback so the whole flow is testable offline. Persists to identity_profiles;
   verified to change the scorer's pick (arms-conscious → avoids sleeveless). 8 tests.
7. ~~Coach~~ **DONE** — `app/domains/coach/` + `app/core/llm.py`. RAG preamble (identity + wardrobe summary + recent outfits), prompt-cached; non-streaming + SSE streaming endpoints; deterministic fallback so it works keyless. 5 tests.
8. ~~Billing~~ **DONE** — `app/domains/billing/service.py`. Stripe checkout (stub without key), webhook as source of truth reconciling subscription_status, time-boxed trial entitlement, and the fit-gated affiliate (gate enforced at write time). 5 tests.
9. ~~Explanation call~~ **DONE** — `service.explain()` now calls Claude (cached preamble, small/fast model) and falls back to the grounded template offline.
10. ~~Production hardening~~ **DONE** — calendar OAuth tokens encrypted at rest (`app/core/crypto.py`, Fernet); `Dockerfile.worker` installs torch/CLIP/MediaPipe and pre-downloads weights so the CV/undertone models activate in the worker with no code change. 3 tests.

## Run it

```bash
cd api
pip install -r requirements.txt      # or just the core for tests
python3 tests/test_scorer.py         # 10 passed
python3 tests/test_api_smoke.py      # 9 passed
uvicorn app.main:app --reload        # http://localhost:8000/docs
# full stack (Postgres + Redis + worker):
docker compose up
```

## Client ↔ server split

The mobile app's TypeScript engine and the backend `scorer.py` are twins of the
same logic. Decision: **the server is authoritative** — the app calls
`GET /v1/daily-look` and renders the returned looks + explanation. The TS engine
stays as an optional offline/instant preview, but the score of record is the
server's. This keeps recommendations consistent across devices and lets the
scorer improve without shipping an app update.


---

## Backend feature-complete (v1.0). Remaining = client + ops.

- **LLM is provider-swappable** — every call routes through `app/core/llm.py`
  (the ONLY file importing a vendor SDK). Switch Anthropic↔OpenAI via
  `LLM_PROVIDER` env; add a provider = one adapter class. Callers ask for a role
  (`model_for('coach')`), never a vendor model id.
- **Expo app wired to the API** — `aura-app/src/data/api/` (config · client ·
  endpoints). Base URL is `EXPO_PUBLIC_API_URL`, the one env var that changes
  between local / TestFlight / prod (see `eas.json`). Verified end-to-end against
  a live backend across every domain.
- **Worker image** — `Dockerfile.worker` installs the CV stack
  (`requirements-worker.txt`) and pre-downloads CLIP/rembg/MediaPipe weights; the
  API image stays small.
- **Setup & deploy** — see `SETUP_AND_DEPLOY.md` (keys, local run, Docker, deploy,
  TestFlight, per-feature testing).
