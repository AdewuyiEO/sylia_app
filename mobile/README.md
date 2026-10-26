# Sylia — mobile app

Expo SDK 57 / React Native 0.86, expo-router, TypeScript. iOS first.

```
app/            screens (file-based routes)
  (tabs)/       Today · Closet · Coach · Discover · You
  auth, onboarding, body, capture, item/[id], settings, paywall
src/
  data/api/     config (base URL), client (Keychain tokens, refresh), endpoints
  data/purchases.ts   RevenueCat wrapper (no-op without a key)
  state/        hooks — screens get data only through these
  design/       tokens (Olive Grove / Earth Riches / Ember), theme, components
  i18n/         en (source), fr, es — device language, English fallback
  lib/          formatting (units, currency, dates), device (location, photos)
```

Rules: screens render loading / error / empty / data from a hook and never
call `fetch`; colours and type come from tokens; one ember (action) element per
screen.

```bash
npm install
npm run typecheck
npx expo start            # needs a dev build or simulator (native modules)
```

Environment (`.env` locally, `eas.json` per build profile):
`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_REVENUECAT_IOS_KEY`,
`EXPO_PUBLIC_PRIVACY_URL`, `EXPO_PUBLIC_TERMS_URL`.

Building for TestFlight: see `../SETUP_AND_DEPLOY.md` §4.
