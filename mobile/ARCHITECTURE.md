# Aura — Architecture & Build Plan

This is how the design becomes a shippable app. It's opinionated on purpose; every choice is justified against the product's one hard constraint — **10 seconds to a wearable look, offline-capable, grounded in owned inventory.**

---

## 1. The stack (and why)

| Layer | Choice | Why this and not the alternative |
|---|---|---|
| **App** | Expo (React Native) + TypeScript, expo-router | One codebase for iOS-primary/Android-secondary. Expo gives us OTA updates, EAS builds, and native modules without ejecting. Router = file-based nav, less boilerplate than bare React Navigation. |
| **State** | Zustand + MMKV persistence | The store is the **local source of truth**. Zustand is 1KB, no boilerplate, and selectors keep Today re-renders cheap. MMKV is synchronous and ~30× faster than AsyncStorage — matters for the ≤800ms cold-launch budget. |
| **Generation** | Client-side rule engine (pure TS), server upgrade path | The engine already works (see `src/domain/engine`). Running it on-device means Today renders with **zero network latency** and works on the subway. A server model can later re-rank; the client engine is the floor, never removed. |
| **Backend** | Supabase (Postgres + Auth + Storage + Edge Functions) | Fastest credible backend for a small team: managed auth, row-level security, S3-style storage, and Deno edge functions for the heavier generation/tagging. Swap-able — everything goes through `src/data/api` repositories, so Postgres → your own API is a one-file change. |
| **Images** | Supabase Storage + `expo-image` cache | Cut-outs and composites are just files. `expo-image` gives disk+memory caching and blurhash placeholders for the skeleton states. |
| **ML — segmentation** | On-device: VisionKit (iOS) / ML Kit Subject Segmentation (Android) via a thin native module | Background removal must be instant and private (spec promise: "processed on device"). No server round-trip for the closet-building flow, which is the make-or-break funnel. |
| **ML — auto-tagging** | Hosted vision model (Edge Function → Replicate/OpenAI vision or a fine-tuned CLIP), cached | Tagging tolerates ~1s latency and benefits from a bigger model. Runs async after capture, drains the tagging queue. Confidence returned per tag drives the dotted/solid convention. |
| **Analytics** | PostHog (self-host or cloud) | Product analytics + feature flags + session replay in one. Instrument the six events from spec §8.4. |
| **Payments** | RevenueCat | Wraps StoreKit/Play Billing, handles the trial + restore logic so the paywall UX rules are enforceable without server plumbing. |

**Not chosen, deliberately:** Redux (too heavy), Firebase (worse relational modelling for the wardrobe graph), a bespoke Node backend on day one (Supabase gets us to alpha faster; graduate later if scale demands).

---

## 2. System shape

```
┌─────────────────────────── DEVICE ───────────────────────────┐
│                                                               │
│  app/ (expo-router)   thin route files, compose features      │
│         │                                                     │
│  src/features/*       screen logic + hooks (useToday, etc.)   │
│         │                                                     │
│  ┌──────┴───────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │ src/design   │   │ src/data     │   │ src/domain       │  │
│  │ tokens +     │   │ Zustand store│──▶│ engine (pure TS) │  │
│  │ primitives   │   │ (MMKV persist)│  │ types, garments  │  │
│  └──────────────┘   └──────┬───────┘   └──────────────────┘  │
│                            │  offline-first: store is truth   │
│  src/ml (segment/tag) ─────┤                                  │
│                            │ sync (push/pull when online)     │
└────────────────────────────┼─────────────────────────────────┘
                             ▼
┌─────────────────────── SUPABASE ─────────────────────────────┐
│  Auth  │  Postgres (RLS)  │  Storage (images)  │ Edge Funcs   │
│                            garments, outfits,    - tag-garment │
│                            wear_events, signals   - generate*  │
└──────────────────────────────────────────────────────────────┘
  * server generation is an optional re-ranker; client engine is the floor
```

**Data flow, the important paths:**

- **Cold launch → Today:** store hydrates from MMKV (sync, <50ms) → `useToday` reads today's cached Drop → renders. No await on network. A background `sync.pull()` reconciles.
- **Add a garment:** capture → on-device segment → optimistic insert into store (status `processing`) → upload image + enqueue `tag-garment` edge function → tags return with confidence → store updates → tagging queue drains.
- **Generate a look:** `useGenerator` calls `engine.generate(items, opts)` **locally**, instantly. If online and the user is Pro, it *also* fires the server re-ranker and swaps in the improved order when it returns (never blocking).
- **Wear:** optimistic store mutation (count++, streak, CPW) → `sync.push()` appends a `wear_event`. Undo pops both.

---

## 3. Module boundaries (the repo)

```
aura/
├── app/                          # ROUTES ONLY — thin, compose a feature
│   ├── _layout.tsx               # theme provider, store hydration, font load
│   ├── (tabs)/_layout.tsx        # tab bar + docked orb
│   ├── (tabs)/today.tsx
│   ├── (tabs)/closet.tsx
│   ├── (tabs)/discover.tsx
│   ├── (tabs)/you.tsx
│   ├── item/[id].tsx
│   ├── add.tsx
│   └── onboarding/index.tsx
│
├── src/
│   ├── design/                   # THE DESIGN SYSTEM (no business logic)
│   │   ├── tokens.ts             # single source of truth (mirrors aura.tokens.ts)
│   │   ├── theme.tsx             # ThemeProvider, useTheme, light/dark
│   │   └── components/           # Button, Chip, Card, Sheet, Orb, Reason…
│   │
│   ├── domain/                   # PURE LOGIC — zero React, 100% testable
│   │   ├── types.ts              # Garment, Outfit, Slot, GenerateOptions…
│   │   ├── garments.ts           # TYPES + COLORS registries
│   │   └── engine/
│   │       ├── harmony.ts        # colour-harmony scoring
│   │       ├── reason.ts         # reason-string generation
│   │       ├── generate.ts       # the outfit composer
│   │       └── generate.test.ts  # the proof
│   │
│   ├── data/                     # PERSISTENCE + REMOTE
│   │   ├── store.ts              # Zustand: items, outfits, wearLog, streak…
│   │   ├── persist.ts            # MMKV storage adapter
│   │   └── api/
│   │       ├── client.ts         # Supabase client (or null → offline-only)
│   │       ├── repo.ts           # Repository interface (swap backends here)
│   │       ├── supabase.repo.ts  # Supabase implementation
│   │       ├── local.repo.ts     # offline-only implementation (runs w/o backend)
│   │       ├── sync.ts           # push/pull reconciliation
│   │       └── schema.sql        # Postgres tables + RLS
│   │
│   ├── art/
│   │   └── garments.tsx          # RN-SVG garment renderers (schematic → photo later)
│   │
│   ├── features/                 # SCREEN COMPOSITION + hooks
│   │   ├── today/                # TodayScreen + useToday
│   │   ├── closet/
│   │   ├── generator/
│   │   ├── item/
│   │   └── onboarding/
│   │
│   └── ml/
│       ├── segment.ts            # background-removal interface + native impl
│       └── tag.ts                # auto-tagging interface (calls edge function)
│
├── app.json  babel.config.js  tsconfig.json  package.json
```

**The rule that keeps this maintainable:** dependencies point inward. `app` → `features` → (`design` + `data` + `domain`). `domain` depends on nothing. `design` depends on nothing but tokens. You can unit-test the entire brain of the app with plain `node`, no simulator.

---

## 4. Data model (Postgres, mirrors the store)

See `src/data/api/schema.sql` for the full DDL with RLS. Core tables:

- `profiles` — taste vector, fit profile, streak, Pro status.
- `garments` — the wardrobe. Image URLs, category, warmth, formality, colors[], tags jsonb (each `{value, source, confidence}`), status, wear_count, last_worn_at, price.
- `outfits` — garment_ids[], composite_url, reason, context jsonb, source, wear_count.
- `wear_events` — the ground-truth signal. outfit_id, garment_ids[], worn_at, photo_url.
- `style_signals` — wear/save/pass/reason with weights; feeds personalization.
- `style_beliefs` — the human-readable Style Memory rows.

Every table is RLS-scoped to `auth.uid()`. Storage buckets: `garments/`, `composites/`, `wears/`, all private with signed URLs.

---

## 5. Build phases (what ships when)

This maps to spec §8.5 — alpha is phases 1–4.

**Phase 0 — Foundation (in progress).** The tested engine, the persisted store (30 passing tests), the repository seam, design tokens + theme, and the first primitive (`Button`) are built. Remaining: the rest of the primitive library, the expo-router shell, and the Today/Closet screens wired to the store. → *You are here — the risky core is done; the UI port is next.*

**Phase 1 — Inventory.** Camera + on-device segmentation + the tagging queue + edge-function tagging. This is the hard part and everything depends on it.

**Phase 2 — Closet complete.** Item detail, collections, sets, wear ledger.

**Phase 3 — Looks.** Generator sheet, slot-swap (client recomposite), occasion styling, the feedback loop + Style Memory.

**Phase 4 — Accounts + sync.** Supabase auth, the sync layer, cross-device.

**Phase 5 — Commerce.** Discover, affiliate, gap detection.

**Phase 6 — Pro.** RevenueCat paywall, Mirror Mode, Closet Report.

**Alpha = end of Phase 3** on a single device, no account. If closet-building (Phase 1) doesn't feel effortless, nothing downstream matters — so it's the first thing to harden after this foundation.

---

## 6. What actually exists today (verified, not aspirational)

Distinguishing what's built and tested from what's specified is the whole point
of an honest handoff. Ground truth as of this delivery:

**Built and passing tests (the two layers that carry the risk):**
- `src/domain/` — the generation **engine in typed TypeScript**, pure and
  deterministic. `npx tsx src/domain/engine/generate.test.ts` → **22 passed**.
- `src/data/store.ts` — the Zustand + MMKV store: `addGarment`, `confirmTags`,
  `generateLooks`, `wearOutfit` (with undo), `looksLeftToday`/`consumeGeneration`,
  `setStatus`, `seedDemo`. `npx tsx src/data/store.test.ts` → **8 passed**
  (drives the store exactly as a screen would — proves the vertical slice).
- `src/data/persist.ts` — MMKV adapter with an in-memory fallback so the store
  runs under plain node/web/tests.
- `src/data/api/repo.ts` — the repository seam + a local-only implementation, so
  the app runs with zero backend.
- `src/design/tokens.ts` + `theme.tsx` — the full token system + a dark-mode-aware
  provider.
- `src/design/components/Button.tsx` — the first primitive (Reanimated press +
  haptics + variants).
- `src/data/api/schema.sql` — the Postgres schema for Phase 4.

**Total: 30 passing tests across the engine and the store.**

**Specified but NOT yet built** (next up, in order):
- Remaining primitives: `Chip`, `GarmentTile`, `OutfitCard`, `ReasonPill`,
  `AuraOrb`, `Sheet`, `SwatchStrip`, `EmptyState`, `Toast`.
- The Expo `app/` router shell + the screens (Today, Closet, Item, Add, Generator).
- The camera + segmentation flow (Phase 2 — the critical path).
- Everything in Phases 4–7 (backend, feedback/memory, Discover, Pro, wow features).

The working single-file reference (`aura-v1.html`) already demonstrates every one
of those screens and their states, so building each RN screen is a mechanical
port: render store data through primitives, using the layouts and copy already
proven there. The store and engine they plug into are done.
