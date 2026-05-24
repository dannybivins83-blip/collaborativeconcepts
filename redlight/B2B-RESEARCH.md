# B2B Fleet-Safety Pivot — Research & Decision Brief

_Last updated: 2026-05-24._

## TL;DR

Consumer Redlight is a viral-loop bet. **Fleet Redlight is a revenue bet** — the same camera-based attention tech sold per-seat to commercial fleets and (downstream) insurance carriers. The fleet-safety market is real, growing ~10–15% annually, and the top three players (Samsara, Lytx, Motive) each do high-eight-to-nine-figure ARR. The cost: 12–18 months and a sales team you don't currently have. The bet pays off if the consumer share-rate doesn't break 15% during the beta — that's your fork point.

---

## 1. Market shape

### Total addressable
Fleet management software is a $25–30B global market. The "video-based safety" sub-segment — which is where Redlight technology fits — is roughly $2.5–4B today, growing 10–15% YoY through 2030. Insurance telematics (UBI — usage-based insurance) is another $50B+ market with much faster growth.

### Buyer
Two distinct buyers, each with different sales motions:

1. **Fleet operators** (the obvious one). Anyone with >25 vehicles: delivery (UPS, FedEx, Amazon DSPs), trucking (long-haul + last-mile), service trades (HVAC, plumbing, landscaping), municipal (transit, sanitation, police), rideshare/livery. Sells per-vehicle per-month.
2. **Commercial insurance carriers**. Progressive Commercial, Nationwide, Travelers, The Hartford. They subsidize or mandate telematics for premium discounts. Wholesale deals, not per-seat. Slower sales cycle, much larger contracts.

### Why fleet operators buy
Three drivers (in order):
- **Liability.** A single at-fault accident with a commercial vehicle averages $148K. Multi-vehicle commercial accidents involving a fatality routinely hit $1–5M. Anything that reduces frequency or provides exculpatory evidence pays for itself in one avoided suit.
- **Insurance premiums.** Carriers offer 10–25% discounts for verified telematics + driver-behavior monitoring. For a 100-vehicle fleet that's $50–150K/yr in real savings.
- **Driver behavior.** Distracted driving is the #1 cause of commercial crashes. Fleets want a deterrent and a coaching tool.

---

## 2. Competitive landscape

| Vendor | What they do | ARR (est.) | Pricing | Weakness |
| --- | --- | --- | --- | --- |
| **Samsara** ($IOT, public) | Telematics + dashcam + ELD + maintenance. The 800-lb gorilla. | $1.2B FY24 | $30–60/vehicle/mo + hardware | Bloated, slow product cycles, expensive hardware lock-in. Generic AI — they don't single out attention at signals. |
| **Lytx** (private, Permira-owned) | The OG dashcam-event-recording company. DriveCam since 1998. | ~$300M | $40–80/vehicle/mo | Aging tech stack, manual event review, slow to ship new ML. |
| **Motive** (formerly KeepTruckin, private) | ELD + dashcam + fleet ops. Rocketship through 2022. | ~$500M, valued $2.85B | $35–55/vehicle/mo | Spreading thin across too many SKUs. |
| **Nauto** (private) | AI-first dashcam. Distracted-driving detection. | ~$50M | $40/vehicle/mo | Smaller, less channel reach. |
| **Netradyne** (private) | DriverI camera, "Green Zone" gamification. | ~$80M | $45/vehicle/mo | Hardware-heavy install. |
| **Lightmetrics** (acquired by Bosch) | Pure-software dashcam SDK. Sells to integrators. | n/a | OEM | Not a direct competitor — sells the SDK others build on. |

### How Redlight is different (the actual angle)

Redlight's MVP angle isn't general distracted-driving (where Samsara/Nauto have a 10-year head start). It's **specifically the red-light reaction window** — quantified, gamified, and measured per-driver. None of the incumbents do this, because their unit of measurement is "events per 100 miles," not "seconds of attention per signal."

The fleet pitch: *"For every signalized intersection your trucks sit at, we tell you who's awake when it turns green — and who isn't. Two seconds of average reaction-time improvement across a 100-vehicle fleet is 12 hours of recovered drive time per week."*

That's a metric Samsara doesn't have a column for.

---

## 3. The fleet product (what would change)

Most of the consumer codebase carries over. The fleet SKU adds, in roughly this order:

| Capability | Effort | Note |
| --- | --- | --- |
| Multi-driver accounts + admin dashboard | M | Web dashboard. Next.js. Roughly 8 engineer-weeks for the v1. |
| Per-trip session aggregation server-side | M | First time you actually need a backend. Postgres + Node. |
| Coaching reports (per-driver attention scorecards) | M | Same data, weekly digest. |
| Hardware: dashboard mount + always-on power | S | Reference design, $40 BOM. Don't build hardware — partner. |
| Always-on background capture (vs. consumer's session-only) | L | This is the privacy line that fleet drivers actually accept and consumers don't. |
| Fleet-grade ML accuracy on the light detection | L | Same TFLite work as consumer, just gated harder. |
| SSO + SOC 2 + GDPR + DOT data-retention rules | L | The compliance moat that locks out indie competitors. |
| Integration with the major fleet OS — Samsara API, Motive API, etc. | M | "Lives inside Samsara" is a faster sale than "replace Samsara." |

Total: 12–18 months with a 4–6 engineer team. About $1.5–2.5M of burn.

---

## 4. Two paths to first revenue

### A. Direct-to-SMB fleet (faster, lower ACV)
Target: 25–100 vehicle fleets — HVAC contractors, regional couriers, municipal sanitation. Easier to reach. Lower budget, faster decision, less procurement friction.

- ACV: $15–40K/yr
- Sales cycle: 30–60 days
- First $100K ARR: 3–6 months from a real beta
- Channels: cold outbound (LinkedIn Sales Navigator + Apollo), industry forums (TruckersReport, Owner-Operator Independent Drivers Assoc), one-day trial offers

### B. Insurance partnership (slower, multi-million)
Target: 2–3 commercial auto carriers. Pitch: "Our data feeds your underwriting, our app reduces your loss ratio."

- Deal size: $1M+ multi-year, sometimes with carrier-funded driver hardware
- Sales cycle: 12–24 months
- First revenue: late 2027 at earliest
- Channels: insurance-industry conferences (ITC Vegas, InsureTech Connect), warm intros, one carrier-relations hire

Recommended sequence: A first (proves ROI numbers you can show a carrier), then B with that proof in hand.

---

## 5. The fork decision

Run the consumer beta for 14 days. Then choose:

| Signal | Decision |
| --- | --- |
| ≥20% of session-starters export a share card AND share rate week 2 > week 1 | **Stay consumer.** Raise a seed on viral coefficient, hire growth + ML. |
| 10–20% share rate, flat or declining | **Hybrid.** Keep consumer alive as a top-of-funnel + brand, but start fleet motion in parallel with one biz-dev hire. |
| <10% share rate | **Pivot fully to fleet.** The viral loop didn't work; the unit economics of consumer mobile advertising are brutal without organic growth. Cut consumer to a marketing site that drives fleet leads. |

This is why the beta event tracker (see `src/services/analytics.ts`) measures `share_card_exported` per `session_started`. That ratio is the fork.

---

## 6. What I'd start now if you pick fleet

1. **Discovery interviews.** Twenty calls with fleet operators of 25–100 vehicles. Sample script in `redlight/legal/` … no, this should be its own doc. (TODO.)
2. **Land 3 design partners** before writing the dashboard. They get the product free for 6 months in exchange for weekly feedback and a logo on the site.
3. **Build the admin dashboard** as a Next.js app alongside this repo. The mobile app stays mostly unchanged — it just starts reporting to a backend.
4. **Insurance research call** — David Carlson (was at Hyundai → State Farm). Will trade an intro for an hour of his time.

## 7. Open questions to validate before committing

- Does the existing camera ML accuracy generalize across the dashcam viewing angles fleets actually use? (Probably not — fleets use windshield-mounted cameras at much wider angles. Fine-tuning needed.)
- Will fleet drivers tolerate always-on capture? (Yes if compensated/required by employer; this is industry norm.)
- Can we get a meeting with Progressive Commercial without a warm intro? (Likely no. Need a fund or angel in the insuretech world.)
- What's the right hardware partner — Pyle, Owl Cam, or buy outright from the Lightmetrics/Bosch dashcam reference designs? (Buy outright, no custom hardware on day one.)

---

## Appendix: live data sources

- **Samsara investor materials** — Q3 FY24 results, $1.249B ARR, 26% YoY. <https://investors.samsara.com>
- **Motive** valuation — $2.85B Series F (Aug 2022, Insight + Kleiner Perkins).
- **Commercial-auto loss data** — National Highway Traffic Safety Administration FARS. <https://www-fars.nhtsa.dot.gov>
- **Insurance telematics market sizing** — Berg Insight, Counterpoint, IDC reports.
- **Fleet-safety video market** — Frost & Sullivan "Video Telematics" reports.

All numbers in this brief are estimates from public sources as of 2026-05. Verify before relying on any specific figure in a fundraising or board context.
