# Sylia — Setup, Keys & Deployment

Everything runs locally with **zero keys**: no key means a sensible fallback
(templated copy, default weather, trial-only billing). Keys only switch the
fallbacks to live services. Commands are for Windows + Git Bash.

```
sylia/
├── api/      FastAPI backend (scorer, CV, coach, billing, brand platform)
├── mobile/   Expo app (iOS-first)
└── render.yaml   one-click backend deploy (API + Postgres)
```

---

## 1. Run the backend locally

```bash
cd api
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env            # then edit PUBLIC_BASE_URL (see below)
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Interactive API docs: http://localhost:8000/docs
- `DATABASE_URL` defaults to a local SQLite file; Postgres works unchanged.
- No Redis needed: background jobs run inline when no broker is reachable.
- **`PUBLIC_BASE_URL`** must be the address your phone uses to reach your PC
  (`http://<PC-LAN-IP>:8000`, find the IP with `ipconfig`). Photo uploads and
  calendar sign-in redirect through it.

Tests (stdlib harness, no infra):

```bash
cd api && for t in tests/test_*.py; do .venv/Scripts/python $t; done
```

Full stack with Postgres + Redis + the CV worker: `docker compose up --build`
inside `api/` (first build is large — it pre-downloads CLIP/rembg weights).

---

## 2. The keys

| Key | Unlocks | Without it |
|---|---|---|
| `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` + `LLM_PROVIDER=openai`) | coach replies, look explanations, onboarding extraction | templated copy (en/fr/es) |
| `OPENWEATHER_API_KEY` | real weather | 20 °C / dry |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | calendar formality signal | neutral formality |
| `REVENUECAT_WEBHOOK_SECRET` | App Store / Play purchases → Pro | trial only |
| `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` | web checkout | stub URL |
| `S3_BUCKET`, `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | photo storage in prod (Cloudflare R2) | local folder (dev only) |
| `JWT_SECRET`, `ENCRYPTION_KEY`, `ADMIN_TOKEN` | auth signing, token encryption, brand onboarding | dev defaults (prod refuses to start with the default JWT secret) |

**Google Calendar:** in Google Cloud Console create an OAuth *Web* client, add
`<PUBLIC_BASE_URL>/v1/integrations/calendar/oauth/callback` as an authorised
redirect URI, enable the Calendar API, and put the id/secret in the env.

---

## 3. Deploy the backend (needed before TestFlight)

TestFlight builds can't reach a PC on your Wi-Fi, so the API needs a public
HTTPS URL. Recommended: **Render + Cloudflare R2** (both have free/cheap tiers).

1. **R2 bucket** — Cloudflare dashboard → R2 → create bucket `sylia-photos`;
   create an API token with read/write on it. Note the account endpoint
   `https://<account-id>.r2.cloudflarestorage.com`.
2. **Render** — dashboard → New → Blueprint → pick this GitHub repo. It reads
   `render.yaml` and creates the API (Docker, runs migrations on start) and a
   Postgres database. Generated secrets (`JWT_SECRET`, `ENCRYPTION_KEY`,
   `ADMIN_TOKEN`) are filled for you.
3. Fill the `sync: false` values in the Render dashboard: `PUBLIC_BASE_URL`
   (the service's `https://…onrender.com` URL), the R2 values, and any keys
   from section 2 you have.
4. Check `https://<your-service>.onrender.com/health` returns `ok`.

The CV pipeline runs inside the API process on this setup (colour and tags
work; background removal and CLIP classification need the separate worker
image — section 6).

---

## 4. Build for TestFlight (from Windows, no Mac)

Prerequisites: Apple Developer Program membership (active), `npm i -g eas-cli`,
`eas login`.

1. Put the API URL in `mobile/eas.json` → `build.production.env.EXPO_PUBLIC_API_URL`
   (replace `https://api.sylia.app` with your Render URL or your own domain).
2. In App Store Connect create the app with bundle id `com.sylia.stylist`.
3. Build and upload:

   ```bash
   cd mobile
   eas build --platform ios --profile production
   eas submit --platform ios --latest
   ```

   EAS asks for your Apple ID on the first build and manages certificates and
   provisioning for you (including the Sign in with Apple capability).
4. In App Store Connect → TestFlight, add yourself as an internal tester.

### In-app subscriptions (when you're ready to charge)

1. App Store Connect → the app → Subscriptions: create a group and a monthly
   product (e.g. `sylia_pro_monthly`), price it per country, add a 7-day
   free-trial introductory offer.
2. RevenueCat: create a project, add the iOS app, import the product, create an
   entitlement **`pro`** and attach the product, make it the current offering.
3. RevenueCat → Integrations → Webhooks: URL
   `https://<api>/v1/billing/revenuecat/webhook`, Authorization header = a
   long random string; put the same string in `REVENUECAT_WEBHOOK_SECRET`.
4. Put the RevenueCat **public iOS SDK key** in `eas.json` →
   `EXPO_PUBLIC_REVENUECAT_IOS_KEY`, then rebuild.

Until then the paywall says subscriptions open soon and the server-side trial
keeps Pro features on.

### Before external testers / App Review

- Privacy Policy and Terms URLs live (`EXPO_PUBLIC_PRIVACY_URL`, `EXPO_PUBLIC_TERMS_URL`).
- App Store privacy "nutrition label" matches `app.json → ios.privacyManifests`
  (email, name, photos, coarse location, purchases, user content, product
  interaction — none used for tracking).
- Review notes: explain body photos are optional, consented, and deleted after
  analysis; provide a demo account.
- Account deletion is in Settings (required by Apple).

---

## 5. Onboard a brand

```bash
curl -X POST https://<api>/v1/admin/brands \
  -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"slug":"maison","name":"Maison","regions":["FR","GB","US"],"commission_bps":800}'
```

The response contains the brand's **partner key** (shown once). The brand then
syncs its catalog with `PUT /v1/partner/products` (up to 500 per call, same
garment vocabulary as the closet, per-country prices) and reads aggregated,
k-anonymous performance from `GET /v1/partner/insights`. Full schema at `/docs`.

---

## 6. Later: separate CV worker

For background removal (rembg) and CLIP classification, run `Dockerfile.worker`
with the same env plus a Redis (`REDIS_URL`) and set `REQUIRE_REDIS=true` on
both API and worker. Without it, items get colour + a "needs review" tag and
users confirm the category — which is also the training data for a better
classifier later.
