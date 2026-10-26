# Sylia

An AI stylist that picks one outfit a day from the clothes you already own —
grounded in how you want to come across, your shape and colouring, the weather,
and your calendar — and only ever suggests buying something when it genuinely
completes your closet.

- **`api/`** — FastAPI backend: the deterministic outfit scorer, CV pipeline,
  body/undertone analysis, identity onboarding, style coach, wear tracking,
  in-app billing, and the brand platform (catalog, closet-gap Discover,
  partner API, k-anonymous insights). 102 tests.
- **`mobile/`** — Expo app (iOS-first), on the Olive Grove / Earth Riches design
  system, in English, French and Spanish.

The recommendation is deterministic; the LLM only *explains* a decision the
scorer already made ("Claude explains, never chooses").

## Docs

- `SETUP_AND_DEPLOY.md` — run locally, keys, deploy (Render + R2), TestFlight,
  subscriptions, brand onboarding
- `REPO_STRUCTURE.md` — code map and what is real / stubbed / unverified
- `mobile/README.md` — app structure and conventions
