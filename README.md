# Sylia

An AI stylist that recommends outfits from the clothes you already own — grounded
in your identity, body, wardrobe, weather, and calendar.

**One repo, two halves:**

- **`api/`** — the backend (FastAPI). All the logic: the outfit scorer, CV
  pipeline, body/undertone analysis, identity extraction, style coach, billing.
  Runs on a server. 68 tests. The recommendation is deterministic; the LLM only
  *explains* a decision the scorer already made (and the LLM is swappable —
  Anthropic/OpenAI via one env var).

- **`mobile/`** — the app (Expo / React Native). The screens users tap, wired to
  the backend through a clean hook layer. Runs on iPhone/Android (Expo Go now,
  TestFlight later).

The two connect through one setting: `EXPO_PUBLIC_API_URL` in `mobile/`.

## Run both together
See **`SETUP_AND_DEPLOY.md`** → "Quickstart — run BOTH together". In short:
backend with `uvicorn app.main:app --host 0.0.0.0 --port 8000`, app with
`npx expo start` after pointing `EXPO_PUBLIC_API_URL` at your computer's IP.

## Docs
- `SETUP_AND_DEPLOY.md` — local run, keys, Docker, deploy, TestFlight, testing
- `REPO_STRUCTURE.md` — full map + build history
