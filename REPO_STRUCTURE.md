# Sylia — Code Map & Status

```
sylia/
├── render.yaml                    backend deploy blueprint (API + Postgres)
├── api/
│   ├── app/
│   │   ├── main.py                app, routers, CORS, prod secret guard
│   │   ├── config.py              every setting (see .env.example)
│   │   ├── core/                  kv (Redis|memory) · jobs · storage (S3/R2|local,
│   │   │                          signed URLs) · llm (provider-swappable) · crypto · ratelimit
│   │   ├── models/                users, subscriptions, revoked_tokens, profiles,
│   │   │                          clothing_items, outfits, coach, integrations, brands, products
│   │   ├── workers/               Celery app (inline when no broker) + CV/body tasks
│   │   └── domains/
│   │       ├── auth/              email + Sign in with Apple, rotating refresh tokens
│   │       ├── account/           /v1/me profile + region, export, delete
│   │       ├── uploads/           signed photo uploads, per-user key namespace
│   │       ├── identity/          text-first onboarding (LLM or heuristic extractor)
│   │       ├── vision/            body scan (consent, photos deleted) + quiz
│   │       ├── closet/            items, CV pipeline (rembg / CLIP / k-means)
│   │       ├── daily_look/        scorer.py (pure) · service · persisted looks,
│   │       │                      wear feedback, swaps, history, WWO stats
│   │       ├── coach/             RAG preamble, SSE, Pro-gated
│   │       ├── integrations/      weather (°C/°F), Google Calendar OAuth
│   │       ├── billing/           RevenueCat (App Store/Play) + Stripe (web)
│   │       └── catalog/           gap.py (closet-gap analysis) · Discover ·
│   │                              partner API · insights · admin onboarding
│   ├── alembic/versions/          09ab1b5b08dc (initial) → 5087b8d17272
│   └── tests/                     13 files, stdlib harness, no infra
└── mobile/                        see mobile/README.md
```

## Real / stubbed / unverified

**Real and tested** (102 backend tests + a live-server HTTP journey):
scorer incl. coverage preference and swap exclusions; auth hardening
(password policy, rotation, revocation, rate limit, Apple token verification
against a local key); uploads with ownership checks; body-photo deletion;
persisted daily looks, wear logging, novelty-decay feed, WWO/streak stats;
account export/deletion; RevenueCat + Stripe webhook entitlement; brand
onboarding, catalog sync, closet-gap Discover with fit gate, regional
availability/pricing, click tracking, add-bought-item, k-anonymous insights;
calendar OAuth callback (Google token exchange mocked); en/fr/es templates.
Mobile: typechecks clean, iOS JS bundle builds, every client route exists on
the server.

**Real code, not exercised against live services:** Anthropic/OpenAI calls;
OpenWeatherMap; Google OAuth with real Google; Apple's real JWKS; RevenueCat
and App Store purchases; S3/R2 presigned URLs; Postgres (migration verified on
SQLite only); CLIP/rembg/MediaPipe on real photos; the worker image.

**Not run on a device yet:** the whole mobile app (native modules —
camera, Keychain, Apple sign-in, purchases — need the EAS/TestFlight build).

**Known gaps:** accessories never appear in looks (scorer has no accessory
slot); Discover analyses up to 300 products per request (~4 s first load, then
cached 6 h) — move to a nightly precompute at scale; no push notifications;
no analytics pipeline beyond server-side wear/click data; legal pages
(privacy/terms) must be written and hosted.
