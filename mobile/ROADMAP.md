# Aura — Project Roadmap

The whole arc, from where the code is today to a shipped, growing product. Phases
map to the architecture's build phases but are framed as product milestones with
**gates** — a phase isn't "done" until its gate is met. The gates are what keep the
plan honest.

Sequencing is relative, not calendar-dated (that depends on team size). Effort is
marked S / M / L. The one metric that gates real spend is **WWO — Weekly Worn
Outfits.**

---

## Where we are now

```
   ✅ DONE                    🔨 NEXT                     ⬜ SPECIFIED
   ─────────                  ───────                     ───────────
   Design system (tokens)     Primitive library          Camera + segmentation
   Generation engine (22 ✓)   expo-router shell          Occasion styling
   State store (8 ✓)          Today + Closet screens      Backend + sync
   Repository seam            Item detail + Add flow      Discover / shopping
   Full product spec          (wire store → UI)           Pro / paywall
   Working web reference                                  Mirror / Ledger / Twin
```

**30 passing tests** across the two layers that carry the risk. The product is
fully specified and demonstrated (`aura-v1.html`); what remains is largely a
mechanical port plus the one genuinely hard flow (camera).

---

## Milestone 1 — Foundation  *(Phase 0–1)*

**Goal:** the app boots on a device and renders real data through the design
system.

| Work | Effort |
|---|---|
| Remaining primitives: Chip, GarmentTile, OutfitCard, ReasonPill, AuraOrb, Sheet, Toast, EmptyState, SwatchStrip | M |
| expo-router shell: `_layout` + 4-tab nav + docked orb + sheet host | S |
| `generationService` wrapping the tested engine | S |
| Today + Closet screens reading `useStore` | M |

**Gate:** cold launch → a wearable look on screen in ≤ 800ms, on a real device,
with a seeded demo closet. The performance contract is provable.

---

## Milestone 2 — The Closet Loop  *(Phase 2 — the critical path)* ⚠

**Goal:** a stranger can photograph 10 garments in a sitting and it feels effortless.

| Work | Effort |
|---|---|
| Camera: single + batch capture (10-shot tray) | M |
| On-device background removal (VisionKit / ML Kit) + server fallback | L |
| Auto-tagging (hosted vision model) → tagging queue → dotted/solid confirm | L |
| Item detail, wear log, laundry/archive | M |

**Gate:** median time to add 10 items ≤ 90 seconds, and ≥ 70% of AI tags accepted
without edit. **This is the make-or-break milestone** — if closet-building isn't
effortless, nothing downstream matters, so it's hardened first among the screens.

---

## Milestone 3 — The Daily Loop  *(Phase 3)*

**Goal:** the retention engine is live end-to-end.

| Work | Effort |
|---|---|
| Generator sheet (occasion / formality / palette / pins) | M |
| Slot-swap — client-side recomposite, ≤200ms, no quota | M |
| Wear logging → streak → cost-per-wear | S |
| The Aura Drop pre-generation (04:00 background task) | S |
| Onboarding (intro → Fit Check → palette reveal → fit profile) | M |

**Gate:** a new user can onboard, add 5+ items, generate, and log a wear — the full
loop — on one device, offline.

---

## 🚩 ALPHA CUT — end of Milestone 3

A **local-only** app: real inventory, real generation, the wear loop, no account.
Ship to TestFlight / internal testers.

**Alpha success gate (this decides whether we spend on a backend):**
**WWO ≥ 3** among a cohort of ~50 testers over 2+ weeks. If people aren't wearing
what Aura suggests, fix the loop before building anything else. This gate is the
most important decision point in the entire roadmap.

---

## Milestone 4 — Accounts & Sync  *(Phase 4)*

**Goal:** the app is multi-device and durable; the backend is on.

| Work | Effort |
|---|---|
| Supabase auth (Apple / Google / email) | S |
| Apply `schema.sql` + row-level security | S |
| Supabase implementation of the `Repo` interface (one file) | M |
| Optimistic write queue + background sync | M |
| Photo upload to Storage; `rerank` Edge Function (engine stays the floor) | M |

**Gate:** a wear logged on phone A appears on phone B within seconds; the app is
still fully usable in airplane mode.

---

## Milestone 5 — Trust & Intelligence  *(Phase 5)*

**Goal:** the model visibly learns, and the user can steer it.

| Work | Effort |
|---|---|
| Style-signal ingestion (wear 10× / save 3× / pass 1× / reason-chip 4×) | M |
| Style Memory screen — editable belief sentences + evidence | M |
| Calibration meter (honest, can go down) | S |
| Occasion styling with the three-strategy result (Safe / Elevated / A risk) + forecast re-checks | M |

**Gate:** returning users report the looks "feel more like me" (qual), and Style
Memory shows ≥ 5 accurate, user-endorsed beliefs.

---

## 🚩 BETA — after Milestone 5

Open beta with accounts, sync, learning, and occasion styling. Begin measuring
retention (D7/D30) and WWO trend, not just absolute WWO.

---

## Milestone 6 — Commerce  *(Phase 6)*

**Goal:** revenue, without becoming a store.

| Work | Effort |
|---|---|
| Gap analysis ("unlocks N outfits") | M |
| Discover: product cards, "with what you own" preview, weekly edit | M |
| Affiliate integration + permanent disclosure | S |
| Aura Pro: RevenueCat, the meter-not-wall paywall, 7-day trial | M |

**Gate:** free→trial→paid conversion ≥ target, and affiliate CTR that doesn't dent
trust metrics. Pro must never gate the daily look.

---

## Milestone 7 — The Wow Layer  *(Phase 7)*

**Goal:** the shareable, category-defining features that drive word of mouth.

| Work | Effort |
|---|---|
| Mirror Mode (on-device recognition, one suggestion, no body commentary) | L |
| Wear Ledger analytics + seasonal Closet Report (Wrapped-style, shareable) | M |
| Style Twin (anonymised taste-match, opt-in) | L |
| Share artifacts: Look Card, Style DNA, Closet Report → Stories | M |

**Gate:** ≥ X% of active users produce a share per month; Style Twin lifts
discovery conversion without hurting retention.

---

## 🚩 1.0 LAUNCH — after Milestone 7

Public launch. Full loop + accounts + learning + commerce + the three wow features
+ viral share mechanics.

---

## Post-1.0 — Growth & Scale

- **Personalisation depth:** move the server `rerank` from heuristic to a learned
  model; the on-device engine remains the offline floor.
- **Wardrobe intelligence:** seasonal transitions, travel packing lists (Pro),
  proactive "14 items are wrong for this week's weather."
- **Brand edits:** clearly-labelled `PAID` sponsored edits, never merged into
  organic recommendations.
- **Platform:** Android hardening, then a lightweight web view (already the share
  landing surface) as an acquisition funnel.
- **Ecosystem:** iOS widget (today's look on the home screen), Watch glance,
  Shortcuts ("what do I wear").

---

## The critical-path summary

```
Foundation → CLOSET LOOP ⚠ → Daily Loop → [ALPHA · gate: WWO≥3]
   → Accounts/Sync → Trust/Intelligence → [BETA]
   → Commerce → Wow Layer → [1.0 LAUNCH] → Growth
```

Two rules govern the whole roadmap: **(1)** the closet-building flow is the single
riskiest thing — build and prove it before polishing anything downstream; and
**(2)** don't spend on the backend until the local alpha proves people actually
wear what Aura suggests. Everything else is comparatively routine execution.
