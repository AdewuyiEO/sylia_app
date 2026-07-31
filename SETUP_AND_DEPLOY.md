# Sylia — Setup, Keys & Deployment Guide

Everything to go from this repo to a running system: the API + worker + database,
the real API keys, and the Expo app pointed at it (local first, then TestFlight).

Nothing here needs a paid service to *run locally* — every external dependency
degrades gracefully without a key. You add keys to turn features from "templated
fallback" into "live".

---

## The repo — one place, two halves

```
sylia/
├── api/         the backend (FastAPI + worker + DB) — runs on a server
│   ├── app/         endpoints, scorer, CV pipeline, LLM layer, models
│   ├── tests/       68 tests
│   ├── alembic/     database migrations
│   ├── Dockerfile · Dockerfile.worker · docker-compose.yml
│   └── requirements.txt · requirements-worker.txt · .env.example
│
├── mobile/      the app (Expo / React Native) — runs on the phone
│   ├── app/         screens (today, closet, coach, onboarding, you, auth)
│   ├── src/         design system, hooks, the API client
│   ├── eas.json     build profiles (local / TestFlight / prod)
│   └── package.json · .env.example
│
├── SETUP_AND_DEPLOY.md      ← this file
└── REPO_STRUCTURE.md
```

`api/` is the kitchen (all the logic, runs out of sight on a server). `mobile/`
is the dining room (what the user sees). They're connected by exactly one setting
— `EXPO_PUBLIC_API_URL` in `mobile/` — which points the app at wherever `api/` is
running.

---

## Quickstart — run BOTH together (two terminals)

**Terminal 1 — the backend** (from the repo root):
```bash
cd sylia/api
python3 -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000       # --host 0.0.0.0 so your phone can reach it
```

**Terminal 2 — the app:**
```bash
cd sylia/mobile
npm install
# tell the app where the backend is (your computer's LAN IP, not localhost):
echo "EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_IP:8000" > .env
npx expo start                                        # scan the QR with Expo Go
```

Find `YOUR_COMPUTER_IP` with `ipconfig` (Windows) or `ipconfig getifaddr en0`
(mac). Now the app on your phone talks to the backend on your computer — sign up,
onboard, and get a daily look. The detailed, per-piece instructions follow below.

---

## Part A — Run the backend locally (no keys, 5 minutes)

```bash
cd sylia/api
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# create the database schema
alembic upgrade head            # or, for a quick SQLite spin-up, just run the app (dev auto-creates)

# run it
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** — the interactive API. Every endpoint has a
"Try it out" button. Sign up, copy the access token into the "Authorize" box, and
exercise the whole thing by hand. This works with zero keys.

Run the tests any time: `for f in tests/test_*.py; do python3 $f; done` → 68 passing.

---

## Part B — The full stack with Docker (Postgres + Redis + worker)

```bash
cd sylia/api
cp .env.example .env             # then fill in keys (Part C) — optional to start
docker compose up --build
```

This starts four services: **db** (Postgres 16), **redis**, **api** (FastAPI),
and **worker** (Celery, built from `Dockerfile.worker` with the CV models). The
API is on :8000. The worker picks up CV/LLM jobs from Redis.

> The **worker image is large** (torch + CLIP + MediaPipe ≈ 3–4 GB) and
> pre-downloads model weights at build time, so the first `docker compose up
> --build` takes a while. The **api image stays small** — the CV stack lives only
> in `requirements-worker.txt` / `Dockerfile.worker`, never in the API image.

---

## Part C — The API keys (what each unlocks, where to get it)

Add these to `sylia/api/.env`. Each is optional; without it the feature uses a
safe fallback.

| Key | Unlocks | Get it from | Fallback if absent |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Coach replies, outfit explanations, identity extraction | console.anthropic.com → API Keys | Templated copy (deterministic) |
| `OPENWEATHER_API_KEY` | Real weather in the daily look | openweathermap.org/api (free tier) | 68°F / no rain default |
| `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` | Live subscriptions | dashboard.stripe.com → Developers → API keys / Webhooks | Stub checkout URL; trial still works |
| Google OAuth (client id/secret) | Calendar formality signal | console.cloud.google.com → Calendar API + OAuth consent | Neutral formality (3) |
| `ENCRYPTION_KEY` | At-rest encryption of calendar tokens | generate: `python -c "import secrets;print(secrets.token_urlsafe(32))"` | Derives from `JWT_SECRET` (fine for dev) |
| `JWT_SECRET` | Signs auth tokens — **set a strong one in prod** | `python -c "import secrets;print(secrets.token_urlsafe(48))"` | Insecure dev default |

### Switching the LLM provider (Anthropic ↔ OpenAI)

**You are not locked to Anthropic.** Every LLM call goes through one file
(`app/core/llm.py`). To switch:

```bash
# in .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL_COACH=gpt-4o
OPENAI_MODEL_EXPLANATION=gpt-4o-mini
```

No code changes. Adding a third provider (Gemini, a local model, etc.) is one
adapter class in `llm.py` implementing `complete()` / `stream()` + a line in the
`_PROVIDERS` map. Callers ask for a *role* (`model_for('coach')`), never a vendor
model string, so nothing downstream changes.

### Stripe webhook (local testing)

```bash
stripe listen --forward-to localhost:8000/v1/billing/webhook
# copy the printed whsec_... into STRIPE_WEBHOOK_SECRET
```

---

## Part D — Point the Expo app at the backend

The app reads **one** environment variable, `EXPO_PUBLIC_API_URL`. This is the
only thing that changes between local, staging, and TestFlight.

### D1 — Local (Expo Go on your phone)

Your phone isn't your computer, so `localhost` won't reach the API. Use your
computer's LAN IP:

```bash
# find your IP: Windows `ipconfig`, mac/Linux `ipconfig getifaddr en0`
# in sylia/mobile/.env
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000     # ← your computer's IP
```

Then:
```bash
cd sylia/mobile
npm install
npx expo start        # scan the QR with Expo Go
```

Run the API with `--host 0.0.0.0` so the phone can reach it:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### D2 — TestFlight (or any deployed build)

Same app, different URL. Set it in the EAS build profile so the compiled binary
points at your deployed API:

```json
// sylia/mobile/eas.json
{
  "build": {
    "preview": {
      "distribution": "internal",
      "env": { "EXPO_PUBLIC_API_URL": "https://api.sylia.app" }
    },
    "production": {
      "env": { "EXPO_PUBLIC_API_URL": "https://api.sylia.app" }
    }
  }
}
```

**Is this changeable later?** Yes — it's just an env var per build profile. A
local dev build, an internal TestFlight build, and a production build are the same
code with three different `EXPO_PUBLIC_API_URL` values. Change it and rebuild;
nothing in the app code hard-codes a URL.

### D3 — Build for TestFlight from Windows

You can't compile iOS on Windows, so build in Expo's cloud:

```bash
npm install -g eas-cli
eas login
eas build --platform ios --profile preview      # builds on Expo's Macs
eas submit --platform ios                        # uploads to App Store Connect → TestFlight
```

Requires an **Apple Developer account ($99/yr)**. The build URL / TestFlight
invite comes from App Store Connect.

---

## Part E — Deploy the API + worker to production

Any container host works. The shape is always: **API service + worker service +
managed Postgres + managed Redis + object storage**.

### E1 — Managed pieces (pick your provider)
- **Postgres**: Neon, Supabase, or RDS. Copy its connection string →
  `DATABASE_URL=postgresql+psycopg://...`
- **Redis**: Upstash, Redis Cloud, or ElastiCache → `REDIS_URL=redis://...`
- **Object storage**: Cloudflare R2 (cheap egress) or S3 → set `S3_BUCKET` and,
  for R2, `S3_ENDPOINT_URL`.

### E2 — Deploy the two images
```bash
# API image (small)
docker build -t sylia-api -f Dockerfile .
# Worker image (CV stack, large)
docker build -t sylia-worker -f Dockerfile.worker .
```
Push both to your registry and run them on Render / Fly.io / Railway / ECS /
Cloud Run. The API runs `uvicorn app.main:app`; the worker runs the Celery
command baked into `Dockerfile.worker`. Point both at the same `DATABASE_URL`,
`REDIS_URL`, and secrets.

### E3 — Migrate the database
```bash
# one-off, against the prod DATABASE_URL
alembic upgrade head
```

### E4 — Checklist before inviting testers
- [ ] `JWT_SECRET` and `ENCRYPTION_KEY` set to strong random values
- [ ] `ENV=prod` (turns off the dev auto-create-tables; migrations own the schema)
- [ ] CORS locked to your app's origin (add FastAPI CORS middleware in `main.py`)
- [ ] Stripe webhook endpoint registered at `https://your-api/v1/billing/webhook`
- [ ] Worker image deployed and connected to Redis (CV/undertone jobs need it)
- [ ] `EXPO_PUBLIC_API_URL` in the EAS profile points at the deployed API

---

## Part F — How to test each functionality

| Functionality | How to test |
|---|---|
| Any endpoint, no UI | `http://localhost:8000/docs` → Authorize → Try it out |
| Recommendation logic | `python3 tests/test_scorer.py` (10 tests) |
| Whole backend | `for f in tests/test_*.py; do python3 $f; done` (68 tests) |
| CV pipeline (real) | Upload an image via `/docs`, poll the job, check the item's colour/cutout |
| Coach streaming | `curl -N -X POST .../coach/conversations/{id}/messages/stream -d '{"message":"..."}'` |
| The app ↔ API | Run API with `--host 0.0.0.0`, set `EXPO_PUBLIC_API_URL`, `npx expo start`, use Expo Go |
| On a real iPhone | EAS build → TestFlight (Part D3) |

The backend is functionally complete (68 tests). The remaining work is
operational: keys, deploy, and building the app's screens against the typed API
client in `sylia/mobile/src/data/api/`.
