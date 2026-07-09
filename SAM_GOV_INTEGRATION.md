# SAM.gov Integration — Research & Plan

**Status:** ✅ **Phase 1 shipped** — "Gov Opps" tab live in the La Gala admin
dashboard (backend + UI). Needs `SAM_GOV_API_KEY` set in Vercel to activate
(see `wwslgc/SETUP.md`). Phase 2 (entity/exclusion lookup) still planned.
**Placement:** new tab inside the **La Gala admin dashboard**
(`wwslgc/admin/index.html`), alongside Leads / Inspections / Invoices.
**Config chosen:** key from **Collaborative Concepts** SAM registration ·
place of performance **FL** · **all** procurement types (no set-aside filter) ·
on-demand dashboard search (no email alerts in v1).
**Date:** 2026-07-09

---

## 1. TL;DR recommendation

Build a **federal contract-opportunity finder** as a new **"Gov Opps"** tab in the
La Gala admin dashboard. It queries SAM.gov's public **Get Opportunities v2** API,
pre-filtered to the NAICS codes La Gala / Collaborative Concepts actually bids
(roofing, building inspection, building construction) in Florida, scores/lists the
results, and lets Danny save ones worth pursuing to a watchlist. This mirrors the
pattern the repo already uses for the Google Places "lead search"
(`POST /api/leads/search`, `api/index.py:465`) — a server-side proxy to a third-party
API with scoring, rendered in a tool page.

Entity lookup and exclusion (debarment) screening are **smaller bolt-ons** on the same
API key and can be added in a later phase; they are not the primary value for a
contractor who wants *work to bid on*.

**Why a server-side proxy (not browser fetch):** the SAM.gov key must stay secret and
the browser would hit CORS. It also lets us cache responses to protect the daily rate
limit (see §4).

---

## 2. The SAM.gov public API landscape

SAM.gov exposes several independent public APIs. Three are relevant here:

| API | Base URL | What it answers | Fit for us |
|---|---|---|---|
| **Get Opportunities v2** | `https://api.sam.gov/opportunities/v2/search` | "What federal solicitations are open that I could bid on?" | ⭐ **Primary** |
| **Entity Management** | `https://api.sam.gov/entity-information/v3/entities` | "Is this company SAM-registered? UEI / CAGE / status?" | Secondary — vet subs/partners; check our own reg |
| **Exclusions** | `https://api.sam.gov/entity-information/v…/exclusions` | "Is this company/person federally debarred?" | Secondary — screen before contracting |

All three authenticate with the **same** `api_key` query parameter.

Sources:
[GSA — Get Opportunities Public API](https://open.gsa.gov/api/get-opportunities-public-api/) ·
[GSA — Entity Management API](https://open.gsa.gov/api/entity-api/) ·
[GovCon API — SAM.gov guide](https://govconapi.com/sam-gov-api-guide)

---

## 3. Get Opportunities v2 — request/response reference

**Endpoint:** `GET https://api.sam.gov/opportunities/v2/search`
(a `/prod/opportunities/v2/search` alias also works.)

### Required parameters
| Param | Notes |
|---|---|
| `api_key` | our secret key (kept server-side) |
| `postedFrom` | **`MM/dd/yyyy`** — *not* ISO-8601 |
| `postedTo` | **`MM/dd/yyyy`** — max span **1 year** per request |

### Key optional filters
| Param | Use for us |
|---|---|
| `ncode` | **NAICS code** — the main relevance filter (see §5) |
| `ccode` | PSC/classification code (e.g. `Z2` repair/alteration of buildings) |
| `state` | Place-of-performance state → `FL` |
| `zip` | tighter geo filter |
| `ptype` | procurement type (codes below) |
| `typeOfSetAside` | e.g. `SDVOSBC`, `WOSB`, `8A`, `HZC`, `SBA` — if CC pursues set-asides |
| `title` | title keyword (note: API has **no full-text body search**, title only) |
| `rdlfrom` / `rdlto` | response-deadline window (hide already-closed) |
| `limit` | max **1000** per page |
| `offset` | pagination |

`ptype` codes: `o` Solicitation · `p` Presolicitation · `k` Combined
Synopsis/Solicitation · `r` Sources Sought · `s` Special Notice · `a` Award Notice ·
`i` Intent to Bundle · `g` Sale of Surplus · `u` Justification. For "work to bid,"
default to `o,p,k,r`.

### Response shape (per opportunity, `opportunitiesData[]`)
`noticeId`, `title`, `solicitationNumber`, `fullParentPathName` (agency),
`postedDate`, `type`, `typeOfSetAsideDescription`, `responseDeadLine`, `naicsCode`,
`classificationCode`, `active`, `placeOfPerformance` (city/state/zip),
`pointOfContact[]` (name/email/phone), `description` (a link, not text), and
`uiLink` (the human sam.gov page). Envelope: `totalRecords`, `limit`, `offset`.

---

## 4. API key & rate limits — the important gotcha

Get a key free from **Account Details** after signing in at sam.gov. Daily limits
depend on the account's role:

| Key type | Daily limit |
|---|---|
| Public / personal, **no SAM role** | **10 requests/day** ← too low to be useful |
| **Entity-registered** (has a role in a registered entity) | **1,000/day** |
| Federal system account | 10,000/day |

**Action item for Danny:** generate the key from an account that holds a role in a
**registered entity** (La Gala / Tilt Patchers / Collaborative Concepts SAM
registration) to get the 1,000/day tier. A bare personal key (10/day) will not sustain
even light dashboard use. Keys **auto-rotate every 90 days** — so store the key in a
Vercel env var and expect to update it quarterly (or wire a reminder).

Sources:
[SAM.gov rate limits](https://govconapi.com/sam-gov-rate-limits-reality) ·
[api.sam.gov rate-limit docs](https://api.sam.gov/docs/rate-limits/)

**Caching strategy (protects the 1,000/day budget):** cache each unique
`(ncode, state, ptype, postedFrom, postedTo)` query in the existing Upstash/KV store
(`_kv_cmd`, `api/index.py:325`) with a ~6–12 h TTL. Opportunities update slowly; this
keeps daily API calls in the low tens.

---

## 5. Relevant NAICS codes (the business filter)

From `BUSINESS-PROFILE.md` and the WWS roof-anchor/inspection line of business:

| NAICS | Description | Why |
|---|---|---|
| **238160** | Roofing Contractors | core WWS / roof-anchor certification work |
| **541350** | Building Inspection Services | WWS inspections, COI/compliance |
| **236220** | Commercial & Institutional Building Construction | GC work |
| **236115** | New Single-Family Housing Construction | custom homes |
| **236116** | New Multifamily Housing Construction | multifamily |
| **236118** | Residential Remodelers | major renovations |
| 238140 / 238170 / 238190 | Masonry / Siding / Other structure | trade subs |

Ship a small curated NAICS→label map in `api/index.py` (like `TRADE_QUERY`) so the tab
offers these as checkboxes rather than making Danny memorize codes. PSC `Z2` (repair/
alteration of buildings) is a useful `ccode` complement to NAICS for facility work.

---

## 6. Implementation plan (phased)

### Phase 1 — Opportunities finder (the deliverable)

**Backend** (`api/index.py`):
- `SAM_OPPS_URL = "https://api.sam.gov/opportunities/v2/search"` and
  `def _sam_key(): return os.environ.get("SAM_GOV_API_KEY")` — mirrors `_places_key()`.
- Curated `SAM_NAICS = {code: label, …}` map (§5).
- `POST /api/admin/sam/opportunities` — **admin-guarded** (`if not _is_admin(): 403`,
  same as every `/api/admin/*` route). Body: `{naics:[…], state:"FL", ptype:[…], days:30}`.
  - Compute `postedFrom/postedTo` from `days` (MM/dd/yyyy), fan out one request per
    NAICS (the API takes a single `ncode`), merge + de-dupe by `noticeId`.
  - **Cache** each sub-query in KV (§4). Return `{configured:false, hint:…}` when the
    env key is missing — exactly like `leads_search` does at `api/index.py:468`.
  - Light **scoring/sort**: soonest `responseDeadLine` first, flag set-asides CC
    qualifies for, hide `active:false` / past-deadline.
- `POST /api/admin/sam/watchlist` + `GET /api/admin/sam/watchlist` — save/list pursued
  opportunities in KV (`sam:watchlist` key), reusing the `_gen_id()` / `_log_activity()`
  helpers already in the file.

**Frontend** (`wwslgc/admin/index.html`):
- Add a **`data-tab="samopps"`** button next to the existing tabs (`api/…` around the
  `Leads / Inspection requests / …` row) and a matching panel.
- Panel: NAICS checkboxes, state input (default FL), lookback selector, "Search" button
  → table of results (title, agency, type, deadline, set-aside, sam.gov link) with a
  "☆ Watch" action. Reuse the dashboard's existing fetch/session pattern
  (PIN auth via `/api/admin/session`).
- **No Tailwind rebuild needed** — the admin dashboard uses the runtime CDN (per
  `CLAUDE.md`), so new classes work without `npm run build:css`.

**Config:** add `SAM_GOV_API_KEY` to Vercel env vars (document it in `wwslgc/SETUP.md`).

### Phase 2 — Entity & exclusion lookup (bolt-on, later)
- `POST /api/admin/sam/entity` → Entity Management API by UEI or legal name → show
  registration status / CAGE / expiration. Useful to vet a sub before hiring, or to
  watch CC's own registration expiry.
- `POST /api/admin/sam/exclusions` → Exclusions API → red/green debarment badge.
- Both reuse the same key and admin guard; add as a sub-panel of the Gov Opps tab.

---

## 7. Risks / gotchas
- **10/day trap:** a personal key silently returns 429s fast. Must use an
  entity-registered key (§4). Surface remaining-quota / 429 state in the UI.
- **90-day key rotation:** env var will need quarterly refresh; note it in SETUP.md.
- **Date format:** `MM/dd/yyyy`, not ISO — a common first-try bug.
- **No body full-text search:** only `title` keyword; rely on NAICS/PSC/state for
  relevance, not free text.
- **1-year max window** per request; our default 30–90 day lookback is well within it.
- **`description` is a link, not text** — don't render it as the blurb; use `title` +
  agency + deadline.
- **Network policy:** `api.sam.gov` must be reachable from Vercel's runtime (it is —
  this only affects the web-session sandbox, not production).

---

## 8. Open questions for Danny
1. Which entity's SAM registration should the API key come from (to get 1,000/day)?
2. Geography — FL only, or also federal work out of state?
3. Should we filter to **set-asides** CC qualifies for (veteran-owned? small business?),
   or show all opportunities?
4. Do we want email alerts on new matching opportunities (a cron over the cached query),
   or just on-demand dashboard search for v1?
