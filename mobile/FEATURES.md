# Aura — Features & Differentiation

Two questions answered plainly: **what the product does today**, and **what makes
it distinct in a crowded "AI stylist" market**. The market is full of shopping
funnels dressed as stylists and inspiration feeds that recommend clothes people
never wear. Aura is neither. The distinction is structural, not cosmetic.

---

## Part A — What Aura does today

Everything here is demonstrated in the working reference build (`aura-v1.html`)
and, for the two core layers, implemented as tested production code
(`src/domain`, `src/data` — 30 passing tests).

### Working now

| Feature | State | Notes |
|---|---|---|
| **Taste onboarding** | Working | 3 intro panels → an 8-card "Fit Check" swipe → a starting palette *generated from the cards you liked* → editable style axes. Under 4 minutes to a taste model. |
| **Add clothes → auto-tag → persist** | Working | Pick garment type + colour (stands in for photograph-and-segment); item lands in the closet with AI-guessed tags and persists across sessions. |
| **Digital closet** | Working | Cut-out grid on a neutral ground, category filters, and a dot marking items with unconfirmed tags. |
| **Item detail** | Working | Wear count, **cost-per-wear** that drops as you wear it, a 52-week wear sparkline, the dotted→solid tag-confirmation convention, and a live "Works with" rail. |
| **Today (the daily look)** | Working | Generates a **real outfit from your actual inventory** using weather + formality + colour-harmony rules — not a canned image. Ships with a plain-English reason. Change the weather or put items in the wash and the look changes. |
| **Outfit generator** | Working | The orb opens a sheet: set occasion / formality / palette, watch the staged loader, get 3 real looks you can page through, wear, or save. Free-look quota meter. |
| **Wear logging loop** | Working | "Wearing this" bumps wear counts, advances a streak, updates cost-per-wear, and offers Undo. This is the signal the whole model learns from. |
| **Style DNA + stats** | Working | Shareable identity card (palette + axis words), plus worn count, closet CPW, and % of closet actually worn. |
| **Local-first persistence** | Working | Everything survives a reload. No account, no network needed. |
| **The generation engine** | Production TS | Pure, deterministic, 22 tests. On-device floor — makes Today instant and offline-capable. |
| **The state store** | Production TS | Zustand + MMKV, 8 integration tests. The local source of truth. |

### Specified & demonstrated, not yet coded in RN

Camera + on-device background removal, the occasion-styling flow, live shopping in
Discover, the Pro paywall, backend sync, and the editable Style-Memory surface are
all designed and shown in the reference build — they're the build backlog, not
open questions.

---

## Part B — What makes Aura distinct

The differentiators fall into two tiers: **structural moats** (design decisions
baked into how the product works, hard for a competitor to copy without rebuilding)
and the **three "wow" features** (the things users show their friends).

### Tier 1 — Structural moats

**1. It styles from what you *own*, not a catalogue.**
Most "AI stylists" are shopping funnels or Pinterest boards. Aura's every
recommendation is composed from your real wardrobe. Shopping only ever appears as
"this unlocks N outfits you can't currently make." This is the core wedge and it
reframes the entire value proposition from *inspiration* to *decision-removal*.

**2. Wear is the ground truth — not likes or saves.**
A logged wear counts 10× more than a save and 10× more than a swipe. Every other
styling app optimises on aspirational signals (what you saved, what you liked),
which is exactly why they recommend clothes you never put on. Aura optimises on
what you *actually wore*, so its recommendations converge on your real life. The
whole app is engineered to make logging a wear a single tap.

**3. The model is readable and editable.**
Style Memory shows what Aura has learned as plain sentences — "you wear trainers
to work," "you avoid yellow near your face" — each with its evidence, each
deletable. No competitor exposes its model this way. It's the answer to "why
should I trust it," and it's worth more than any accuracy bump.

**4. Every AI output has a reason, and guessed ≠ confirmed.**
No look ships without a concrete, evidence-based reason ("linen keeps you cool and
it's 31°C today"). AI-guessed values wear a dotted underline; confirmed ones are
solid. Trust is calibrated visually, everywhere, without a single paragraph of
explanation.

**5. Bodies are described, never graded.**
No "flattering," no "for your shape," no before/after. Aura collects fit
preferences and never ranks a body. For a fashion-anxious Gen-Z audience this is a
values position *and* a market position competitors built on body-typing can't
easily follow.

**6. Instant, offline, local-first.**
The ten-second-to-a-look contract: the store is the source of truth and Today
never awaits the network. The engine runs on-device. Users feel this as an app
that's simply faster than everything else in the category.

**7. No public feed, no follower counts, no likes on people.**
The social layer is about clothes, not status. This is a deliberate positioning
moat: the same audience that finds Instagram exhausting will keep Aura installed.

### Tier 2 — The three "wow" features (the shareable hooks)

**① Mirror Mode** *(Pro)* — Point the phone at yourself in a mirror. Aura
recognises which of *your* catalogued garments you're wearing and gives one line
of feedback plus exactly one suggested swap. Every competitor operates *before* or
*after* dressing; this happens *during* — and it produces the best wear data in the
industry (a photo of what was genuinely worn).

**② The Wear Ledger** — cost-per-wear as a running receipt. Every wear updates a
per-item figure and a closet-wide utilisation %. "That jacket's down to €4.10 a
wear — your best buy this year." It turns a styling app into a quiet anti-waste and
financial tool, gives users a reason to log wears (the number moves), and is the
single most screenshot-able thing the app produces.

**③ Style Twin** — match with anonymised users whose *taste* is close but whose
*wardrobe* differs: "someone with your taste owns this jacket and wears it 4× a
month." It solves cold-start and discovery at once, gives inventory-grounded
shopping recommendations far better than a catalogue, and creates social value
*without* the comparison anxiety of a feed. Anonymous, opt-in, off by default.

---

## Part C — Positioning in one line

> Others show you clothes to buy or looks to envy. **Aura tells you what to wear,
> from what you already own, in ten seconds — and gets smarter every time you get
> dressed.**

The north-star metric follows directly: **Weekly Worn Outfits** — outfits logged
as actually worn, per user per week. If that number climbs, the product is working;
every feature above is in service of it.
