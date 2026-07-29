# adometr — Business Plan
**Brand:** adometr · adometr.com (secured 2026-07-29) · *"Miles out. Money in."*
**Entity:** Collaborative Concepts LLC (Adometr is the brand; d/b/a filing deferred — required
before signing/invoicing under the name) · **Owner:** Danny Bivins
**Rev:** 2026-07-29 (rebrand rewrite; roundtable-stress-tested, Full C-Suite, verdict YELLOW)
**Year-1 cash budget: $5k–$15k** · GL insurance coverage **confirmed ✓**

---

## 1. The Business — Who / What / When / Where / Why / How

**WHO.**
- *Supply side:* South Florida vehicle owners with high daytime mileage — gig & delivery
  drivers (DoorDash/UberEats/Instacart/Amazon Flex/Spark), home-health nurses & aides,
  pool/pest/lawn route operators, outside sales reps, construction subs, realtors, commuters —
  plus non-car asset owners (golf carts/LSVs, work trailers, boats, food trucks).
- *Demand side:* local/regional advertisers already spending on billboards, radio, or PPC:
  home services & roofers, personal-injury and other law firms, med spas/dental, gyms,
  restaurants & franchises, insurance and real-estate teams, credit unions, urgent care —
  plus public district marketers (DDAs/CRAs) and flagship pursuits (Brightline, agencies).
- *Operator:* Danny (sales + approvals + signatures), backed by an automation bench —
  the admin desk, the scout agent, OVERLORD (infra), and the build agent (this repo).

**WHAT.** A two-sided marketplace for pay-per-mile mobile out-of-home advertising: brands
buy geo-targeted wrapped-vehicle campaigns; drivers earn $0.12–$0.35 per verified mile
(2,000 paid mi/mo cap); non-car assets rent at flat monthly placement rates. Adometr owns
the sponsor relationship, matching, verification, reporting, and keeps the spread.

**WHEN.** Now → first signed pilot targeted by Oct 1, 2026 (Day-90 kill-review Oct 26).
Campaigns run 3–6 month terms; drivers submit mileage monthly; sponsors get monthly
verified-mile reports; referral milestones pay at wrap/3/6/12 months.

**WHERE.** Home market: the I-95 corridor, Jupiter → Miami (Palm Beach, Broward,
Miami-Dade), plus the Turnpike and US-1. Expansion territories via ambassadors:
Orlando (I-4/408 commuter market) and Melbourne / Space Coast — with West Palm and
Broward anchored by territory partners as well. Highest-value micro-markets: dense commuter corridors, cart-legal
downtowns (Delray's Atlantic Ave), airport zones, event venues. Digital storefront:
adometr.com (landing + calculator + both application forms + three portals).

**WHY (each party).**
- *Drivers:* their commute already happens — a wrap turns it into $250–$700/mo, costs them
  nothing, protects the paint, and is removable. Referrals add up to $375/driver.
- *Sponsors:* ~$1–4 estimated effective CPM vs $10–30 for static billboards; geo-exact;
  verified miles + photo proof + promo-code attribution a billboard can't offer; no 12-month
  board lease; a local operator who answers his own phone.
- *Adometr:* ~55% gross margin on media fees with near-zero fixed costs, riding rails
  (site, portals, verification, referrals) that are already built and cost ~$0/month to run.

**HOW (the operating loop, end to end).**
1. Driver applies (form auto-writes to the database + emails Danny; referrer auto-credited).
2. Danny scores A/B/C in the admin queue → one-click qualify/decline.
3. Docs verification: 7-point checklist (license, insurance, photos, odometer proof, signed
   agreement, MVR consent; paid MVR pull is wired but deferred). Driver → `wrap_ready`.
4. Sponsor signs an insertion order; production fee collected **before** vinyl prints.
5. Matching: geography first, canvas second, miles third; 3× wrap-ready bench per campaign.
6. Install at partner shop → match goes `active`; driver's portal opens mileage submission.
7. Monthly: driver submits odometer miles + photo → Danny approves in the queue → the
   ledger computes payouts (in-cap miles × rate + flat) → sponsor's dashboard updates
   verified miles + estimated impressions; CSV report downloadable.
8. Renewal case = the report + promo-code redemptions. Churned car → replaced ≤21 days.

## 2. Acquisition Playbooks

### Drivers (supply) — channels in ROI order, weekly cadence
1. **Referral flywheel (built):** every driver has a share link + QR; $50/$75/$100/$150
   milestones. Every driver touchpoint repeats it. Target: >40% of new drivers via referral
   by month 6.
2. **Gig watering holes:** South Florida Uber/Lyft/DoorDash Facebook groups, r/uberdrivers —
   value-first calculator posts (copy written, in `adometr/outreach/`); MIA/FLL/PBI staging
   lots with the tear-tab flyer + QR.
3. **Occupation channels:** home-health agencies (driver perk + agency referral fee),
   pool/pest/irrigation supply houses, pizza shops, Danny's construction subs (one text —
   written in his voice), FAU/PBSC/FIU commuters, Turo hosts (3–5 cars per yes).
4. **Craigslist/FB Marketplace gigs** posts, rotated monthly, all three counties.
5. **Paid (only when organic saturates):** Meta lead ads, rideshare-interest + corridor-zip
   geofence, CPL cap $8.

### Sponsors (demand) — channels in ROI order
1. **Danny's own network (warm):** roofers, PI attorneys, med spas, PMs/HOAs — first 10
   pitches come from here; the objection cheat sheet is phone-ready.
2. **Already-advertising businesses:** photograph billboards/bus benches on I-95/US-1/
   Okeechobee/Glades — those advertisers are pre-qualified for cheaper mobile OOH.
3. **DDAs/CRAs:** West Palm, Delray, Fort Lauderdale, Boca — pilot letters written, priced
   under small-purchase thresholds; first public logo unlocks the rest.
4. **Agencies & networking rooms:** 10/5/5/10% referral makes agencies, chambers, and BNI
   a commission-only sales force.
5. **Franchises/multi-location** (one yes = three counties) and the **Brightline** flagship
   memo (event-day swarms around stations).
6. **The fleet itself:** every wrapped car carries a "your brand here / adometr.com" rear
   decal — the product advertises the product.

### Marketing outlets (owned / earned / paid)
- **Owned:** adometr.com + calculator (SEO copy live), referral links + QR codes, the demo
  truck, rear-window "your ad here" decals, Google Business Profile ("advertising agency,
  Lantana FL"), an email list built from applicants.
- **Organic social:** wrap-reveal transformation videos (IG Reels/TikTok — install timelapses
  are proven high-engagement), driver payday screenshots (with permission), corridor-spot
  content; LinkedIn posts for the sponsor side.
- **Earned:** South Florida Business Journal / local biz podcasts ("local answer to
  billboard prices" pitch), chamber newsletters, DDA press releases when the pilot signs.
- **Paid (last):** Meta lead ads both sides, Google Search on "car wrap advertising
  [city]" + "billboard cost [city]" — only after organic channels saturate.

## 3. Automation Map — what runs itself, what's next, what stays human

**Automated today (built, $0/mo):**
- Intake → database + email, referral crediting, access codes, portal logins
- Admin queues (applications, mileage), payout math/ledger, sponsor reporting + CSV
- Referral links/QR generation and live counts
- Scout agent: prospect hunting + outreach drafting on demand; OVERLORD: infra via the bus

**Automate next (in order of leverage):**
1. **New-lead alert → scored digest** (scout session run on a schedule or on demand each
   morning: triage overnight applications, draft follow-ups into Gmail).
2. **Smartcar odometer pulls** (~$3/car): monthly verified miles with zero driver effort —
   replaces photo-approval labor for compatible 2015+ cars; auto-creates mileage rows.
3. **Stripe invoicing** (existing CC account): auto-bill sponsors monthly; unpaid → pause
   reporting automatically.
4. **Report emails:** monthly sponsor PDF/CSV auto-sent; driver payout notifications.
5. **Wrap-condition nudges:** monthly SMS/email to drivers due for a photo check-in.
6. **GPS ingestion webhook** (endpoint pattern exists): Bouncie devices → corridor-level
   reports for premium campaigns, per-car toggle already in the admin desk.

**Stays human (deliberately):** sponsor closing calls, driver approval judgment, mileage
fraud review, wrap install scheduling, contract signatures, pricing exceptions.

## 4. Unit Economics (per average car, partial wrap)

| Line | Monthly |
|---|---|
| Sponsor media fee (guardrail: 2.0–2.5× driver cost; floor $750 full wrap) | ~$600–675 |
| Driver payout (1,500 verified mi × $0.18) | ~$270 |
| **Adometr gross margin per car** | **~$330–405 (≈55%)** |

One-time wrap production+install (~$800–1,500 partial) bills at cost +15%, **collected
before production** — wraps are never fronted on spec. Verification cost ladder: odometer
photos $0 (live) → Smartcar ~$3/car → GPS device ~$9/car (sponsor-funded, per-car toggle).

## 5. Financial Projection (base case, conservative)

| Milestone | Cars live | Gross media/mo | Driver payouts/mo | Adometr gross/mo |
|---|---|---|---|---|
| M3 (first pilot + 1) | 5 | ~$3.2k | ~$1.4k | ~$1.8k |
| M6 (3 sponsors) | 12 | ~$7.8k | ~$3.4k | ~$4.4k |
| M12 (8–10 sponsors) | 30 | ~$19.5k | ~$8.5k | ~$11k |

Year-1 revenue ≈ $80–120k at ~55% gross margin before owner time. Cash break-even month
2–3: fixed costs are trivial (domain ~$12/yr, attorney ~$1k one-time, existing CC insurance,
hosting $0, Stripe under the existing CC account). Downside (revenue 30% under): still
cash-positive — no fixed burn; underperformance costs Danny's time, not capital.

## 6. Organization

- **Owner/CEO:** Danny — sells, approves, signs. Hard cap ~5 hrs/wk until first sponsor cash.
- **Automation bench:** admin desk, adometr-scout agent, OVERLORD (infra), build agent.
- **First hire trigger:** >25 active cars or >6 active sponsors → part-time ops coordinator.

## 7. Risks & Mitigations

1. **Two-sided cold start** → sell demand first; wraps print only after sponsor payment;
   3× wrap-ready bench per campaign.
2. **Attribution skepticism (top objection)** → promo codes/QR on every wrap, verified-mile
   reports, estimates always labeled — honesty as positioning.
3. **Owner bandwidth (the real constraint)** → 5 hrs/wk cap; automation map above exists to
   keep it there; Day-90 kill-review enforces discipline.
4. **Liability / driver incident** → runs under Collaborative Concepts LLC (owner accepted
   the shared-entity trade-off; spin out a dedicated LLC when MRR justifies); driver's own
   insurance primary + indemnity; sponsor no-control clause; GL coverage confirmed ✓;
   attorney review of both contracts is the remaining gate before the first wrap.
5. **Rideshare platform policies** → delivery/route drivers first; platform risk sits with
   the driver by contract (§4); never marketed as "Uber-approved."
6. **Driver churn mid-campaign** → 21-day replacement guarantee priced into margin.
7. **Brand spelling ("adometr")** → full spelling priced at $5k premium; dropped-vowel
   domain is the rational buy (Flickr/Tumblr precedent). Consistent lowercase wordmark
   everywhere; revisit acquiring adometer.com if it reprices.

## 8. Milestones & Kill Criteria

**Done (July 2026):** platform built + live ✓ · brand locked (name/logo/palette/tagline) ✓ ·
adometr.com purchased ✓ (Vercel attach in progress via OVERLORD) · GL insurance confirmed ✓ ·
contracts drafted ✓ · referral engine live ✓ · scout agent + outreach packs + objection
sheet ready ✓ · verification pipeline (checklist/photos/GPS-toggle) live ✓

**Aug 2026:** rate card locked (turns outreach placeholders into numbers) · attorney review
of both contracts · demo truck wrapped · 10 warm sponsor pitches · DDA letters to West Palm
+ Delray · d/b/a filed before the first Adometr-name signature
**Sep 2026:** first signed IO with production fee collected · 15 wrap-ready drivers ·
Smartcar + Stripe automations evaluated once revenue starts
**Oct 2026 (Day-90 kill-review, ~Oct 26):** no signed sponsor → stop outbound spend, site
stays as passive lead catcher, revisit quarterly. Signed → scale per GTM.
**Q4 2026:** 3 paying sponsors, 12+ cars, Smartcar verification live, DDA pilot submitted
**2027:** $25k MRR target; ops hire and Brightline/agency channel evaluations
