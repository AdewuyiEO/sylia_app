# Aura — app

The production Expo codebase. See `ARCHITECTURE.md` for the full plan.

## What's here now
- `src/domain/` — pure generation engine (22 tests)
- `src/data/` — Zustand store + MMKV persist + repository seam (8 tests)
- `src/design/` — tokens, theme provider, Button primitive

## Run the tests (no simulator needed)
```
npm install       # or: npm i -D tsx typescript && npm i zustand react
npm test          # runs engine + store suites → 30 passing
```

## Next steps (Phase 0 → alpha)
1. `npx create-expo-app` shell, wire `src/design/tokens.ts` into a ThemeProvider (done).
2. Build remaining primitives: Chip, GarmentTile, OutfitCard, ReasonPill, AuraOrb, Sheet, Toast.
3. Port screens from `aura-v1.html` (layouts + copy final) into `app/` routes,
   rendering `useStore` data through the primitives.
4. Phase 2: camera + on-device segmentation + tagging queue — the critical path.

The engine and store the screens plug into are done and tested.
