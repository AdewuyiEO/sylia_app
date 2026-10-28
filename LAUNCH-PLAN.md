# Sylia — launch plan: VPS → TestFlight → App Store & Google Play

Everything needed to go live, in order, with every cost. Prices were checked in
October 2026 from public pricing pages and trackers. They change, so confirm the
price at checkout. "You" = steps only you can do (accounts, payments, passwords,
legal). "Claude" = what I do in the code once you give me the result.

---

## 1. Every cost, in one table

| Item | Where | Cost | How often | Needed for |
|---|---|---|---|---|
| Apple Developer Program | developer.apple.com | **$99** | yearly | TestFlight + App Store *(already paid)* |
| Domain, e.g. `getsylia.com` | Cloudflare Registrar | **~$10.50** (.com) · ~$14.20 (.app) | yearly | API address, website, privacy policy, email |
| VPS, Hetzner **CX23** (2 vCPU, 4 GB RAM, 40 GB disk) | hetzner.com/cloud | **~€6** (€5.49 + €0.50 IPv4) | monthly | the whole backend |
| Hetzner automatic backups | Hetzner panel, tick "Backups" | **~€1.20** (20% of server price) | monthly | protection if the server dies |
| Expo EAS builds | expo.dev | **$0** (free plan: up to 15 iOS + 15 Android builds a month) | monthly | building the app |
| Claude API (style explanations, coach) | console.anthropic.com | **pay as you go**: about $0.05–0.30 per active user per month (estimate) | usage | "Why this look", coach |
| Prepaid Claude API credit to start | console.anthropic.com | **$5–10** | once, then top up | |
| Weather | openweathermap.org | **$0** (free tier) | — | weather-aware looks |
| RevenueCat (subscriptions) | revenuecat.com | **$0** until about $2,500 monthly revenue, then about 1% | usage | Sylia Pro payments |
| Apple's cut of subscriptions | App Store | **15%** with the Small Business Program (else 30%) | per sale | — |
| Google Play developer account | play.google.com/console | **$25** | once | Android |
| Google's cut of subscriptions | Play | **15%** on subscriptions | per sale | — |
| Website + privacy policy hosting | Cloudflare Pages | **$0** | — | required by both stores |
| Support email (`hello@yourdomain`) | Cloudflare Email Routing | **$0** (forwards to your Gmail) | — | store listing contact |
| Uptime monitoring | uptimerobot.com | **$0** | — | alerts if the API goes down |

### Totals

| Stage | Up front | Then monthly |
|---|---|---|
| **TestFlight** (iOS testing) | domain ~$10.50 + $5–10 API credit | **~€7 VPS** + a few $ of Claude API |
| **App Store launch** | nothing extra | same, rising with users (Claude API usage) |
| **Google Play launch** | $25 once | same |
| **First year, all in** (excluding the Apple fee you already paid) | **≈ $45** | **≈ $10–15 a month** until you have real traffic |

Optional, later: registered company (needed only for a Google Play
*organization* account or for selling as a business; cost depends on country),
trademark for "Sylia", a paid Expo plan for faster builds ($19/month).

---

## 2. Decisions to make first

1. **Domain name.** `sylia.app` and `sylia.com` are **already taken**. These
   appeared available on 28 Oct 2026; confirm at checkout:
   **`getsylia.com`** (recommended: cheap, familiar), `heysylia.com`,
   `trysylia.app`, `sylia.co`, `sylia.style`.
2. **VPS provider.** Recommended: **Hetzner CX23, location Falkenstein or
   Nuremberg (Germany)**. It's the cheapest good option and works well for both
   Lagos and Europe.
   Alternatives: DigitalOcean (~$24/month for 4 GB), Contabo (cheaper, slower).
3. **Account type on Google Play.** *Personal* (any adult, needs 12 testers for
   14 days) or *Organization* (needs a registered company + free D-U-N-S
   number, skips the 12-tester rule).

---

## 3. Phase 1 — Domain (30 minutes) · You

1. Create a free Cloudflare account → **Domain Registration → Register
   Domains** → search your name → buy (card or PayPal).
2. In Cloudflare **DNS** for the domain, add:
   - `A` record · name `api` · value = your VPS IP · **Proxy OFF (grey cloud)**
     (Caddy on the server gets the HTTPS certificate itself).
3. **Email Routing** → create `hello@yourdomain` → forward to your Gmail.
4. Send Claude the domain → Claude updates the app (`eas.json`) to
   `https://api.yourdomain`, plus the privacy/terms links.

## 4. Phase 2 — VPS (20–30 minutes) · You, with Claude checking

Full commands: [`deploy/DEPLOY-VPS.md`](deploy/DEPLOY-VPS.md).
1. hetzner.com → Cloud → new project → **Add server**: Ubuntu 24.04, CX23,
   tick **Backups**, add your SSH key (`ssh-keygen -t ed25519` in PowerShell).
2. Put the server IP in the `api` DNS record (Phase 1).
3. `ssh root@IP` → clone the repo → `bash setup-server.sh api.yourdomain` →
   paste your Anthropic key into `.env` → `docker compose up -d --build`.
4. Open `https://api.yourdomain/health` → `"status":"ok"`.
5. Claude runs the live checks: sign-up, photo upload, tagging, daily look,
   reveal, streaks, try-on, account deletion.
6. Free uptime alert: uptimerobot.com → HTTP monitor on `/health`.

## 5. Phase 3 — Website pages (Claude writes, you publish, free)

Both stores require a **privacy policy URL** and a **support URL**.
- Claude writes: landing page, privacy policy (covers photos, try-on photo,
  measurements, location, Claude AI processing, deletion, retention), terms of
  use, support page.
- You: Cloudflare → **Workers & Pages → Create → Pages → upload** the folder,
  attach `yourdomain` and `www`. Done.
- Pages: `https://yourdomain/privacy`, `/terms`, `/support`.

## 6. Phase 4 — TestFlight (first build ~1 hour, mostly waiting)

**Already set in the code:** bundle ID `com.sylia.stylist`, EAS project
linked, Sign in with Apple, privacy manifest, encryption flag (no export
paperwork), en/fr/es, iPhone only, build numbers auto-increment.

**You, once:**
1. **App Store Connect → Apps → + New App**: platform iOS, name **Sylia** (if
   taken, e.g. "Sylia: AI Stylist"), primary language English, bundle ID
   `com.sylia.stylist`, SKU `sylia-ios`.
2. Install tools (PowerShell): `npm install -g eas-cli` then `eas login`.

**Build and upload** (in `sylia/mobile`):
```bash
eas build --platform ios --profile production
eas submit --platform ios --latest
```
`eas build` asks you to sign in with your Apple ID (you type the password; EAS
creates the signing certificate). The build runs on Expo's servers (~15–30 min).
`eas submit` uploads it; Apple processes it (~10–30 min).

**Testers:**
- **Internal** (up to 100 people on your App Store Connect team): available at
  once, no review. Add yourself → install the **TestFlight** app → accept.
- **External** (up to 10,000 by email or public link): needs a quick **Beta
  App Review** (usually under a day). Fill "What to test", a contact email and
  a test account.

**What to test on a real iPhone:**
sign-up / Sign in with Apple · onboarding taste picker · body scan + quiz ·
add 6+ clothes by photo · the 7:00 reveal + notification · Today's look, wear
it, streak · journey · coach · Discover · **try-on setup + try sizes** ·
paywall (sandbox) · dark mode · French/Spanish · delete account.

## 7. Phase 5 — Subscriptions (Sylia Pro)

You, in **App Store Connect → Business**:
1. Sign the **Paid Apps Agreement**, add **bank account** and **tax forms**.
   Without this, subscriptions can't work, even in testing.
2. Apply to the **App Store Small Business Program** (15% instead of 30%).
3. **Monetization → Subscriptions**: group "Sylia Pro" → products e.g.
   `sylia_pro_monthly`, `sylia_pro_yearly` → set prices per country (Apple
   converts automatically) → 7-day free trial as an introductory offer.
4. **RevenueCat** (free): create project → add the iOS app → paste the App Store
   **In-App Purchase key** (App Store Connect → Users and Access →
   Integrations) → entitlement `pro` → attach both products → offering
   "default".
5. RevenueCat → Integrations → **Webhook**: URL
   `https://api.yourdomain/v1/billing/revenuecat/webhook`, Authorization value =
   a long random string. Put the same string on the server as
   `REVENUECAT_WEBHOOK_SECRET` in `.env`.
6. Send Claude the RevenueCat **public iOS SDK key** (safe to share; it ships
   inside the app). Claude adds it to `eas.json`, and you rebuild.
7. Test with a **Sandbox Apple ID** (App Store Connect → Users and Access →
   Sandbox) on a TestFlight build.

## 8. Phase 6 — App Store listing and review

**Assets** (Claude can produce most from the design files):
| Asset | Spec |
|---|---|
| App icon | 1024×1024 PNG, no transparency *(in the app already)* |
| Screenshots | iPhone **6.9-inch: 1320×2868**, 3–10 images; App Store Connect shows the exact accepted sizes |
| App preview video | optional, 15–30 s, from the motion video |
| Name / subtitle | 30 characters each, e.g. "Sylia" / "Your AI stylist, every day" |
| Promotional text, description, keywords (100 characters) | en, fr, es |
| Support URL, privacy policy URL, marketing URL | from Phase 3 |
| Category | Lifestyle (secondary: Shopping) |

**Forms in App Store Connect:**
- **App Privacy**: answer to match what the app collects: email, name,
  photos, coarse location, purchases, user content, product interaction. None
  of it is used for tracking; all of it is linked to the user. Claude gives you
  the exact answers.
- **Age rating** questionnaire (expect 4+ or 9+; no mature content).
- **EU Digital Services Act trader status**: say whether you're a trader. If
  yes, your contact details are shown on the EU store.
- **Review notes**: a demo account (email + password) with a filled closet,
  plus a note that try-on needs Pro (sandbox purchase works) and that the photo
  is optional.
- **Pricing and availability**: free app + subscription; choose countries.

**Apple review checks that apply to Sylia** (already handled in the app):
account deletion inside the app ✓ · Sign in with Apple next to email ✓ ·
restore purchases ✓ · subscription terms on the paywall ✓ · privacy links ✓ ·
permission messages explain why ✓ · AI output explained, not decided ✓.

Submit → review usually **1–2 days**. Choose "manually release" so you control
launch day.

## 9. Phase 7 — Google Play

1. play.google.com/console → pay **$25** → verify identity (government ID; for
   organizations also D-U-N-S). Can take a few days.
2. Create the app "Sylia", package `com.sylia.stylist`, free, with in-app
   purchases.
3. Build and upload (in `sylia/mobile`):
   ```bash
   eas build --platform android --profile production
   eas submit --platform android --latest
   ```
   The first upload needs a Google Play **service account key** for EAS. Expo's
   docs walk through it; you create it in the Google Cloud console.
4. **Closed testing** (personal accounts): **12+ testers opted in for 14
   days in a row**. Friends, family, early fans; a tester who drops out resets
   the 14 days. Then **apply for production access**.
5. Forms: **Data safety** (same answers as Apple's privacy form), **content
   rating** (IARC), **target audience** (18+ fits the consent rules), ads = no,
   **government apps** = no, **financial features** = no.
6. Store listing: icon 512×512, **feature graphic 1024×500**, phone screenshots
   (2–8), short description (80 characters), full description (4,000).
7. Subscriptions: Play Console → Monetize → Subscriptions (same product IDs)
   → connect Play to RevenueCat with a service account → add the RevenueCat
   **Android public key** → Claude adds it and you rebuild.
8. Review: first review often takes several days.

## 10. Launch-week checklist

- [ ] Server: `/health` OK, uptime alert on, Hetzner backups on, a database
      backup listed (`docker compose exec backup ls /backups`)
- [ ] A real purchase tested in sandbox; RevenueCat shows the event; the app
      unlocks Pro
- [ ] Demo account ready for Apple/Google reviewers
- [ ] Privacy policy matches the store privacy forms
- [ ] Support email answers
- [ ] Brand partner catalog: at least a few real products so Discover isn't
      empty (`/v1/admin/brands` + Partner API)
- [ ] Store listing in en/fr/es; screenshots show real clothes

## 11. As you grow (no action now)

| When | Change | Cost |
|---|---|---|
| ~5,000+ active users or the server feels slow | resize VPS in the Hetzner panel (minutes) | next tier up |
| photos pass ~30 GB | move photos to object storage (`STORAGE_BACKEND=s3`) | ~$0.015/GB/month |
| want realistic photo try-on | GPU model (FASHN VTON v1.5) on pay-per-use GPU | estimated fractions of a cent per try-on |
| revenue > $2,500/month | RevenueCat takes about 1% | — |

## 12. Who does what

| You | Claude |
|---|---|
| Buy domain, VPS; create Apple/Google/RevenueCat/Anthropic accounts; type all passwords and keys; sign agreements, tax, bank | Update `eas.json` with your domain and RevenueCat keys |
| Run the server commands in `DEPLOY-VPS.md` | Verify the live API end to end |
| `eas build` / `eas submit` (Apple sign-in prompts) | Fix anything that breaks in builds or review |
| Invite testers, answer reviewers | Write privacy policy, terms, support and landing pages |
| Press "Release" | Store text (en/fr/es), screenshots from the designs, privacy-form answers, review notes |
