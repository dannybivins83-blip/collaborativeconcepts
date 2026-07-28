# CLAUDE.md — Repository Guide

Notes for Claude (and humans) working in this repo.

## ‼️ Read this before editing any file in a subdomain folder

**Multiple Vercel projects share the same root domain** (`collaborativeconceptsfl.com`).
Just because a folder exists in this repo does NOT mean its corresponding subdomain
is served from this repo. Editing a folder whose subdomain is bound to a different
Vercel project is wasted work — the changes never go live.

### Deployment map (as of 2026-06-08)

| Subdomain | Served from | This repo's folder | Status |
|---|---|---|---|
| `collaborativeconceptsfl.com` (apex) | this project (`collaborativeconcepts`) | `/` (root HTML files) | ✅ live |
| `wwslgc.collaborativeconceptsfl.com` | this project | `/wwslgc/` | ✅ live |
| `casadelmonte.collaborativeconceptsfl.com` | **separate** `casa-del-monte-portal` Vercel project | `/lagala/casadelmonte/` | ⚠️ **NOT live** |

When the subdomain column says "separate project," any edits in this repo's
corresponding folder will **not** affect the live site. Either:
1. Repoint the subdomain to this Vercel project (Vercel → Domains)
2. Get write access to the repo that actually serves the subdomain
3. Explicitly confirm with the user that the edit is intentional anyway
   (e.g. preparing the folder so it's ready when re-pointed)

### How the guardrail enforces this

Every HTML file in a subdomain folder has a marker meta tag:

```html
<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">
```

On every Claude session start, `.claude/hooks/session-start.sh`:

1. Parses `vercel.json` for every host referenced under `has.host`
2. Curls each subdomain root
3. Confirms the response includes the marker meta tag

If the marker is missing, the host + its source folder are written to
`.claude/state/mismatched-subdomains`. Then `.claude/hooks/pre-tool-use.sh`
will refuse Edit / Write / MultiEdit / NotebookEdit calls that target any
file inside a mismatched folder, until the user explicitly clears the
state file (`rm .claude/state/mismatched-subdomains`) or fixes the binding.

### Adding a new subdomain to this repo

When you set up a new subdomain to be served from this repo:

1. Create the folder (e.g. `/newthing/`)
2. Add the marker meta tag to its `index.html`:
   `<meta name="x-claude-source-repo" content="dannybivins83-blip/collaborativeconcepts">`
3. Add a rewrite in `vercel.json` mapping the host to the folder
4. Confirm in the Vercel dashboard that the subdomain is bound to this project

The startup hook will pick it up automatically on the next session.

## Repo overview

- **Marketing site** at the apex (`collaborativeconceptsfl.com`) — root `*.html`
  files (`index.html`, `team.html`, `properties.html`, `invest.html`,
  `contact.html`, `solutions.html`, `pipeline.html`, `pipeline-100.html`,
  `outreach.html`), plus `/projects/` and `/blog/`.
- **WWS landing page** at `/wwslgc/` (subdomain root) — public OSHA
  Walking-Working Surfaces marketing page; lead-capture form via FormSubmit.
- **WWSLGC portal** at `/wwslgc/send/` — internal outreach mailer with Microsoft
  365 and Gmail OAuth integration. Backend in `api/index.py`.
- **Casa Del Monte mock** at `/lagala/casadelmonte/` — **NOT currently live**
  (see deployment map). Prototype landing page + portal sit here waiting for
  the subdomain to be repointed.
- **Backend** at `api/index.py` — single Flask app handling all `/api/*`
  requests via the `vercel.json` rewrite. Sections include the WWSLGC OAuth
  mailer and the Casa Del Monte portal email-attachment uploads.
- **SoFlo Permit Leads** at `/permits/` — internal BatchData-style
  building-permit lead dashboard for Martin / Palm Beach / Broward /
  Miami-Dade. Engine in `api/permits.py` (routes `/api/permits/*`: search,
  tags, sources, discover, CSV export). Pulls real permits per county:
  Miami-Dade (official open-data, resolved via ArcGIS Hub v3 dataset API),
  Broward (Fort Lauderdale + unincorporated county ArcGIS layers), Martin
  (Accela portal scraper in `api/accela.py` + development-projects layer).
  **FL cities permit independently of their county, so each city is its own
  source** — 19 run Tyler EnerGov Civic Access (`kind: energov_css`) and Boca
  publishes monthly CSVs (`kind: csv_monthly`). Palm Beach therefore has 8
  sources, not zero (that earlier "no queryable feed" note was wrong).
  EnerGov gotchas, all learned the hard way — don't re-litigate:
  the `tenantName` header is **ignored** (the server resolves the tenant from
  the Host; bogus/empty values return identical data), so a new city needs only
  a host — find it by DNS-probing `<slug>-energovweb|energovpub.tylerhost.net`
  patterns, then confirm with a real search call. Self-hosted cities use a
  site-specific IIS path (`path` key; Sunrise is `/EnerGov_Prod/SelfService`).
  Paging dies at Elasticsearch's 10k `max_result_window`, so bulk pulls must
  filter server-side via `PermitCriteria.Description` +
  `EnableDescriptionSearch` — and that match is **OR over tokens** (`ExactMatch`
  does nothing), so multi-word terms are junk: use single words and classify
  locally. Records carry `MainParcel` (folio/PCN) — the join key to each county
  appraiser for owner + mailing. Miami Beach runs CSS but its search API 500s
  for everyone including its own page; not wired up.
  Schema auto-mapping is name-based then **content-based** (infers fields
  from real record values when column names don't match); a blocklist rejects
  known wrong-jurisdiction ArcGIS orgs. Time window supports days/months/years/
  specific-year with server-side date filtering + pagination. Add/override
  feeds via `PERMITS_EXTRA_SOURCES` env var — no deploy needed. Also serves
  Miami-Dade RER **code violations** (EnerGov layer 86, open cases) as a
  distinct "violation" category. The **re-roof lead list** (`/api/permits/reroof`,
  the WWS anchor-recert campaign) excludes single-family & pitched-roof
  (shingle/tile/metal) jobs by DEFAULT — a house re-roof is not a roof-anchor
  lead. This is intentional (see `pitched_roof`/`single_family` tags +
  `wws_disqualified()`); it's a text-only first pass (the feed has no unit/use),
  with the offline appraiser step filtering the rest on units. `?include_residential=1`
  keeps them; `filtered_residential` reports the count dropped. Click any
  dashboard row to expand a full record detail panel. Serverless-safe: whole-request time budget + Accela
  deadline stay under `vercel.json` `maxDuration` (measured: per-county 16-17s,
  all-counties 31s vs a 45s budget). Offline tests:
  `python3 _permits_tests.py` (97) and `python3 _accela_tests.py` (14), all
  network mocked. **Known broken (pre-existing):** `broward_uninc` 404s on a
  moved ArcGIS Hub dataset and `martin` parses no rows — both return 0.

- **WrapMiles** at `/wrapmiles/` — car-wrap sponsorship marketplace (pay-per-mile
  mobile OOH). Landing page + three portals: `/wrapmiles/admin/` (matchmaking
  desk), `/wrapmiles/driver/`, `/wrapmiles/sponsor/`. API in `api/wrapmiles.py`
  (`/api/wrapmiles/*`), registered from `api/index.py` like permits. Storage is
  Postgres via `WRAPMILES_DB_URL`/`POSTGRES_URL`/`DATABASE_URL` (Neon through
  Vercel Storage); until attached, the API returns `db_not_configured` and the
  portals show a setup screen — nothing crashes. Admin auth =
  `WRAPMILES_ADMIN_KEY` env var; drivers/sponsors log in with email + an access
  code generated in the admin panel (no email infra needed). Money = integer
  cents; payouts = approved in-cap miles × rate + flat monthly (non-car assets
  like golf carts are flat-rate). Impressions are always labeled estimates
  (50/verified mile). Landing forms dual-write: FormSubmit email + best-effort
  POST to the API. **Referral links:** every driver auto-gets a shareable
  `ref_code` (NAME-XXXX); `/wrapmiles?ref=CODE` persists to localStorage and
  prefills `referred_by` on both forms; driver portal has a share card
  (copy/native share/WhatsApp/SMS/QR via `/api/wrapmiles/qr?ref=`) with live
  signup counts. Offline tests: `python3 _wrapmiles_tests.py` (61, sqlite).
  Contracts (attorney-review drafts) in `wrapmiles/legal/`; outreach copy in
  `wrapmiles/outreach/`; scout skills in `.claude/skills/wrapmiles-*`.

## Local tooling

- Python: 3.11+, deps in `requirements.txt`
- Static site. **One build step for WWS public pages:** they load a prebuilt
  `/assets/wws.css` (Tailwind) instead of the runtime CDN. **If you add/change a
  Tailwind class on any `wwslgc/*.html` or `wwslgc/guides/*.html` page, run
  `npm run build:css`** or the new class won't be styled. Config in
  `tailwind.config.js` + `src/tailwind-input.css`; `node_modules` gitignored.
  The admin/portal/send/design tools still use the runtime CDN (they build class
  names dynamically in JS), so no rebuild is needed for those.
- WWS images are WebP-wrapped: public pages use `<picture><source webp><img jpg></picture>`.
  Regenerate WebP with `sharp` if you add images to `assets/wws/`.
- Tests / linters: none currently wired

<!-- OVERLORD-BUS v1 -->
## Standing rule: keys, secrets & infra provisioning go to OVERLORD

Owner directive (2026-07-28): **any task involving credentials, API keys, env
vars, database provisioning, or dashboard-level infrastructure changes is
routed to the `overlord` agent via the bus — do not walk Danny through it and
do not handle secret values yourself.** Draft the bus message (task, project,
verification steps, where to reply), never include secret VALUES in it, and
let OVERLORD provision + store the secret and deliver it to Danny directly.

**Cloud sessions (Claude Code web/remote) cannot reach the bus** — it lives on
the owner's local machine. From a cloud session, queue the message as a file in
`.claude/bus-outbox/` (frontmatter: status/to/from/date/subject) and commit it.
**Local sessions: on session start, check `.claude/bus-outbox/` — move any
`status: new` files into the bus inbox of the addressee** (per the bus section
below), then update the file's status to `delivered` in the repo.

## Collaborative Concepts — cross-project comms (OVERLORD bus)
You are one agent in Collaborative Concepts LLC (owner: Danny Bivins). Coordinate with other projects through the shared message bus — do NOT route through the owner:
`C:\Users\kjburnz\acculynx roofr reprot\_OVERLORD\bus\` (read `bus\PROTOCOL.md`).
- Find your slug in `bus\registry.json` (match your project path); if not listed, add yourself.
- On start + each work session: check `inbox\<your-slug>\` for `status: new`; act; reply into the sender's inbox; mark done -> move to `archive\<your-slug>\`.
- To reach another agent/project: drop a message file in `inbox\<their-slug>\`.
- Cross-project decision or blocked: message `overlord`. Never put secret VALUES in a message.
The OVERLORD heartbeat (scheduled agent) routes the bus and escalates owner-decisions.
<!-- /OVERLORD-BUS -->
