# Sylia app — how the screens connect to the backend

## The layering (why redesign is easy)

```
  SCREEN  (app/*.tsx)         ← presentation only: renders 4 states, calls actions
    │  uses
    ▼
  useAsync / auth store       ← state: loading/error/data, login status
    │  calls
    ▼
  api.* (src/data/api/…)      ← typed endpoint functions
    │  via
    ▼
  http client + tokens        ← fetch, auth header, refresh-on-401
    │  →  EXPO_PUBLIC_API_URL  (the one env var that changes per environment)
```

A screen's job is: call an `api.*` function through `useAsync`, then render
**loading / error / empty / data**. It never touches fetch, tokens, or URLs, and
never computes recommendations (the server does). So restyling a screen means
re-rendering those four states differently — the data path underneath is
untouched and already proven.

## Designing later — three paths

1. **Figma → hand it over → reskin.** The API calls and state stay; only the
   presentational components change.
2. **Edit tokens/primitives.** Everything reads `src/design/tokens.ts`; change the
   tokens and every screen restyles at once.
3. **Rebuild a screen yourself.** As long as it calls the same `api.*` functions
   and reads the same stores, it drops in.

## What's wired now
- `app/auth.tsx` → `useAuth` → `api.auth.login/signup`
- `app/_layout.tsx` → auth gate (guest → /auth, authed → /today)
- `app/(tabs)/today.tsx` → `useAsync(api.dailyLook.get)` → renders 4 states
- `src/data/api/` → config · client (tokens, refresh) · endpoints (all domains)
- `src/state/` → auth store · useAsync

## Still to wire (same pattern)
Closet grid → `api.closet.list`; add-item → `api.closet.upload`; onboarding chat →
`api.identity.*`; coach → `api.coach.*`; body quiz → `api.body.quiz`.
